#!/usr/bin/env sh

set -eu

python_bin="${YUANTUS_BOOTSTRAP_PYTHON:-python}"
tenant_id="${YUANTUS_BOOTSTRAP_TENANT_ID:-tenant-1}"
org_id="${YUANTUS_BOOTSTRAP_ORG_ID:-org-1}"
admin_username="${YUANTUS_BOOTSTRAP_ADMIN_USERNAME:-admin}"
admin_password="${YUANTUS_BOOTSTRAP_ADMIN_PASSWORD:-}"
admin_user_id="${YUANTUS_BOOTSTRAP_ADMIN_USER_ID:-1}"
admin_roles="${YUANTUS_BOOTSTRAP_ADMIN_ROLES:-admin}"
viewer_username="${YUANTUS_BOOTSTRAP_VIEWER_USERNAME:-ops-viewer}"
viewer_password="${YUANTUS_BOOTSTRAP_VIEWER_PASSWORD:-}"
viewer_user_id="${YUANTUS_BOOTSTRAP_VIEWER_USER_ID:-2}"
viewer_roles="${YUANTUS_BOOTSTRAP_VIEWER_ROLES:-ops-viewer}"
skip_meta="${YUANTUS_BOOTSTRAP_SKIP_META:-0}"
dataset_mode="${YUANTUS_BOOTSTRAP_DATASET_MODE:-p2-observation}"
fixture_manifest_path="${YUANTUS_BOOTSTRAP_FIXTURE_MANIFEST_PATH:-./tmp/p2_observation_fixture_manifest.json}"

if [ -z "${admin_password}" ]; then
  echo "Missing required env: YUANTUS_BOOTSTRAP_ADMIN_PASSWORD" >&2
  exit 1
fi

if [ -z "${viewer_password}" ]; then
  echo "Missing required env: YUANTUS_BOOTSTRAP_VIEWER_PASSWORD" >&2
  exit 1
fi

echo "Running database migrations..."
"${python_bin}" -m yuantus db upgrade

if [ -n "${YUANTUS_IDENTITY_DATABASE_URL:-}" ]; then
  echo "Running identity migrations..."
  if [ "${YUANTUS_IDENTITY_MIGRATIONS_MODE:-identity-only}" = "full" ]; then
    "${python_bin}" -m yuantus db upgrade --identity
  else
    "${python_bin}" -m yuantus db upgrade --identity-only
  fi
else
  echo "Skipping identity migrations (empty YUANTUS_IDENTITY_DATABASE_URL)"
fi

echo "Seeding identity: ${admin_username} (bootstrap admin)"
"${python_bin}" -m yuantus seed-identity \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  --username "${admin_username}" \
  --password "${admin_password}" \
  --user-id "${admin_user_id}" \
  --roles "${admin_roles}"

echo "Seeding identity: ${viewer_username} (bootstrap non-superuser)"
"${python_bin}" -m yuantus seed-identity \
  --tenant "${tenant_id}" \
  --org "${org_id}" \
  --username "${viewer_username}" \
  --password "${viewer_password}" \
  --user-id "${viewer_user_id}" \
  --roles "${viewer_roles}" \
  --no-superuser

if [ "${skip_meta}" != "1" ]; then
  echo "Seeding meta..."
  "${python_bin}" -m yuantus seed-meta
else
  echo "Skipping meta seed (YUANTUS_BOOTSTRAP_SKIP_META=1)"
fi

case "${dataset_mode}" in
  none)
    echo "Skipping dataset seed (YUANTUS_BOOTSTRAP_DATASET_MODE=none)"
    ;;
  generic)
    echo "Seeding shared-dev generic demo data..."
    "${python_bin}" -m yuantus seed-data --tenant "${tenant_id}" --org "${org_id}"
    ;;
  p2-observation)
    echo "Seeding shared-dev P2 observation fixtures..."
    mkdir -p "$(dirname "${fixture_manifest_path}")"
    python ./scripts/seed_p2_observation_fixtures.py \
      --tenant "${tenant_id}" \
      --org "${org_id}" \
      --admin-user-id "${admin_user_id}" \
      --admin-username "${admin_username}" \
      --viewer-user-id "${viewer_user_id}" \
      --viewer-username "${viewer_username}" \
      --manifest-path "${fixture_manifest_path}"
    ;;
  *)
    echo "Unsupported YUANTUS_BOOTSTRAP_DATASET_MODE: ${dataset_mode}" >&2
    exit 1
    ;;
esac

cat <<EOF
Shared-dev bootstrap complete.

Create this local regression env file on the operator machine:

  \$HOME/.config/yuantus/p2-shared-dev.env

Suggested contents:
  BASE_URL="https://change-me-shared-dev-host"
  USERNAME="${admin_username}"
  PASSWORD="${admin_password}"
  TENANT_ID="${tenant_id}"
  ORG_ID="${org_id}"
  ENVIRONMENT="shared-dev"

Additional non-superuser smoke account:
  USERNAME="${viewer_username}"
  PASSWORD="${viewer_password}"

Dataset mode:
  ${dataset_mode}

Fixture manifest:
  ${fixture_manifest_path}
EOF
