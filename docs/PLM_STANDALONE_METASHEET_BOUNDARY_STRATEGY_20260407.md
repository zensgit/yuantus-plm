# PLM Standalone vs Metasheet Platform Boundary Strategy

## Goal

Define a product and implementation boundary that allows:

1. `Yuantus / PLM` to ship as a complete standalone SKU with its own front-end.
2. `Metasheet2` to continue evolving into a broader collaboration platform without duplicating PLM core.
3. The lightweight "sheet/workflow/front-desk" capabilities inside PLM to remain a subset of the fuller Metasheet platform.

This document is intentionally grounded in the current repositories:

- Yuantus already contains reusable metadata and workflow primitives in
  [src/yuantus/meta_engine/views/models.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/views/models.py),
  [src/yuantus/meta_engine/views/mapping.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/views/mapping.py),
  [src/yuantus/meta_engine/workflow/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/workflow/service.py),
  [src/yuantus/meta_engine/approvals/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/approvals/service.py),
  and
  [src/yuantus/meta_engine/app_framework/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/app_framework/service.py).
- Yuantus already exposes an embedded front-end through
  [src/yuantus/api/routers/workbench.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/api/routers/workbench.py)
  backed by
  [src/yuantus/web/workbench.html](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/web/workbench.html),
  and the page is already public-routed in
  [src/yuantus/api/middleware/auth_enforce.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/api/middleware/auth_enforce.py).
- Yuantus already has a strong query surface through
  [src/yuantus/meta_engine/web/query_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/query_router.py)
  and `AMLQueryService`, so the system is not starting from a blank "view engine" state.
- Metasheet2 already shows the shape of a more productized PLM workspace in
  `/Users/huazhou/Downloads/Github/metasheet2/apps/web/src/views/PlmProductView.vue`
  and
  `/Users/huazhou/Downloads/Github/metasheet2/apps/web/src/components/plm/PlmWorkbenchShell.vue`.
- Metasheet2 also already speaks to Yuantus in `yuantus` mode through
  `/Users/huazhou/Downloads/Github/metasheet2/packages/core-backend/src/data-adapters/PLMAdapter.ts`,
  including auth, search, AML detail, BOM tree, where-used, compare, substitutes, files, and ECO-backed approval actions.

## Core Positioning

### Yuantus / PLM

Yuantus remains the system of record for:

- item master data
- BOM / version / baseline
- ECO / lifecycle / release
- approval state and audit trail
- document references and CAD-oriented domain logic

It must have its own native front-end when sold standalone.

### Metasheet2

Metasheet2 becomes the organization-level collaboration shell for:

- flexible tabular workspaces
- saved views across teams
- dashboards and executive portals
- automation and event-driven coordination
- supplier/project/department portals
- cross-system composition across PLM, Athena, and Dedup

It must not replace PLM core rules. It should orchestrate around them.

## Product Rule

The PLM-embedded collaboration layer must always stay **PLM-bound**, not generic.

That means the embedded capabilities may operate on:

- item
- BOM
- ECO
- approval
- release
- document reference

But they should not expose:

- arbitrary user-defined tables
- generic app building
- plugin marketplace behavior
- cross-system workflow composition
- organization-wide dashboarding as a primary product surface

## Recommended Front-End Layering

### Layer 1: Yuantus Native PLM Front-End

This is mandatory for standalone PLM and should be treated as the official customer-facing product surface.

It should include:

- object search and navigation
- item detail pages
- BOM view and edit flows
- version and baseline views
- ECO and release workspace
- approval inbox and approval actions
- document association and sync status
- admin/config/integration status pages

This layer should be organized around objects and workflows, not around API buttons.

### Layer 2: Yuantus Embedded Lightweight Collaboration

This is where simplified "Metasheet-like" capabilities belong inside standalone PLM.

Allowed:

- saved list views per object type
- column selection, sorting, filtering
- batch edit for PLM-safe fields
- approval inbox / task inbox
- limited role-specific forms
- simple event actions inside PLM, such as "after approval, create release task"

Not allowed:

