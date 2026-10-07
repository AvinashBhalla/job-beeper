#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y ca-certificates curl git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

cd /opt
if [ ! -d /opt/job-beeper ]; then
  git clone --branch v2-live-radar https://github.com/AvinashBhalla/job-beeper.git
fi
cd /opt/job-beeper
git fetch origin
git reset --hard origin/v2-live-radar

docker compose -f v2/docker-compose.yml up -d --build
