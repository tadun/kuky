#!/usr/bin/env bash
# setup_ssh.sh — generates an SSH key and copies it to your BrickPi robot
#
# Run this ONCE on your Mac before using deploy.sh or VS Code Remote-SSH.
# Usage: ./setup_ssh.sh <user@host>  e.g.  ./setup_ssh.sh pi@brickpi.local

set -euo pipefail

ROBOT="${1:?Usage: $0 <user@host>}"
KEY="$HOME/.ssh/id_ed25519_kuky"

echo "==> Generating SSH key at ${KEY}"
ssh-keygen -t ed25519 -C "kuky-brickpi" -f "${KEY}" -N ""

echo "==> Copying public key to robot (you will be prompted for the robot's password)"
ssh-copy-id -i "${KEY}.pub" "${ROBOT}"

echo "==> Adding host alias 'brickpi' to ~/.ssh/config"
cat >> ~/.ssh/config <<EOF

Host brickpi
    HostName ${ROBOT#*@}
    User ${ROBOT%@*}
    IdentityFile ${KEY}
    ServerAliveInterval 30
EOF

echo ""
echo "Done! You can now:"
echo "  ssh brickpi                  # connect in terminal"
echo "  ./deploy.sh brickpi          # deploy project"
echo "  VS Code > Remote-SSH > brickpi  # open remote workspace"
