# Hosted deployment image: ONE Render service running everything --
# Omnigraph server, console backend, query gateway, and both role-scoped
# MCP servers (HTTP transport) -- behind a Caddy reverse proxy on Render's
# single public $PORT. Simpler than one-Render-service-per-role at the
# cost of being a single point of failure and no independent scaling (see
# PRODUCTION_READINESS.md -- acceptable for a POC demo, not for real prod).
#
# Graph storage is local disk under /data, backed by a Render persistent
# disk mounted there (see render.yaml) -- Render's free tier has no
# persistent disk, which is why this needs a small paid plan.

# ---- Stage 1: build the Rust engine from source (Linux target) ---------
FROM rust:1-bookworm AS rust-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    protobuf-compiler \
    git \
    && rm -rf /var/lib/apt/lists/*

# Same upstream engine the local dev setup builds from (README.md) --
# cloned fresh here rather than vendored into this repo.
RUN git clone --depth 1 https://github.com/ModernRelay/omnigraph.git /omnigraph

WORKDIR /omnigraph
RUN cargo build --release --locked -p omnigraph-cli -p omnigraph-server

# ---- Stage 2: runtime -----------------------------------------------------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    debian-keyring \
    debian-archive-keyring \
    apt-transport-https \
    gnupg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
       -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
    && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
       -o /etc/apt/sources.list.d/caddy-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends caddy \
    && rm -rf /var/lib/apt/lists/*

COPY --from=rust-builder /omnigraph/target/release/omnigraph /usr/local/bin/omnigraph
COPY --from=rust-builder /omnigraph/target/release/omnigraph-server /usr/local/bin/omnigraph-server

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir \
    -r pipeline/requirements.txt \
    -r console/backend/requirements.txt \
    -r mcp-server/requirements.txt \
    -r agents/requirements.txt

RUN chmod +x /app/deploy/start.sh

# Only Caddy's port is externally reachable -- everything else (omnigraph-
# server, gateway, backend, both MCP servers) binds to 127.0.0.1 only and
# is reached through Caddy's path-based routing (deploy/Caddyfile).
EXPOSE 10000

CMD ["/app/deploy/start.sh"]
