# Product SKU Matrix

## Purpose

Give sales, delivery, and engineering one shared packaging view for the current PLM and Metasheet product line.

The governing rule is:

- product strategy: layered selling
- engineering strategy: shared contract, separate implementations
- deployment strategy: profile-based delivery

## SKU Matrix

| SKU | Delivery Profile | Included Runtime | Front-End Positioning | Target Customer | Quote Band | Sales Note |
| --- | --- | --- | --- | --- | --- | --- |
| `PLM Base` | `base` | Yuantus backend + embedded workbench/admin console | Admin/operator console, not yet a daily end-user PLM front-end | Customers with their own portal/front-end team, SI-led projects, backend-first enterprise IT teams | Entry | Sell as authoritative PLM core with embedded admin surface |
| `PLM Collaboration Pack` | `collab` | `PLM Base` + saved views + bounded batch edit + lightweight automation + limited portals/forms | Expanded PLM operator surface, still not the primary customer-grade front-end | Same as `PLM Base`, but needing more self-service collaboration around PLM data | Entry+ | Keep scope PLM-bound; do not pitch this as a generic low-code platform |
| `Metasheet Platform` | `metasheet-standalone` or `combined` when paired with PLM | Metasheet backend + web app + platform modules | Organization-level collaboration, portal, dashboard, and app shell | Departmental and enterprise collaboration buyers needing a flexible work platform | Platform | Can be sold standalone or attached to PLM, Athena, and Dedup |
| `All-in-One / Combined` | `combined` | Yuantus + Metasheet + optional Athena + optional Dedup | Customer-facing front-end primarily provided by Metasheet; Yuantus remains authoritative PLM backend | Default offer for most manufacturing customers that want a usable front-end out of the box | Enterprise | Best fit for customers expecting an immediately usable product surface rather than backend-led integration |

## Short Sales Guidance

### What to Lead With

- For most manufacturing customers, lead with `All-in-One / Combined`.
- For customers with strong internal IT or existing portals, lead with `PLM Base` or `PLM Collaboration Pack`.
- For non-PLM digital operations opportunities, lead with `Metasheet Platform`.

### What Not to Overpromise

- `PLM Base` is not the final polished daily end-user front-end today.
- `PLM Collaboration Pack` is not a generic app builder.
- `Metasheet Platform` does not replace PLM object authority.

## Positioning Summary

### Yuantus / PLM

Owns:

- item/BOM/version/ECO/release authority
- approval state tied to PLM objects
- document relationships tied to PLM objects

### Metasheet

Owns:

- collaborative workspace shell
- dashboards and portals
- automation for non-PLM and cross-system coordination
- customer-facing front-end in the combined offer

## Default Packaging Rule

If the buyer asks for:

- strict PLM authority and backend integration -> `PLM Base`
- PLM plus lightweight collaboration around the same objects -> `PLM Collaboration Pack`
- usable front-end across teams from day one -> `All-in-One / Combined`
- broader work platform beyond PLM -> `Metasheet Platform`

## Follow-Up Assets

This matrix should be read together with:

- [PLM_STANDALONE_METASHEET_BOUNDARY_STRATEGY_20260407.md](/Users/huazhou/Downloads/Github/Yuantus/docs/PLM_STANDALONE_METASHEET_BOUNDARY_STRATEGY_20260407.md)
- [WORKFLOW_OWNERSHIP_RULES.md](/Users/huazhou/Downloads/Github/Yuantus/docs/WORKFLOW_OWNERSHIP_RULES.md)
- [PACT_FIRST_INTEGRATION_PLAN_20260407.md](/Users/huazhou/Downloads/Github/Yuantus/docs/PACT_FIRST_INTEGRATION_PLAN_20260407.md)
