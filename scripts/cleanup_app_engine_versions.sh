#!/usr/bin/env bash
#
# cleanup_app_engine_versions.sh
#
# Deletes all non-serving App Engine versions (versions receiving 0%
# traffic), keeping only the version(s) currently serving traffic.
#
# Usage:
#   ./scripts/cleanup_app_engine_versions.sh [PROJECT_ID] [SERVICE]
#
# Arguments:
#   PROJECT_ID - GCP project ID (optional, defaults to current gcloud
#                config)
#   SERVICE    - App Engine service name (optional, defaults to
#                'default')
#
# Exit codes:
#   0 - Success (versions deleted or none to delete)
#   1 - Error (invalid arguments, gcloud command failed, etc.)

set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null)}"
SERVICE="${2:-default}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: PROJECT_ID not provided and no default project set"
  echo "Usage: $0 [PROJECT_ID] [SERVICE]"
  exit 1
fi

echo "==> Cleaning up App Engine versions for project: ${PROJECT_ID}"
echo "==> Service: ${SERVICE}"

# Get all versions for the service
ALL_VERSIONS=$(gcloud app versions list \
  --project="${PROJECT_ID}" \
  --service="${SERVICE}" \
  --format="value(version.id)" \
  --sort-by="~version.createTime" 2>/dev/null || true)

if [[ -z "${ALL_VERSIONS}" ]]; then
  echo "==> No versions found for service '${SERVICE}'"
  exit 0
fi

# Get versions receiving traffic (serving versions)
SERVING_VERSIONS=$(gcloud app versions list \
  --project="${PROJECT_ID}" \
  --service="${SERVICE}" \
  --hide-no-traffic \
  --format="value(version.id)" 2>/dev/null || true)

if [[ -z "${SERVING_VERSIONS}" ]]; then
  echo "WARNING: No serving versions found. Skipping cleanup."
  exit 0
fi

echo "==> Serving versions (will be kept):"
echo "${SERVING_VERSIONS}" | sed 's/^/    /'

# Find versions to delete (all versions minus serving versions)
VERSIONS_TO_DELETE=""
while IFS= read -r version; do
  if ! echo "${SERVING_VERSIONS}" | grep -qx "${version}"; then
    VERSIONS_TO_DELETE="${VERSIONS_TO_DELETE}${version}"$'\n'
  fi
done <<< "${ALL_VERSIONS}"

# Remove trailing newline
VERSIONS_TO_DELETE=$(echo -n "${VERSIONS_TO_DELETE}")

if [[ -z "${VERSIONS_TO_DELETE}" ]]; then
  echo "==> No old versions to delete. All versions are serving traffic."
  exit 0
fi

VERSION_COUNT=$(echo "${VERSIONS_TO_DELETE}" | wc -l | tr -d ' ')
echo "==> Found ${VERSION_COUNT} old version(s) to delete:"
echo "${VERSIONS_TO_DELETE}" | sed 's/^/    /'

# Delete versions one by one (gcloud doesn't support batch delete)
echo "==> Deleting old versions..."
while IFS= read -r version; do
  if [[ -n "${version}" ]]; then
    echo "    Deleting version: ${version}"
    gcloud app versions delete "${version}" \
      --project="${PROJECT_ID}" \
      --service="${SERVICE}" \
      --quiet 2>&1 | sed 's/^/      /' || {
        echo "    WARNING: Failed to delete version ${version}"
      }
  fi
done <<< "${VERSIONS_TO_DELETE}"

echo "==> Cleanup complete!"

# Show remaining versions
echo "==> Remaining versions:"
gcloud app versions list \
  --project="${PROJECT_ID}" \
  --service="${SERVICE}" \
  --format="table(version.id,traffic_split,last_deployed_time.date())" \
  --sort-by="~version.createTime"
