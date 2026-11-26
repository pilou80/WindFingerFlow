#!/bin/bash
# Build and (re)start the service, recording the git sha1 shown in the watermark of every page.
set -e
cd "$(dirname "$0")/.."
sha=$(git rev-parse --short=7 HEAD)
[ -n "$(git status --porcelain)" ] && sha="$sha-dirty"
sudo env GIT_SHA="$sha" docker compose up -d --build
echo "deployed $sha"
