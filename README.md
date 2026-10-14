# cloudrun-benchmark

Benchmark of three equivalent HTTP APIs on Google Cloud Run (São Paulo, `southamerica-east1`), load-tested with [wrk](https://github.com/wg/wrk) from a VM in the same region.

## Specs

| | node-fastify | rust-poem | go-fasthttp |
|---|---|---|---|
| Language / framework | Node.js 22 + Fastify 5 | Rust + Poem 3 (tokio) | Go + fasthttp (+ `fasthttp/router`) |
| Redis client | ioredis | redis-rs (`ConnectionManager`) | rueidis (auto-pipelining) |
| Container | `node:22-alpine` | multi-stage, `distroless/cc` | multi-stage, `distroless/static` |

**Endpoints (identical in all three)**
- `GET /data` picks one of 20 stored documents at random (`benchmark:data:0` … `benchmark:data:19`) and returns it as-is (`application/json`), or 404 if the key is not set.

The APIs are read-only. `scripts/setup.py` (stdlib Python, no dependencies) generates **20 random JSON documents** and writes them to Redis. Sizes grow geometrically from **exactly 100 bytes up to exactly 50 KiB (51,200 bytes)**: 100, 139, 193, 268, 372, 516, 717, 996, 1383, 1920, 2666, 3703, 5142, 7140, 9915, 13769, 19120, 26551, 36870, 51200. It supports `redis://` and `rediss://` URLs (with password).

**Payload:** `{"items":[{id,name,score,active,tags[3]}...],"pad":"<random>"}`. The pad string brings each document to its exact size (ASCII only).

**Infrastructure (Pulumi, `infra/`)**
- Cloud Run v2, one service per API (3 total), `southamerica-east1`, 1 vCPU / 512 MiB, min = max = 1 instance, concurrency 20, public.
- Redis: `e2-highcpu-4` Debian 12 VM (`redis-server`, password-protected, `maxmemory 512mb`, no persistence) in the same zone. Reached over its internal IP: the Cloud Run services use Direct VPC egress, and a firewall rule allows tcp/6379 only from the default network's private ranges.
- Load generator: `e2-highcpu-4` Debian 12 VM in `southamerica-east1-a` (separate from the Redis VM) with `wrk` installed, plus `/usr/local/bin/setup.py` and `/usr/local/bin/bench.sh` (pre-configured with the three service URLs).

**Load profile (`scripts/bench.sh`, overridable via env):** 5 s warm-up, then `wrk -t2 -c20 -d30s --latency` against `GET /data`, node first, then rust, then go.

## Run locally

Requires Docker, and `wrk` for the benchmark.

```bash
docker compose up -d --build      # redis + node (:3000) + rust (:3001) + go (:3002)

./scripts/setup.py                    # writes to localhost:6380 (compose redis)
curl -s localhost:3000/data | wc -c   # varies per request, 100 to 51200

./scripts/bench.sh                # benchmarks all three
THREADS=4 CONNECTIONS=40 DURATION=60s ./scripts/bench.sh

docker compose down
```

Locally, compose runs a plain Redis container. Results are only indicative, since APIs and wrk share one machine.

## Results on cloudrun

`wrk -t2 -c20 -d30s --latency` from the benchmark VM, random one of the 20 payloads (100 B to 50 KiB) per request. Both the Redis VM and the load generator are `e2-highcpu-4`.

| | Node.js (Fastify) | Rust (Poem) | Go (fasthttp) |
|---|---|---|---|
| Requests/sec | 505.28 | **544.61** | 531.82 |
| Transfer/sec | 4.50 MB | **4.82 MB** | 4.71 MB |
| Latency (avg) | **216.38 ms** | 231.69 ms | 224.52 ms |
| Latency p50 | 14.97 ms | 12.24 ms | **10.99 ms** |
| Latency p75 | **387.38 ms** | 434.95 ms | 416.80 ms |
| Latency p90 | **782.19 ms** | 799.46 ms | 791.42 ms |
| Latency p99 | 1.02 s | 1.02 s | 1.02 s |
| Latency max | **1.06 s** | 1.04 s | 1.05 s |
| Requests in 30 s | 15,180 | **16,362** | 15,980 |

Rust is ahead on throughput (+8% over Node, +2% over Go), but the differences are small. The latency distribution is bimodal for all three: the median is 11 to 15 ms, but p75 and above is hundreds of milliseconds up to about 1 s.

The same test on `e2-micro` VMs (below) gave nearly the same numbers, so the Redis VM and the load generator were not the limit. The pattern is the same for all three runtimes, so the limit is probably on the Cloud Run side (the 1 vCPU instance, its concurrency or the request path), not the language. This was not investigated, so these numbers say more about the setup than about the languages.

### Previous run (`e2-micro` VMs, same workload)

| | Node.js (Fastify) | Rust (Poem) | Go (fasthttp) |
|---|---|---|---|
| Requests/sec | 490.97 | **558.49** | 558.35 |
| Transfer/sec | 4.39 MB | **5.09 MB** | 4.99 MB |
| Latency (avg) | **210.65 ms** | 230.35 ms | 228.54 ms |
| Latency p50 | 15.16 ms | 11.65 ms | **8.92 ms** |
| Latency p75 | **365.78 ms** | 443.99 ms | 439.01 ms |
| Latency p90 | **774.60 ms** | 802.46 ms | 797.79 ms |
| Latency p99 | 1.02 s | 1.02 s | **1.01 s** |
| Latency max | 1.16 s | **1.05 s** | 1.06 s |
| Requests in 30 s | 14,749 | **16,780** | **16,780** |

### Earlier run (single 100 KiB payload, Node and Rust only, `e2-micro` VMs)

| | Node.js (Fastify) | Rust (Poem) |
|---|---|---|
| Requests/sec | 237.72 | **467.93** |
| Transfer/sec | 23.26 MB | **45.79 MB** |
| Latency (avg) | 83.80 ms | **42.59 ms** |
| Latency p50 | 81.34 ms | **42.16 ms** |
| Latency p90 | 95.26 ms | **48.79 ms** |
| Latency p99 | 112.70 ms | **58.97 ms** |
| Requests in 30 s | 7,139 | **14,051** |

That run used a different workload (one fixed 100 KiB document), so it is not comparable with the table above.

## Deploy

Releases use [release-please](https://github.com/googleapis/release-please) with [Conventional Commits](https://www.conventionalcommits.org/): merging the release PR on `main` only cuts the release and does not deploy. Deploys are manual: Actions → **deploy** → *Run workflow* (or `gh workflow run deploy.yml`). It builds the images, pushes them to Artifact Registry and runs `pulumi up` (stack `prod`).

GitHub configuration:
- Variables: `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_SERVICE_ACCOUNT` (Workload Identity Federation)
- Secrets: `PULUMI_ACCESS_TOKEN`, `RELEASE_PLEASE_TOKEN` (PAT with `contents` + `pull requests` write; needed because Actions is not allowed to create PRs)

After deploy, run the benchmark from the VM (the `vmSsh` stack output has the command):

```bash
gcloud compute ssh benchmark-wrk --zone southamerica-east1-a
sudo setup.py   # once, populates Redis (URL comes from /etc/benchmark-redis.env, root-only)
bench.sh
```
