#!/usr/bin/env bash
# deploy.sh — syncs the project to the BrickPi robot over SSH
#
# Usage:
#   ./deploy.sh <robot_host>          # e.g. ./deploy.sh pi@brickpi.local
#   ./deploy.sh pi@192.168.1.42
#
# First run: also installs dependencies on the robot.

set -euo pipefail

ROBOT="${1:?Usage: $0 <user@host>}"
REMOTE_DIR="/home/pi/kuky"

echo "==> Syncing to ${ROBOT}:${REMOTE_DIR}"
rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
  --exclude '.git' --exclude '*.egg-info' \
  ./ "${ROBOT}:${REMOTE_DIR}/"

echo "==> Installing dependencies on robot"
ssh "${ROBOT}" "cd ${REMOTE_DIR} && pip3 install -r requirements.txt"

echo "==> Deploy complete. Run with:"
echo "    ssh ${ROBOT} 'cd ${REMOTE_DIR} && python3 -m kuky.scripts.run_robot'"
