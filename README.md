# cloudrun-benchmark

Benchmark of two equivalent HTTP APIs on Google Cloud Run (São Paulo, `southamerica-east1`), load-tested with [wrk](https://github.com/wg/wrk) from a VM in the same region.

## Specs

| | node-fastify | rust-poem |
|---|---|---|
| Language / framework | Node.js 22 + Fastify 5 | Rust + Poem 3 (tokio) |
| Redis client | ioredis | redis-rs (`ConnectionManager`) |
| Container | `node:22-alpine` | multi-stage, `distroless/cc` |

**Endpoints (identical in both)**
- `GET /data` returns the JSON stored in Redis under `benchmark:data` as-is (`application/json`), or 404 if the key is not set.

The APIs are read-only. `scripts/setup.py` (stdlib Python, no dependencies) generates a random JSON document of **exactly 100 KiB (102,400 bytes)** and writes it to Redis. It supports `redis://` and `rediss://` URLs (with password).

**Payload:** `{"items":[{id,name,score,active,tags[3]}...],"pad":"<random>"}`. The pad string brings the size to exactly 102,400 bytes (ASCII only).

**Infrastructure (Pulumi, `infra/`)**
- Cloud Run v2, one service per API, `southamerica-east1`, 1 vCPU / 512 MiB, min = max = 1 instance, concurrency 20, public.
- Redis: [Upstash](https://upstash.io) (not provisioned here; supply its `rediss://` URL).
- Load generator: `e2-micro` Debian 12 VM in `southamerica-east1-a` with `wrk` installed, plus `/usr/local/bin/setup.py` and `/usr/local/bin/bench.sh` (pre-configured with both service URLs).

**Load profile (`scripts/bench.sh`, overridable via env):** 5 s warm-up, then `wrk -t2 -c20 -d30s --latency` against `GET /data`, node first, then rust.

## Run locally

Requires Docker, and `wrk` for the benchmark.

```bash
docker compose up -d --build      # redis + node (:3000) + rust (:3001)

./scripts/setup.py                    # writes to localhost:6380 (compose redis)
curl -s localhost:3000/data | wc -c   # 102400

./scripts/bench.sh                # benchmarks both
THREADS=4 CONNECTIONS=40 DURATION=60s ./scripts/bench.sh

docker compose down
```

Locally, compose runs a plain Redis container. Results are only indicative, since APIs and wrk share one machine.

## Deploy

Releases use [release-please](https://github.com/googleapis/release-please) with [Conventional Commits](https://www.conventionalcommits.org/): merging the release PR on `main` triggers `deploy.yml`, which builds the images, pushes them to Artifact Registry and runs `pulumi up` (stack `prod`).

GitHub configuration:
- Variables: `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_SERVICE_ACCOUNT` (Workload Identity Federation)
- Secrets: `PULUMI_ACCESS_TOKEN`, `REDIS_URL` (Upstash `rediss://default:<password>@<host>:6379`)

After deploy, run the benchmark from the VM (the `vmSsh` stack output has the command):

```bash
gcloud compute ssh benchmark-wrk --zone southamerica-east1-a
REDIS_URL='rediss://default:<password>@<host>:6379' setup.py   # once, populates Upstash
bench.sh
```
