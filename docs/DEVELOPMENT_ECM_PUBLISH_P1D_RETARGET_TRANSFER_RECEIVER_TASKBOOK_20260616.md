# ECM Publish — P1D Retarget to Athena Transfer Receiver (Decision Taskbook)

Date: 2026-06-16
Status: **DECISION — pending gate review**
Supersedes the ingest-surface assumption in
`docs/DEV_AND_VERIFICATION_ECM_PUBLISH_P1D_CMIS_ADAPTER_SKELETON_20260616.md` (#768).
Drives the next phase: **P1D-retarget** (build `AthenaTransferReceiverAdapter`).

## 0. Why this exists

The P1D skeleton (#768) was built against an **assumed** Athena CMIS browser-binding
`createDocument`. A read of the actual Athena codebase (`/Users/chouhua/Downloads/Github/Athena`,
`ecm-core`, our own sibling repo — no license boundary) shows that assumption is wrong on
every structural axis, and that Athena has a **purpose-built system-to-system ingest
protocol** (the *Transfer Receiver*) that fits the PLM release outbox far better. This
taskbook records the surface decision and locks the load-bearing design choices before the
retarget build, so they can be gate-reviewed (and so we don't burn a live Phase-0 cycle
re-discovering them).

## 1. Surface decision

| Surface | Verdict | Rationale (from the Athena source read) |
|---|---|---|
| **Transfer Receiver** (`POST /api/v1/transfer/receiver/documents`) | **CHOSEN** | Purpose-built for system-to-system ingest with **receiver-side idempotency**; single multipart call **with content**; a working reference sender (`AthenaTransferHttpClient.uploadRemoteDocument`) exists to emulate; its dedupe model maps onto our at-least-once + per-file outbox. |
| Native multipart upload (`POST /api/v1/documents/upload`) | Secondary | Single call with content, but folder-**UUID**-only targeting, **no idempotency**, weak identity carrying. |
| CMIS browser (`POST /api/cmis/browser?cmisaction=…`) | Compliance reference only | Wrong on every axis for our use (see §1.1). Keep as interop reference, not the production path. |

### 1.1 Why the #768 CMIS adapter is wrong (and silently false-succeeds)

- Path is `/api/cmis/browser` (no context-path), **not** `/cmis/browser` → 404.
- `cmisaction` is a **query param**, not a body key → 400 (or silent wrong-route).
- The DTO is strict **camelCase** and Jackson `FAIL_ON_UNKNOWN_PROPERTIES=false` → our
  snake_case keys (`folder_path`, `object_type_id`, identity fields) are **silently dropped**
  → a **zero-byte document at repository root**, returned 2xx — a false success worse than a
  reject.
- `createDocument` is **content-less** (ignores `contentBase64`); bytes require a separate
  `setContentStream` call. `folderPath` does **not** auto-create folders (404 if missing).
- The new object id is nested at `object.objectId` (our `send()` reads top-level → always
  `None`). CMIS requires a **Keycloak JWT** (our static service token → 401).

## 2. Transfer Receiver contract (the real target)

`POST {athena_base}/api/v1/transfer/receiver/documents`, `multipart/form-data`, → `201`
`{documentId, documentName, disposition, message}`.

Multipart params: `file` (bytes; part filename → node name), `parentFolderId` (UUID,
**required**, must pre-exist), `conflictPolicy` (enum, default `RENAME`),
`sourceRepositoryId` (String), `sourceNodeId` (UUID), `sourceLastModifiedAt`
(ISO-8601 LocalDateTime), `description` (optional).

Auth: two custom headers `X-Athena-Transfer-User` / `X-Athena-Transfer-Secret`, matched
against a `TransferReceiverRegistration` row on Athena (authType NONE/BASIC/BEARER;
credentials scoped to one folder subtree; provisioned via the `/api/v1/transfer/receivers`
admin API). This path is in Athena's `SecurityConfig` permitAll carve-out — it does **not**
use the Keycloak JWT / OAuth flow.

Receiver-side idempotency: keyed on `(root_folder_id[from creds], sourceRepositoryId,
sourceNodeId)` (UNIQUE in `transfer_node_mappings`), watermark = `sourceLastModifiedAt`
**exact equality**. The **4-rule disposition matrix**: (1) mapping hit + watermark equal →
`UNCHANGED` (replay no-op); (2) mapping hit + watermark differs → `OVERWRITTEN` (new
version); (3) no mapping + name conflict → governed by `conflictPolicy`
(`SKIP`/`RENAME`/`OVERWRITE`); (4) else → `CREATED`. There is **no content-checksum** in
this decision.

## 3. Locked decisions

- **D1 — Surface.** Target the Transfer Receiver `/documents` endpoint (multipart). The
  #768 `AthenaCmisPublicationAdapter` + `PUBLICATION_ECM_*` CMIS settings are **downgraded to
  a compliance reference** (see D11).

- **D2 — Identity folding (load-bearing).** The receiver accepts ONE `sourceNodeId` UUID as
  the dedupe discriminator; our key is a 5-tuple. Fold deterministically:
  `sourceNodeId = uuid5(NAMESPACE_PLM, "item_id|version_id|file_id|file_role")`.
  `version_id` **and** `file_role` MUST be in the hash (else two roles/versions of one item
  collide on one mapping row). `sourceRepositoryId` = a stable per-PLM-instance constant (new
  setting `PUBLICATION_ECM_SOURCE_REPOSITORY_ID`, e.g. `"yuantus-plm"`). `target_system` maps
  to the **receiver registration** (one registration per PLM source), not into the hash.

- **D3 — Watermark.** `sourceLastModifiedAt` = the version's **fixed publish timestamp**
  (`ItemVersion.released_at`), ISO-8601, **stable across retries — never `now()`**. Because
  controlled CAD files are immutable per version: replay → Rule 1 `UNCHANGED` (clean
  at-least-once); a content change only ever appears as a **new `version_id`** → new
  `sourceNodeId` → `CREATED` (distinct node). If `released_at` is null, fall back to a
  deterministic stamp derived from the content fingerprint — but never a wall-clock at send
  time (that breaks Rule 1 and, under default RENAME, spawns `(Replica N)` duplicates).

- **D4 — conflictPolicy.** Send an explicit policy, **never the default `RENAME`**. Since a
  stable `sourceNodeId` means Rules 1/2 (mapping-based) normally govern, `conflictPolicy`
  only bites the no-mapping + name-collision edge (a same-named doc from another source under
  our folder). **Recommend `SKIP`** (do not clobber a doc we didn't map; record the returned
  existing `documentId` and flag for reconciliation). *To ratify with ops: `SKIP` vs
  `OVERWRITE`.*

- **D5 — Version model.** **Distinct Athena node per PLM version** (each `version_id` → its
  own `sourceNodeId` → its own node), **not** Athena's internal version chain. Matches PLM's
  immutable-version model and keeps the per-file at-least-once key clean.

- **D6 — Auth.** Custom headers `X-Athena-Transfer-User` / `X-Athena-Transfer-Secret`
  matching a `TransferReceiverRegistration` provisioned **per `target_system`** on Athena.
  New PLM settings: `PUBLICATION_ECM_TRANSFER_USER`, `PUBLICATION_ECM_TRANSFER_SECRET`
  (never logged). The OAuth `ATHENA_*` settings + the async `AthenaClient` flow are **not**
  the auth path for this surface. Provisioning the registration (+ a dedicated credential) is
  an **Athena-side / ops prerequisite** for go-live.

- **D7 — Dispatch reads bytes.** The **enqueue path stays byte-free** (unchanged). The
  **worker's send path** gains a content-fetch: read the controlled file's bytes via the
  storage provider at dispatch time and stream them as the multipart `file` part. v1 may
  buffer with a size cap + a clear `remote_error`/terminal split on read failure; streaming
  large CAD files is a follow-up (the reference sender buffers in memory).

- **D8 — Folder resolution.** `parentFolderId` (UUID) must be resolved/pre-provisioned.
  Strategy: a configured root folder (`PUBLICATION_ECM_ROOT_FOLDER_ID`) + ensure
  per-`item`/`version` subfolders via `POST /folders` (create-or-get, conflict-policy'd), and
  optionally `GET /verify?folderId=` to confirm the folder + `repositoryId` before pushing.
  *To ratify: nested `/item/version` folders vs a flat folder with identity in the node name.*

- **D9 — Outbox persistence.** Persist the returned `documentId` (+ `disposition`) onto the
  outbox row (`properties.athena_document_id`, `properties.athena_disposition`). The response
  does **not** echo our key, so the outbox owns the `plm_key → documentId` mapping. (Slots
  into the existing `properties.remote_id` write.)

- **D10 — Success/error semantics.** `disposition ∈ {CREATED, RENAMED, OVERWRITTEN,
  UNCHANGED, SKIPPED}` → all **SENT** (UNCHANGED/SKIPPED are idempotent no-ops, **not**
  failures). Map onto the worker's existing classification: 5xx/timeout/429/408/401/403 →
  `remote_error` (retryable); a credential/scope `SecurityException` (403-equivalent for a
  wrong folder/cred) and **quota rejection** → terminal (`validation_error`-class), not
  retry-forever. Distinguish on `disposition`, **not** the HTTP 2xx subtype (UNCHANGED is
  also 201).

- **D11 — #768 disposition.** Keep `cmis_adapter.py` as a **compliance reference** (clearly
  marked, default-off, never resolved) OR remove it; repoint `resolve_adapter` to the new
  `AthenaTransferReceiverAdapter`. *Recommend: keep + relabel* (it documents the CMIS contract
  we verified). The `PUBLICATION_ECM_TARGET_SYSTEM` gate semantics carry over to the new
  adapter.

- **D12 — Integrity.** The receiver does **not** validate content checksum. PLM asserts
  integrity before send (we hold the fingerprint) and **optionally** reads back
  `athena:contentHash` (or the version) to compare post-send. *To ratify: verify-after-send
  yes/no.*

## 4. Phase 0 (live) verification — against the real contract

When a live Athena + a provisioned receiver registration are available, run:
- **U1** — `GET /verify?folderId=` with the PLM credential returns 200 + the expected
  `repositoryId`; a wrong/foreign folder → 403-equivalent (cred-scope check).
- **U2** — `POST /folders` ensures the `/PLM/<item>/<version>` (or chosen) tree idempotently.
- **U3** — `POST /documents` with a real controlled file → `201 CREATED`, `documentId`
  persisted; the bytes land (content hash matches PLM fingerprint).
- **U4** — **replay the same row** (stable `sourceNodeId` + `sourceLastModifiedAt`) →
  `UNCHANGED`, no duplicate node (the core at-least-once guarantee).
- **U5** — a new `version_id` of the same file → new `sourceNodeId` → `CREATED` (distinct
  node), confirming the immutable-version model; and confirm a credential/quota failure
  surfaces as a terminal (non-retry-forever) outcome.

## 5. Out of scope / deferred

- Streaming large-file multipart (v1 buffers with a size cap).
- The **kill-switch-at-dispatch** decision (carried from #767): a running worker drains
  unconditionally; decide whether the drain path also honors `ECM_PUBLISH_ENABLED`.
- OAuth client-credentials is **N/A** for this surface (Transfer uses header creds), so the
  earlier OAuth forward-flag is moot for the production path; the `AthenaClient` OAuth flow
  remains only for health/other Athena calls.

## 6. Open items to confirm at build time

- The exact `TransferReceiverRegistration` provisioning (who creates it; whether a dedicated
  service account is required; authType choice BASIC vs BEARER).
- The precise `/verify` + `/folders` request/response shapes (re-read at implementation; the
  auth-detail reader was rate-limited during the mapping, though the Transfer + CMIS readers
  covered the auth model).
- Secret handling: Athena stores the receiver secret in plaintext and compares with
  `Objects.equals` — provision a strong, rotation-capable credential; never log it PLM-side.
