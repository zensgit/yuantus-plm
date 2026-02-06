# CAD-ML Queue Smoke Report (DXF + Docker Attempt, 2026-02-05)

## Command
```
RUN_CAD_ML_DOCKER=1 CAD_PREVIEW_SAMPLE_FILE="docs/samples/cad_ml_preview_sample.dxf" CAD_ML_QUEUE_REPEAT=5 CAD_ML_QUEUE_WORKER_RUNS=6 CAD_ML_QUEUE_MUTATE=1 CAD_ML_QUEUE_CHECK_PREVIEW=1 YUANTUS_CAD_ML_BASE_URL="http://127.0.0.1:18000" scripts/verify_cad_ml_queue_smoke.sh http://127.0.0.1:7910 tenant-1 org-1
```

## Summary
- Result: FAILED (docker daemon not running)
- Error: `Cannot connect to the Docker daemon at unix:///Users/huazhou/.docker/run/docker.sock`
- Log: /tmp/verify_cad_ml_queue_smoke_dxf_quality_defaults_docker_20260205-222607.log

## Notes
- Attempted to launch Docker Desktop via CLI; AppleEvent timed out (-1712).
- Please start Docker Desktop manually, then rerun the command above.

## Troubleshooting checklist
- Open Docker Desktop manually and wait for the whale icon to show “Docker Desktop is running”.
- Verify daemon is up: `docker ps` should succeed without timeout.
- If the CLI hangs, restart Docker Desktop once from the UI, then retry.
- If the socket exists but still fails, check `docker context ls` to ensure `desktop-linux` is active.
- As a last resort, reboot the machine to clear stale Docker backend processes.