- generic base/table creation
- open-ended low-code app builder
- cross-system automation editor
- plugin marketplace UX
- company-wide cockpit as a primary PLM dependency

### Layer 3: Metasheet Platform

This remains the full collaboration platform and upsell path.

It should own:

- multi-app navigation
- generic data apps
- automation builder
- dashboards and executive reporting
- portals for external and internal stakeholders
- cross-system views over PLM, Athena, Dedup, and future services

## Capability Boundary Matrix

| Capability | Yuantus Standalone | Metasheet Platform | Notes |
| --- | --- | --- | --- |
| Item/BOM/ECO/Release UI | Yes | Read/write via adapters | Core PLM domain stays in Yuantus |
| Approval inbox | Yes | Yes | Metasheet can surface it, not redefine it |
| Saved views | Yes, PLM-bound only | Yes, generic and richer | Same concept, different scope |
| Batch edit | Yes, safe scoped fields | Yes, broader workflows | Yuantus should enforce PLM rules |
| Supplier portal | Limited PLM forms | Full portal builder | Standalone PLM gets restricted entry forms |
| Automation | Basic PLM event actions | Full automation platform | Yuantus only supports narrow recipes |
| Dashboard / BI | Minimal operational views | Full org-wide dashboards | Keep PLM product focused |
| App marketplace | No | Yes | Avoid product overlap |
| Generic schema/table builder | No | Yes | Hard boundary |

## Shared Contract Strategy

The right goal is **shared semantics and reusable service contracts**, not shared runtime code.

Because Yuantus and Metasheet2 are different stacks, the integration kernel should live in:

- versioned domain APIs
- OpenAPI / JSON schema
- Pact contracts
- shared object semantics
- workflow and approval contracts
- event schemas
- auth and identity conventions

Do not make cross-repo UI component reuse or shared runtime libraries a hard requirement. The product stacks are different enough that trying to share more than contracts will create drag, service sprawl, or rewrite pressure.

The operative rule is:

- contract shared
- implementation separate
- ownership explicit

## Current Integration Baseline

The strategy should build on what already works today.

### Existing Yuantus Standalone Surface

Yuantus already has a standalone front-end entry at `/api/v1/workbench` through
[src/yuantus/api/routers/workbench.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/api/routers/workbench.py).

This is not yet the final customer-grade PLM workspace, but it is already:

- an embedded front-end
- a standalone deployment surface
- a valid base for `PLM Base`

### Existing Query Core

Yuantus already exposes:

- `POST /api/v1/aml/query`
- `GET /api/v1/aml/{item_type}/{item_id}`
- `POST /api/v1/aml/bom/explode`
- `POST /api/v1/aml/where-used`

through
[src/yuantus/meta_engine/web/query_router.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/web/query_router.py).

That means "view/query core" already exists and should be strengthened, not redesigned from scratch.

### Existing Metasheet Federation Path

Metasheet2 already contains a Yuantus-aware adapter in
`/Users/huazhou/Downloads/Github/metasheet2/packages/core-backend/src/data-adapters/PLMAdapter.ts`.

The practical meaning is:

- the two systems are already connected by HTTP contracts
- the most urgent engineering task is to freeze and verify those contracts
- the wrong move now would be to replace that path with an abstract shared-runtime idea

## What Can Be Reused from Yuantus Today

### Metadata-Driven Views

Yuantus already has definitions for forms and grid views in:

- [src/yuantus/meta_engine/views/models.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/views/models.py)
- [src/yuantus/meta_engine/views/mapping.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/views/mapping.py)

These are a strong base for:

- object list layouts
- role-specific forms
- mobile/desktop mapping

What is still missing is persistence and API support for **user/team saved views** instead of only static admin-defined layouts.

### Workflow and Inbox Foundations

Yuantus already has workflow execution and pending task retrieval in:

- [src/yuantus/meta_engine/workflow/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/workflow/service.py)

That can back:

- task inbox
- process transitions
- lightweight approval/task center in the PLM front-end

### Generic Approval Backbone

Yuantus already has a reusable approval state machine in:

- [src/yuantus/meta_engine/approvals/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/approvals/service.py)

That is the right domain anchor for:

