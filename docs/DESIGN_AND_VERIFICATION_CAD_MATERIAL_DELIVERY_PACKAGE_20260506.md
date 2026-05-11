# CAD Material Delivery Package Design And Verification

## Goal

把 CAD Material Sync 从“本机有代码”收敛为“Yuantus 仓库可交付、可重新 clone、可继续验证”的交付包。重点解决三个问题：

- AutoCAD 客户端迁入 Yuantus 后有明确 manifest。
- 换电脑前知道哪些源码、脚本、fixture 和文档必须进入 Git。
- macOS 上有一个入口可以验证服务端插件、AutoCAD 客户端契约和交付包完整性。

## Design

新增交付验证入口：

- `scripts/verify_cad_material_delivery_package.py`
- `scripts/print_cad_material_delivery_git_commands.sh`

验证内容：

- 必要交付文件存在，包括 `clients/autocad-material-sync/`、服务端插件、测试、fixture 和关键设计文档。
- `clients/autocad-material-sync` 下没有 `bin/`、`obj/`、`*.dll`、`*.pdb` 等构建产物。
- 迁移范围内不再引用旧 PLM AutoCAD 客户端路径或本机绝对 workspace 路径。
- 迁移范围内文本文件没有尾随空白。
- AutoCAD 客户端静态验证通过。
- CAD mock drawing fixture 通过。
- CAD fixture 到 Yuantus 插件 e2e 通过。
- SQLite DB create/update/outbound e2e 通过。
- `/diff/preview` contract fixture 通过。
- Python 验证脚本可编译。
- AutoCAD project、WPF XAML 和 PackageContents XML 可解析。

新增客户端 manifest：

- `clients/autocad-material-sync/MANIFEST.md`
- `docs/CAD_MATERIAL_SYNC_GITHUB_HANDOFF_20260506.md`

manifest 说明：

- 目录职责。
- 关键源码文件。
- macOS 本地验证入口。
- Windows + AutoCAD 2018 验收入口。
- 不应提交的构建产物边界。
- GitHub 分支、新电脑继续步骤和 Windows AutoCAD 2018 后续验证边界。

新增 Git staging 指令打印器：

- `scripts/print_cad_material_delivery_git_commands.sh --review-cmds`
- `scripts/print_cad_material_delivery_git_commands.sh --git-add-cmd`

它只覆盖 CAD Material Sync 交付包，不包含 `.claude/`、`local-dev-env/` 和 `docs/DELIVERY_DOC_INDEX.md`。

## Commit Boundary

建议单独提交 CAD Material Sync 交付包，至少包含：

- `clients/autocad-material-sync/`
- `plugins/yuantus-cad-material-sync/`
- `src/yuantus/web/workbench.html`
- `src/yuantus/api/tests/test_workbench_router.py`
- `src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py`
- `scripts/verify_cad_material_diff_confirm_contract.py`
- `scripts/verify_cad_material_delivery_package.py`
- `scripts/print_cad_material_delivery_git_commands.sh`
- `playwright/tests/cad_material_workbench_ui.spec.js`
- `docs/CAD_MATERIAL_SYNC_GITHUB_HANDOFF_20260506.md`
- `docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_*.md`
- `docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_PLUGIN_20260506.md`
- `docs/samples/cad_material_diff_confirm_fixture.json`

精确 staging 指令可由脚本打印：

```bash
bash scripts/print_cad_material_delivery_git_commands.sh --git-add-cmd
```

不要在本功能提交中纳入：

- `.claude/`
- `local-dev-env/`
- `docs/DELIVERY_DOC_INDEX.md` 的本地脏改动
- `tmp/`
- `node_modules/`
- AutoCAD `bin/`、`obj/`、DLL/PDB/EXE 输出

## Verification

一键交付验证：

```bash
python3 scripts/verify_cad_material_delivery_package.py
```

结果：

```text
OK: CAD material delivery package verification passed
```

服务端插件和 Workbench 目标 pytest：

```bash
PYTHONPATH=src python3 -m pytest src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py src/yuantus/api/tests/test_workbench_router.py -q
```

结果：

```text
46 passed, 1 warning in 4.13s
```

脚本内部已执行：

```bash
python3 clients/autocad-material-sync/verify_material_sync_static.py
python3 clients/autocad-material-sync/verify_material_sync_fixture.py
python3 clients/autocad-material-sync/verify_material_sync_e2e.py
python3 clients/autocad-material-sync/verify_material_sync_db_e2e.py
python3 scripts/verify_cad_material_diff_confirm_contract.py
python3 -m py_compile clients/autocad-material-sync/verify_material_sync_static.py clients/autocad-material-sync/verify_material_sync_fixture.py clients/autocad-material-sync/verify_material_sync_e2e.py clients/autocad-material-sync/verify_material_sync_db_e2e.py scripts/verify_cad_material_diff_confirm_contract.py plugins/yuantus-cad-material-sync/main.py src/yuantus/meta_engine/tests/test_plugin_cad_material_sync.py
xmllint --noout clients/autocad-material-sync/CADDedupPlugin/CADDedupPlugin.csproj clients/autocad-material-sync/CADDedupPlugin/MaterialSyncDiffPreviewWindow.xaml clients/autocad-material-sync/CADDedupPlugin/PackageContents.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2018.xml clients/autocad-material-sync/CADDedupPlugin/PackageContents.2024.xml
```

限定 diff check：

```bash
git diff --check -- scripts/verify_cad_material_delivery_package.py clients/autocad-material-sync docs/DESIGN_AND_VERIFICATION_CAD_MATERIAL_DELIVERY_PACKAGE_20260506.md docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_PLUGIN_20260506.md README.md
```

结果：无输出，表示本轮交付包改动没有空白错误。

Git 指令打印器语法验证：

```bash
bash -n scripts/print_cad_material_delivery_git_commands.sh
bash scripts/print_cad_material_delivery_git_commands.sh --git-add-cmd
```

结果：语法通过，并输出 17 行精确 `git add -- ...` pathspec。

## Remaining Boundary

macOS 仍不能替代 Windows + AutoCAD 2018 实机验收。真实验收仍需：

```powershell
cd clients\autocad-material-sync
powershell -ExecutionPolicy Bypass -File .\verify_autocad2018_preflight.ps1 -RunBuild
```

然后在 AutoCAD 2018 中执行 `NETLOAD` 和 `PLMMAT*` 命令，验证真实 DWG 标题栏/明细表读写。
