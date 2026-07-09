#!/bin/bash
# Starts every backend process, then fronts them all with Caddy on
# Render's single public $PORT (see deploy/Caddyfile for the routing).
# No real process supervision (if a background process dies, this script
# doesn't restart it) -- acceptable for a POC demo, documented as a real
# gap in PRODUCTION_READINESS.md.
set -euo pipefail

export OMNIGRAPH_SERVER_BEARER_TOKENS_FILE=/app/cluster/tokens.dev.json
mkdir -p /data

cd /app/cluster
# cluster.yaml (the repo's own copy, used for local dev too) leaves
# `storage:` unset so local setup keeps defaulting to the config
# directory itself, per README.md. This container's copy is disposable
# (baked into the image, never affects the git repo or local dev), so
# patch in this path here, once, idempotently.
#
# On Render's free plan (no persistent disk -- see render.yaml), /data is
# just a directory on the container's own ephemeral filesystem: it
# survives while the service stays up, but a free-tier restart (spin-down
# from inactivity, or a redeploy) wipes it, same as anything else in the
# container. Re-run ingestion + approval to repopulate `main` if that
# happens before a demo.
grep -q '^storage:' cluster.yaml || echo 'storage: /data' >> cluster.yaml

# `cluster apply` requires state.json to already exist -- `cluster import`
# bootstraps it on a genuinely fresh /data, and fails harmlessly
# (state_already_exists) on every later boot once it's there, hence `||
# true`. Then apply is itself idempotent on every boot/redeploy.
omnigraph cluster import --config . || true
omnigraph cluster apply --config .

omnigraph-server --cluster . --bind 127.0.0.1:8080 &

echo "waiting for omnigraph-server..."
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8080/healthz > /dev/null 2>&1; then
    echo "omnigraph-server is up"
    break
  fi
  sleep 1
done

cd /app/mcp-server
python -m uvicorn gateway:app --host 127.0.0.1 --port 8090 &

cd /app/console/backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 &

cd /app/mcp-server
python mcp_server.py --role content-agent --transport streamable-http --host 127.0.0.1 --port 9001 &
python mcp_server.py --role gtm-agent      --transport streamable-http --host 127.0.0.1 --port 9002 &

sleep 3

exec caddy run --config /app/deploy/Caddyfile --adapter caddyfile