- approval inbox
- approval lifecycle cards
- request detail
- decision audit history

### App/Extension Registry

Yuantus already has a lightweight extension registry in:

- [src/yuantus/meta_engine/app_framework/models.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/app_framework/models.py)
- [src/yuantus/meta_engine/app_framework/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/app_framework/service.py)

This is useful for:

- PLM module packaging
- feature gating
- menu/extension points inside the native PLM front-end

It should not be allowed to drift into a full end-user app marketplace inside standalone PLM.

## Workflow Engine Ownership

This boundary must be explicit, otherwise both products will grow overlapping workflow features.

### Yuantus Owns All PLM Object Workflows

Anything that changes PLM object state must be executed by Yuantus-owned workflow and approval APIs.

Examples:

- ECO approval
- item release
- BOM governance transitions
- version/release gates
- supplier review when the decision mutates PLM object state

The reason is simple: the state machine, object integrity rules, and release cascade live in Yuantus.

### Metasheet Owns Non-PLM Workflows

Metasheet BPMN should be used for workflows that do not own PLM object state.

Examples:

- onboarding
- reimbursement
- department requests
- internal coordination workflows

### Gray-Zone Rule

If a workflow touches a PLM object, Yuantus remains the authority and Metasheet may provide:

- UI
- portal entry
- inbox experience
- orchestration around the PLM call

But the actual state transition still goes through Yuantus APIs.

## What the Current Workbench Should Become

The current workbench in
[src/yuantus/web/workbench.html](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/web/workbench.html)
should be retained, but explicitly positioned as:

- operator console
- QA / verification console
- integration and API exercise surface
- admin utility surface

It should **not** become the final customer-facing PLM workspace.

More precisely:

- it is already the embedded front-end for standalone deployment
- it should continue to exist
- it should evolve into a stronger admin/operator shell
- the customer-facing PLM workspace should be built next to it, not by forcing this page to absorb all product responsibilities

## Recommended Product Packaging

### SKU 1: PLM Base

Includes:

- native PLM workspace
- search, detail, BOM, version, ECO, release
- approval inbox
- document relationship surface
- minimal operational dashboards

### SKU 2: PLM Collaboration Pack

Adds:

- saved views
- batch edit
- limited external forms
- simple PLM automation recipes
- team work queues and role-based workspaces

This pack still stays PLM-bound.

### SKU 3: Metasheet Platform

Adds:

- generic work apps
- dashboards
- automation designer
- cross-system portals
- broader collaboration and departmental use cases

This becomes the natural upsell path instead of a replacement migration.

## Deployment Profiles

Commercial packaging should map cleanly to deployment shape.

### Profile A: PLM Base

Contains:

- Yuantus backend
- embedded Yuantus front-end

Suggested shape:

- `docker-compose -f base.yml -f yuantus.yml up`

### Profile B: PLM Collaboration Pack

Contains:

- Profile A
- saved views
- bounded batch edit
- lightweight automation
- limited portals/forms

Suggested shape:

- same Yuantus deployment
- feature flag or license gates such as `YUANTUS_ENABLE_COLLAB=true`

### Profile C: Combined

Contains:

- Profile A or B
- Metasheet backend and front-end
- adapter configuration pointing to Yuantus

Suggested shape:

- `docker-compose -f base.yml -f yuantus.yml -f metasheet.yml up`
- `PLM_API_MODE=yuantus`

The critical property is that upgrading from A or B to C should not require PLM data migration. Metasheet should remain a view/orchestration layer over Yuantus-owned PLM state.

## Engineering Guardrails

### 1. Pact-First Contract Protection

Before adding more product surface, protect the already-live cross-repo integration with Pact.

The immediate target is the existing Metasheet `PLMAdapter` to Yuantus route set:

- auth login
- health
- search
- AML detail
- BOM tree
- where-used
- BOM compare
- compare schema
- files
- ECO-backed approval actions

Without contract verification, "independent evolution" is just an assumption.

### 2. No Cross-System Database Coupling

Metasheet2 should not directly read or write PLM tables in production architecture.

Use:

- versioned APIs
- adapters
- read models
- event subscribers

