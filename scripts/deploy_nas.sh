#!/usr/bin/env bash
# Deploy Gazeta to the NAS without rsync (UGOS lacks rsync). Tars the repo,
# pipes it over SSH, unpacks on the NAS, then builds + starts the container.
#
#   ./scripts/deploy_nas.sh
#
# Override host/user/path via env vars if needed.
set -euo pipefail

NAS_USER="${NAS_USER:-guztaluz}"
NAS_HOST="${NAS_HOST:-192.168.0.19}"
NAS_PATH="${NAS_PATH:-/home/guztaluz/gazeta}"

echo "Deploying to ${NAS_USER}@${NAS_HOST}:${NAS_PATH}"

# Build a tar of the project (include gitignored .env + secrets, exclude cruft)
# and stream it straight into a remote 'tar x'. One SSH session, one password.
ssh "${NAS_USER}@${NAS_HOST}" "mkdir -p '${NAS_PATH}'"

tar czf - \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='output/*.png' \
  --exclude='output/latest.png' \
  --exclude='tmp' \
  . | ssh "${NAS_USER}@${NAS_HOST}" "tar xzf - -C '${NAS_PATH}'"

# UGOS user isn't in the docker group, so docker needs sudo. Use -t for the
# sudo password prompt. (Run once with: ssh in and `sudo -v` if it complains.)
echo "Building + starting container on the NAS (first build is slow)..."
echo "(you'll be asked for your sudo password on the NAS)"
ssh -t "${NAS_USER}@${NAS_HOST}" "cd '${NAS_PATH}' && sudo docker compose up -d --build"

echo "Done."
echo "Logs:  ssh ${NAS_USER}@${NAS_HOST} 'sudo docker logs -f gazeta'"
echo "Test:  curl -X POST http://${NAS_HOST}:8420/print/summary"
