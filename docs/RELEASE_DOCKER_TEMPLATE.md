# Docker Release Template

Use this template once a registry is available.

## Prerequisites

- Docker logged in to the registry
- Access to push `yuantus-api` and `yuantus-worker`

## Build & Push

```bash
REGISTRY=ghcr.io/your-org TAG=v0.1.3 \
  scripts/release_docker.sh
```

## Example Tags

- `ghcr.io/your-org/yuantus-api:v0.1.3`
- `ghcr.io/your-org/yuantus-worker:v0.1.3`
