#!/usr/bin/env python3
"""Store 20 random JSON documents in Redis, from exactly 100 bytes up to exactly 50 KiB.

The documents are saved as benchmark:data:0 .. benchmark:data:19 with sizes growing
geometrically (100 B, ..., 51200 B); the APIs serve a random one per request.

Usage: REDIS_URL=redis://default:<pw>@<host>:6379 ./setup.py
REDIS_URL lookup: environment, then /etc/benchmark-redis.env (root-only, written on the
VM by Pulumi; run with sudo), then the docker-compose redis (localhost:6380). Stdlib only.
"""
import json
import os
import random
import socket
import ssl
import string
import sys
import uuid
from urllib.parse import unquote, urlparse

KEY_PREFIX = "benchmark:data"
COUNT = 20
MIN_SIZE = 100
MAX_SIZE = 50 * 1024  # 51200 bytes


def sizes():
    ratio = (MAX_SIZE / MIN_SIZE) ** (1 / (COUNT - 1))
    out = [round(MIN_SIZE * ratio**i) for i in range(COUNT)]
    out[-1] = MAX_SIZE
    return out


def rand_str(n):
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def item():
    return {
        "id": str(uuid.uuid4()),
        "name": rand_str(16),
        "score": random.random(),
        "active": random.random() > 0.5,
        "tags": [rand_str(8) for _ in range(3)],
    }


def build_payload(size):
    dumps = lambda o: json.dumps(o, separators=(",", ":"))
    total = len(dumps({"items": [], "pad": ""}))
    items = []
    while True:
        it = item()
        cost = len(dumps(it)) + (1 if items else 0)
        if total + cost > size:
            break
        items.append(it)
        total += cost
    out = dumps({"items": items, "pad": rand_str(size - total)})
    assert len(out.encode()) == size, len(out.encode())
    return out.encode()


def command(*args):
    parts = [b"*%d\r\n" % len(args)]
    for a in args:
        a = a if isinstance(a, bytes) else a.encode()
        parts.append(b"$%d\r\n%s\r\n" % (len(a), a))
    return b"".join(parts)


def redis_url():
    if os.environ.get("REDIS_URL"):
        return os.environ["REDIS_URL"]
    try:
        with open("/etc/benchmark-redis.env") as f:
            for line in f:
                if line.startswith("REDIS_URL="):
                    return line.split("=", 1)[1].strip()
    except OSError as e:
        if os.path.exists("/etc/benchmark-redis.env"):
            sys.exit(f"cannot read /etc/benchmark-redis.env ({e.strerror}); run with sudo")
    return "redis://localhost:6380"


def main():
    url = urlparse(redis_url())
    sock = socket.create_connection((url.hostname, url.port or 6379), timeout=10)
    if url.scheme == "rediss":
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=url.hostname)
    f = sock.makefile("rwb", buffering=0)

    def call(*args):
        sock.sendall(command(*args))
        reply = f.readline().strip()
        if reply.startswith(b"-"):
            sys.exit(f"redis error: {reply.decode()}")

    if url.password:
        call("AUTH", unquote(url.username or "default"), unquote(url.password))
    call("DEL", KEY_PREFIX)  # key from the old single-document layout
    for i, size in enumerate(sizes()):
        payload = build_payload(size)
        call("SET", f"{KEY_PREFIX}:{i}", payload)
        print(f"ok: set {KEY_PREFIX}:{i} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
