#!/usr/bin/env python3
"""Store a random JSON document of exactly 100 KiB (102400 bytes) in Redis.

Usage: REDIS_URL=rediss://default:<pw>@<host>:6379 ./setup.py
Default REDIS_URL targets the docker-compose redis (localhost:6380). Stdlib only.
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

KEY = "benchmark:data"
SIZE = 100 * 1024


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


def build_payload():
    dumps = lambda o: json.dumps(o, separators=(",", ":"))
    total = len(dumps({"items": [], "pad": ""}))
    items = []
    while True:
        it = item()
        cost = len(dumps(it)) + (1 if items else 0)
        if total + cost > SIZE:
            break
        items.append(it)
        total += cost
    out = dumps({"items": items, "pad": rand_str(SIZE - total)})
    assert len(out.encode()) == SIZE, len(out.encode())
    return out.encode()


def command(*args):
    parts = [b"*%d\r\n" % len(args)]
    for a in args:
        a = a if isinstance(a, bytes) else a.encode()
        parts.append(b"$%d\r\n%s\r\n" % (len(a), a))
    return b"".join(parts)


def main():
    url = urlparse(os.environ.get("REDIS_URL", "redis://localhost:6380"))
    sock = socket.create_connection((url.hostname, url.port or 6379), timeout=10)
    if url.scheme == "rediss":
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=url.hostname)
    f = sock.makefile("rwb", buffering=0)

    def call(*args):
        f.write(command(*args))
        reply = f.readline().strip()
        if reply.startswith(b"-"):
            sys.exit(f"redis error: {reply.decode()}")

    if url.password:
        call("AUTH", unquote(url.username or "default"), unquote(url.password))
    payload = build_payload()
    call("SET", KEY, payload)
    print(f"ok: set {KEY} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
