# CLAUDE.md

Benchmark comparing a Node/Fastify API and a Rust/Poem API on Cloud Run (São Paulo). See README.md for specs.

## Layout
- `node-fastify/` – Fastify 5 + ioredis (`src/index.js`), own Dockerfile
- `rust-poem/` – Poem 3 + redis-rs (`src/main.rs`), own Dockerfile
- `docker-compose.yml` – local stack (redis, node on :3000, rust on :3001)
- `scripts/setup.py` – generates the exactly-102,400-byte random JSON and SETs it in Redis (run on the VM / locally; APIs have no write endpoint)
- `scripts/bench.sh` – wrk runner (assumes setup.py already ran); both scripts are installed on the VM by Pulumi
- `infra/` – Pulumi (Python, `__main__.py`): 2 Cloud Run services + e2-micro wrk VM. Redis is external (Upstash, `redisUrl` secret config)
- `.github/workflows/` – `ci.yml` (commitlint + build), `release.yml` (release-please), `deploy.yml` (images + pulumi up)

## Rules
- Both APIs must stay behaviorally identical: same routes, same Redis key `benchmark:data`. Change one, change the other.
- Config via env only: `PORT` (default 8080), `REDIS_URL`.
- Everything in `southamerica-east1`. Do not add GCP-managed Redis; Redis is Upstash.
- Upstash needs TLS: keep rustls features on the `redis` crate.
- Commits must follow Conventional Commits (`feat:`, `fix:`, `chore:`...); releases are automated by release-please, never bump versions by hand.

## Commands
- Run locally: `docker compose up -d --build`; `./scripts/setup.py` (compose redis is on host :6380), then `curl -s localhost:3000/data | wc -c` (expect 102400), same for :3001.
- Preview infra: `cd infra && python -m venv venv && venv/bin/pip install -r requirements.txt && pulumi preview` (needs GCP creds and stack config).
