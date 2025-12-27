# Day 35 - CAD Filename Parsing

## Scope
- Parse revision from `.prt/.asm.<rev>` filenames.
- Ensure generic local extraction defers to filename fallback.

## Verification - CAD Filename Parsing

Command:

```bash
bash scripts/verify_cad_filename_parse.sh
```

Result:

```text
ALL CHECKS PASSED
```

Notes:
- Samples: model2.prt.1, J2824002-06上封头组件v2.dwg, 比较_J2825002-09下轴承支架组件v2.dwg
