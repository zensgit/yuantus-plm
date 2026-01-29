#!/usr/bin/env bash
# Release helper: build & push docker images for yuantus
set -euo pipefail

REGISTRY="${REGISTRY:-}"
TAG="${TAG:-v0.1.3}"

if [[ -z "$REGISTRY" ]]; then
  echo "REGISTRY is required. Example: REGISTRY=ghcr.io/your-org" >&2
  exit 2
fi

API_IMAGE="${API_IMAGE:-${REGISTRY}/yuantus-api}"
WORKER_IMAGE="${WORKER_IMAGE:-${REGISTRY}/yuantus-worker}"

# Build images locally

docker build -t "${API_IMAGE}:${TAG}" -f Dockerfile .
docker build -t "${WORKER_IMAGE}:${TAG}" -f Dockerfile.worker .

# Push images

docker push "${API_IMAGE}:${TAG}"
docker push "${WORKER_IMAGE}:${TAG}"

echo "Pushed:"
echo "  ${API_IMAGE}:${TAG}"
echo "  ${WORKER_IMAGE}:${TAG}"
