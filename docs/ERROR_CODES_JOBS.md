# Jobs 错误码清单

用于 job 失败诊断（`payload.error.code` / `cad_change_logs.payload.error_code`）。

## 通用错误码

- `handler_missing`  
  说明：任务类型没有注册处理器  
  处理：检查 worker 是否注册了该 task_type（cli.py / plugin worker 注册）

- `missing_file_id`  
  说明：任务 payload 缺少 `file_id`  
  处理：检查触发入口是否正确传递 file_id（/cad/import 或自定义 job）

- `file_not_found`  
  说明：数据库中找不到对应 file 记录  
  处理：确认 file_id 是否存在于 `meta_files`

- `source_missing`  
  说明：存储对象缺失（S3 key / 本地路径不存在）  
  处理：检查 `diagnostics.system_path`、`diagnostics.storage_exists`

- `connector_failed`  
  说明：CAD connector 调用失败  
  处理：检查 connector 服务健康、token、格式支持

- `fatal`  
  说明：任务抛出 JobFatalError（不可重试）  
  处理：查看 `payload.error.message` 确定具体原因

- `job_failed`  
  说明：通用失败（不可分类）  
  处理：查看 `payload.error.message` 与 `job.last_error`

## 使用建议

1) `GET /api/v1/jobs/{id}` 查看 `diagnostics` 与 `payload.error`  
2) `cad_change_logs` 查询 `job_failed` 记录（包含 error_code）  
3) 如为 `source_missing`，优先检查 S3/本地存储路径
