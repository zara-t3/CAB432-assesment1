#!/usr/bin/env bash
set -euo pipefail
HOST=${1:-"http://localhost:8080"}
TOKEN="$2"    # JWT
IMG="$3"      # image_id
seq 1 200 | xargs -I{} -P 20 curl -s -X POST "$HOST/api/v1/jobs" \
 -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
 -d '{"image_id":"'"$IMG"'","pipeline":["resize_4k","gaussian_blur","sharpen"],"repeat":6}' >/dev/null
echo "Fired 200 jobs concurrently."
