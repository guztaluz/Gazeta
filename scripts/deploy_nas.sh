#!/usr/bin/env bash
# Deploy Gazeta to the NAS: sync the repo (incl. .env + secrets, which are
# gitignored) and rebuild the Docker container over SSH.
#
#   ./scripts/deploy_nas.sh
#
# Override host/user/path via env vars if needed.
set -euo pipefail

NAS_USER="${NAS_USER:-guztaluz}"
NAS_HOST="${NAS_HOST:-192.168.0.19}"
NAS_PATH="${NAS_PATH:-/volume1/docker/gazeta}"

echo "Deploying to ${NAS_USER}@${NAS_HOST}:${NAS_PATH}"

# rsync the project. --delete keeps the remote clean. We DO include .env and
# secrets/ (needed at runtime, gitignored) but exclude venv/build cruft.
rsync -az --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.git/' \
  --exclude 'output/*.png' \
  --exclude 'output/latest.png' \
  --exclude '/tmp/' \
  ./ "${NAS_USER}@${NAS_HOST}:${NAS_PATH}/"

echo "Building + starting container on the NAS..."
ssh "${NAS_USER}@${NAS_HOST}" "cd ${NAS_PATH} && docker compose up -d --build"

echo "Done. Check: ssh ${NAS_USER}@${NAS_HOST} 'docker logs -f gazeta'"
echo "Test:  curl -X POST http://${NAS_HOST}:8080/print/summary"
