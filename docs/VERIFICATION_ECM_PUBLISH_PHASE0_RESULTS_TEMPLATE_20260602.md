# VERIFICATION — ECM Publish Phase 0 Results

> Fill this from `scripts/ecm_publish_phase0/smoke.py` output. This file, completed,
> is the **Phase 0 gate artifact** that unblocks Phase 1 coding.
>
> Run by: ______ · Date: ______ · Athena ver/commit: ______ · Keycloak realm: ______

## Findings

| ID | Question | Result | Notes / evidence |
|----|----------|--------|------------------|
| **U1** | Keycloak **realm role** Athena accepts for CMIS write | role = `______` ; accepted? ☐ yes ☐ no | token `realm_access.roles` = `______` |
| **U2** | Version-producing **call sequence** (test on **two separate docs**) | ☐ 2-call `createDocument`→`setContentStream` <br> ☐ 3-call `createDocument`→`checkOut`→`checkIn(PWC)` | path A version count/label = ______ · path B = ______ |
| **U3** | Property **key path** + search | ☐ bare `plm_part` <br> ☐ needs `athena:property.*` (via `updateProperties`) | **MANUAL** via Athena Node/Search API (CMIS read-back may omit custom props): does `properties.plm_part` find it? ☐ yes ☐ no |
| **U4** | `X-Tenant-ID` routing | ☐ correct tenant ☐ wrong/none | landed under node path: ______ |
| **U5** | `createFolder Released/<part>` | ☐ works (id `______`) ☐ fails | error if any: ______ |

## Decisions these lock (feed back into the design / adapter)

- **Adapter CMIS sequence** = ______ (from U2).
- **Property write/query** = bare keys at `createDocument`, query `properties.<key>` ☐ confirmed / ☐ switch to `athena:property.*` (from U3).
- **Service-account role** to provision in Keycloak = ______ (from U1).
- **Tenant→base-folder** recipe confirmed for `tenant-1` = ______ (from U4/U5).

## Go / No-Go

- ☐ **GO** — all five answered; Phase 1 coding may start.
- ☐ **BLOCKED** — open items: ______________________________________________

## Anything surprising
(record any Athena response shape that differs from the design's assumptions — e.g. objectId path, error envelope, content-stream behavior)

______________________________________________
