# Phase 0 — ECM Publish verification kit

Run this **once** against a live Athena + Keycloak to turn the design's five
hypotheses into facts. It blocks Phase 1 coding (see
`../../docs/DESIGN_ECM_PUBLISH_RELEASE_TO_ECM_PHASE01_20260602.md` §5).

## Prereqs (owner / whoever has infra)

1. **Athena + Keycloak up.** Athena validates Keycloak JWTs; it has no own token endpoint.
2. **Keycloak service account**: a *confidential* client with **Service accounts roles** enabled.
   You must grant it an **Athena-accepted *realm* role** — the one Athena maps to document/CMIS
   write (check Athena's `SecurityConfig` role expectations). This is a **realm role** that shows up
   in the token's `realm_access.roles`, **not** a Keycloak *client* role. Which role works is **U1**.
3. **A base folder** in Athena under the target tenant's root; put its node id in `ATHENA_FOLDER_ID`.
   The script creates `Released-<run>/<part>` under it (proving nested createFolder, **U5**).

## Run

```bash
cd scripts/ecm_publish_phase0
cp .env.example .env && $EDITOR .env       # fill the 6 values
pip install httpx                          # if needed
set -a; source .env; set +a
python smoke.py
```

The script never prints the access token. It prints each request's raw response, probes
**two separate documents** for the two versioning paths, and ends with a **RESULTS** block.

## Record

Copy the answers into `../../docs/VERIFICATION_ECM_PUBLISH_PHASE0_RESULTS_TEMPLATE_20260602.md`
(path is relative to this folder) and commit it — that filled template is the Phase 0 gate
artifact that unblocks Phase 1.

| ID | Question | Why it matters |
|----|----------|----------------|
| U1 | Which **realm** role does Athena accept for CMIS write? | A token is not authz; the service account needs the right realm role. |
| U2 | Does `setContentStream` alone version, or is `checkOut`→`checkIn` required? | Fixes the adapter's call sequence. Tested on two separate docs; compare `cmisselector=versions` counts. |
| U3 | Is `plm_part` written + **searchable** as `properties.plm_part`? | **Manual check** — Athena's CMIS object read-back may omit custom props, so confirm via Athena's Node/Search API/UI. If bare keys don't search, retry `athena:property.*` via `updateProperties` and note it. |
| U4 | Does `X-Tenant-ID` route into the right tenant workspace? | The publish must land in the correct tenant. |
| U5 | Does nested `createFolder` (`Released/<part>`) work with the same token/tenant? | The worker creates this sub-folder per part. |

## Cleanup

Delete the test folder `Released-<run>` (and everything under it) from Athena afterwards.
If path B left the document checked out (a PWC), cancel that checkout.