This is consistent with the contract-first and anti-corruption-layer direction already identified in the external system strategy documents.

### 3. Versioned Domain Contracts First

Before building rich cross-product UI, stabilize versioned APIs for:

- item detail
- BOM detail and update
- ECO detail and transition
- approval request and transition
- release readiness and execution
- document references and sync state

### 4. Subset, Not Fork

The PLM-embedded lightweight collaboration features must be intentionally designed as a subset of the richer platform concepts.

Examples:

- Yuantus saved views = PLM-scoped subset of platform saved views
- Yuantus automation = recipe-based subset of platform automation
- Yuantus inbox = PLM-scoped task/approval slice of broader work management

### 5. Shared Concepts, Independent Rendering

Keep shared meanings aligned, but allow different front-ends to render them differently.

The shared contract is:

- object identity
- workflow state
- approval state
- action semantics
- event schema

Not:

- pixel-perfect shared UI implementation

### 6. No New Generic Domain Types Inside Yuantus

The embedded Yuantus front-end may only operate on AML-registered PLM domain objects and related projections.

Allowed:

- new BOM/ECO/item views
- inboxes over PLM workflow and approval state
- PLM-safe bulk editing

Not allowed:

- arbitrary user-created business tables
- unrelated non-PLM domain models
- generic workflow-owned app data inside Yuantus

This is the concrete implementation form of "Yuantus must not become a small Metasheet."

## Organizational Guardrails

Technical boundaries alone are not enough.

The following process rules should exist across both repos:

- document a hard "Yuantus must not do" list in contributor guidance
- require Metasheet review when Yuantus adds or changes public PLM endpoints
- require Yuantus review when Metasheet adds new PLM-facing adapter behavior
- review overlap quarterly: views, automation, inbox, portals, workflow features

## Delivery Roadmap

### Phase 0: Lock the Contract

1. Add consumer Pact tests in Metasheet for the current Yuantus route set.
2. Add provider verification in Yuantus CI.
3. Freeze ownership and workflow engine boundary in writing.

### Phase A: Reframe the Current Yuantus Front-End

1. Keep the current workbench as an admin/operator console.
2. Create a dedicated `PLM Workspace` route and page family.
3. Organize the UI around objects and workflows:
   - left rail: search, object families, inbox
   - center: detail / BOM / versions / documents
   - right rail: approval / release / sync / activity

### Phase B: Add the Lightweight Collaboration Layer

1. Add saved PLM views.
2. Add bounded batch edit.
3. Add task and approval inbox pages.
4. Add limited external forms for supplier or reviewer participation.
5. Add a narrow set of automation recipes tied to PLM events.

### Phase C: Formalize the Platform Boundary

1. Publish stable PLM APIs and event contracts.
2. Consume them from Metasheet2 through adapters only.
3. Build the richer platform experiences in Metasheet2:
   - dashboards
   - portals
   - generic data workspaces
   - broader automation

## Immediate Next Steps for Yuantus

The next practical build sequence should be:

1. Add Pact coverage for the current Metasheet-to-Yuantus route set before expanding the integration surface.
2. Introduce a dedicated native `PLM Workspace` page and route.
3. Reuse the current approval and release APIs from the new workspace.
4. Add a first-class inbox page backed by
   [src/yuantus/meta_engine/workflow/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/workflow/service.py)
   and
   [src/yuantus/meta_engine/approvals/service.py](/Users/huazhou/Downloads/Github/Yuantus/src/yuantus/meta_engine/approvals/service.py).
5. Add saved-view persistence for PLM object lists.
6. Keep workbench as the operator surface for API-level verification and advanced operations.

## Final Recommendation

The strategic answer is not "PLM or Metasheet".

It is:

- `Yuantus` ships a complete native PLM product with a bounded lightweight collaboration layer.
- `Metasheet2` becomes the broader platform shell and upsell path.
- both are connected by stable contracts and shared semantics, not duplicated business logic or shared runtime code.

That preserves standalone PLM viability, keeps the Metasheet platform ambition intact, and creates a clean commercial upgrade path instead of two overlapping products.
