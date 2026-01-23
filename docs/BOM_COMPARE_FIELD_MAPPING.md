# BOM Compare Field Mapping

This document provides a field-level mapping for BOM compare output and how
line keys are constructed for diffing.

Endpoints:
- `GET /api/v1/bom/compare/schema`
- `GET /api/v1/bom/compare`

---

## 1) Compare Output Structure (Summary)

`/api/v1/bom/compare` returns:

- `summary`: added/removed/changed counts with severity buckets
- `added[]` / `removed[]`: entries with `line` and `line_normalized`
- `changed[]`: entries with `before_line/after_line`, `before_normalized/after_normalized`, and `changes[]`

When `include_child_fields=true`, entries also include `parent` and `child`
metadata (id/config_id/item_number/name).

---

## 2) Line Field Mapping

The compare output standardizes a small set of line fields. These fields are
derived from relationship properties (`meta_items.properties` for the BOM line).

Defaults:
- By default, only `quantity/uom/find_num/refdes/effectivity_from/effectivity_to`
  are selected (see `_select_relationship_properties`).
- `effectivities` are only included when `include_effectivity=true`.
- `substitutes` are only included when `include_substitutes=true`.

Table:

| Field | Source (relationship properties) | Normalization | Severity | Inclusion |
| --- | --- | --- | --- | --- |
| quantity | `quantity` | decimal -> float | major | default |
| uom | `uom` | upper-case string | major | default |
| find_num | `find_num` | trimmed string | minor | default |
| refdes | `refdes` | split by `; , | whitespace`, upper-case, unique sorted list | minor | default |
| effectivity_from | `effectivity_from` | ISO datetime string | major | default |
| effectivity_to | `effectivity_to` | ISO datetime string | major | default |
| effectivities | derived from effectivity records (type/start/end/payload) | sorted tuples (type,start,end,payload) | major | only when `include_effectivity=true` |
| substitutes | derived from substitute relationships (item_id, rank, note) | sorted tuples (item_id, rank, note) | minor | only when `include_substitutes=true` |

Notes:
- `line_normalized` / `before_normalized` / `after_normalized` are JSON-safe.
  Internal tuples are converted to lists.
- If `include_relationship_props` is provided, only those keys are selected
  from `relationship.properties` (unless `include_effectivity/substitutes` are enabled).

---

## 3) Field Severity

Severity buckets are used for `summary.changed_*` and `changed[].severity`:

- `major`: quantity, uom, effectivity_from, effectivity_to, effectivities
- `minor`: find_num, refdes, substitutes
- `info`: any other field

---

## 4) Compare Modes

Compare modes map to line key strategies and property inclusion:

| Mode | line_key | include_relationship_props | aggregate_quantities |
| --- | --- | --- | --- |
| only_product | child_config | [] | false |
| summarized | child_config | [quantity, uom] | true |
| num_qty | child_config_find_num_qty | [quantity, uom, find_num] | false |
| by_position | child_config_find_num | [quantity, uom, find_num] | false |
| by_reference | child_config_refdes | [quantity, uom, refdes] | false |

When `aggregate_quantities=true`, duplicate lines under the same key are merged:
- quantities are summed
- UOM is merged; mixed values become `MIXED`

---

## 5) Line Key Strategies

The line key determines how two BOMs align lines for diffing.
All keys include parent + child context to avoid cross-parent collisions.

Legend:
- `P` = parent_config_id (fallback to parent_id)
- `C` = child_config_id (fallback to child_id)
- `p` = parent_id
- `c` = child_id
- `FN` = normalized find_num
- `RD` = normalized refdes (comma-joined)
- `Q` = normalized quantity
- `EFF` = normalized effectivity key (`effectivities` or from/to)

| line_key | Key format |
| --- | --- |
| child_config | `P::C` |
| child_id | `p::c` |
| relationship_id | `relationship_id` (fallback to `p::c`) |
| child_config_find_num | `P::C::FN` |
| child_id_find_num | `p::c::FN` |
| child_config_refdes | `P::C::RD` |
| child_id_refdes | `p::c::RD` |
| child_config_find_refdes | `P::C::FN::RD` |
| child_id_find_refdes | `p::c::FN::RD` |
| child_config_find_num_qty | `P::C::FN::Q` |
| child_id_find_num_qty | `p::c::FN::Q` |
| line_full | `p::c::FN::RD::EFF` |

---

## 6) Example Changed Entry (Minimal)

```json
{
  "relationship_id": "rel-123",
  "line_key": "ROOT::childA",
  "before_line": {"quantity": 1, "uom": "EA", "find_num": "10"},
  "after_line": {"quantity": 2, "uom": "EA", "find_num": "10"},
  "before_normalized": {"quantity": 1.0, "uom": "EA", "find_num": "10"},
  "after_normalized": {"quantity": 2.0, "uom": "EA", "find_num": "10"},
  "changes": [
    {
      "field": "quantity",
      "left": 1,
      "right": 2,
      "normalized_left": 1.0,
      "normalized_right": 2.0,
      "severity": "major"
    }
  ],
  "severity": "major"
}
```
