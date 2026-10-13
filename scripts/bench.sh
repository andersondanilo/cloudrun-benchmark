#!/usr/bin/env bash
# Run setup.py first to populate Redis.
# Usage: NODE_URL=... RUST_URL=... [THREADS=4 CONNECTIONS=20 DURATION=30s] ./bench.sh
# Defaults target the docker-compose stack. Needs: wrk, curl.
set -euo pipefail

[ -f /etc/benchmark.env ] && . /etc/benchmark.env

NODE_URL="${NODE_URL:-http://localhost:3000}"
RUST_URL="${RUST_URL:-http://localhost:3001}"
THREADS="${THREADS:-2}"
CONNECTIONS="${CONNECTIONS:-20}"
DURATION="${DURATION:-30s}"

run() {
  local name="$1" url="${2%/}"
  echo "=== $name ($url) ==="
  echo "payload bytes: $(curl -fsS "$url/data" | wc -c)  (run setup.py first if this fails)"
  echo "-- warmup"; wrk -t"$THREADS" -c"$CONNECTIONS" -d5s "$url/data" >/dev/null
  echo "-- measure"; wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency "$url/data"
  echo
}

run "node-fastify" "$NODE_URL"
run "rust-poem" "$RUST_URL"
