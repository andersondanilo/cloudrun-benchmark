#!/usr/bin/env bash
# Run setup.py first to populate Redis.
# Usage: NODE_URL=... RUST_URL=... GO_URL=... [THREADS=4 CONNECTIONS=240 DURATION=30s] ./bench.sh
# Defaults target the docker-compose stack. Needs: wrk, curl.
set -euo pipefail

[ -f /etc/benchmark.env ] && . /etc/benchmark.env

NODE_URL="${NODE_URL:-http://localhost:3000}"
RUST_URL="${RUST_URL:-http://localhost:3001}"
GO_URL="${GO_URL:-http://localhost:3002}"
THREADS="${THREADS:-2}"
CONNECTIONS="${CONNECTIONS:-240}"
DURATION="${DURATION:-30s}"

run() {
  local name="$1" url="${2%/}"
  echo "=== $name ($url) ==="
  curl -fsS -o /dev/null -w "check GET /data: HTTP %{http_code}\n" "$url/data" || { echo "run setup.py first"; exit 1; }
  echo "-- warmup"; wrk -t"$THREADS" -c"$CONNECTIONS" -d5s "$url/data" >/dev/null
  echo "-- measure"; wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency "$url/data"
  echo
}

run "node-fastify" "$NODE_URL"
run "rust-poem" "$RUST_URL"
run "go-fasthttp" "$GO_URL"
