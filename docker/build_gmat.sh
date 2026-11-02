#!/bin/sh
# Builds orbitbench-gmat:0.1 from the gmat-mcp checkout, at the pinned commit (committed files only).
# Needs the gmat-worker image: docker build -t gmat-worker -f docker/worker/Dockerfile . (in gmat-mcp).
set -e
GMAT_MCP="${GMAT_MCP_PATH:-../GMAT-MCP}"
COMMIT="${GMAT_MCP_COMMIT:-d161333}"
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$HERE/app" && mkdir -p "$HERE/app"
git -C "$GMAT_MCP" archive "$COMMIT" server.py gmat_session.py core tools | tar -x -C "$HERE/app"
docker build -f "$HERE/gmat.Dockerfile" -t orbitbench-gmat:0.1 "$HERE"
