"""Downloads for the nightly job: OPD's published export files only (https://files.openparldata.ch/exports/), never the
API. Every URL is checked against the host's robots.txt with RFC 9309 semantics (longest match wins, allow wins a tie,
`*` and `$` patterns, groups for one agent merged), ported from gegenprobe's robots9309.py. Fail closed: robots.txt
unreachable, 401/403 or 5xx → nothing is fetched; 404/410 → allowed (RFC 9309 §2.3.1.3)."""
from __future__ import annotations

import functools
import gzip
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from typing import Iterator

UA = "querschnitt/0.6 (Hack Apertus; open-source; nightly export delta)"
EXPORTS = "https://files.openparldata.ch/exports/"
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


class Refused(RuntimeError):
    pass


# ---------------------------------------------------------------- RFC 9309
def product_token(ua: str) -> str:
    m = re.match(r"\s*([A-Za-z_-]+)", ua or "")
    return m.group(1).lower() if m else ""


def normalize(s: str) -> str:
    def esc(m):
        ch = chr(int(m.group(1), 16))
        return ch if ch in _UNRESERVED else "%" + m.group(1).upper()
    s = re.sub(r"%([0-9A-Fa-f]{2})", esc, s)
    return "".join(c if 33 <= ord(c) < 127 else "".join(f"%{b:02X}" for b in c.encode()) for c in s)


def parse(text: str, ua: str = UA) -> list[tuple[bool, str]]:
    token = product_token(ua)
    groups, agents, rules, last_agent = [], [], [], False
    for raw in text.lstrip("﻿").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if not last_agent and (agents or rules):
                groups.append((agents, rules)); agents, rules = [], []
            agents.append("*" if v == "*" else product_token(v)); last_agent = True
        elif k in ("allow", "disallow"):
            last_agent = False
            if agents and v:
                rules.append((k == "allow", normalize(v)))
        elif k != "sitemap":
            last_agent = False
    if agents or rules:
        groups.append((agents, rules))
    mine = [r for a, r in groups if token and token in a]
    return [x for r in mine for x in r] if mine else [x for a, r in groups if "*" in a for x in r]


@functools.lru_cache(maxsize=1024)
def _rx(pattern: str) -> re.Pattern:
    body = pattern[:-1] if pattern.endswith("$") else pattern
    return re.compile(".*".join(re.escape(p) for p in body.split("*")) + (r"\Z" if pattern.endswith("$") else ""), re.S)


def decide(rules: list[tuple[bool, str]], path: str) -> bool:
    path = normalize(path or "/")
    if path == "/robots.txt":
        return True
    best = None
    for allow, pat in rules:
        if pat and _rx(pat).match(path):
            key = (len(pat), allow)
            best = key if best is None or key > best else best
    return True if best is None else best[1]


def url_path(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    return (p.path or "/") + ("?" + p.query if p.query else "")


_ROBOTS: dict[str, list[tuple[bool, str]] | None] = {}


def robots_rules(host_url: str) -> list[tuple[bool, str]] | None:
    """Rules for our agent, or None = fetch refused (fail closed)."""
    p = urllib.parse.urlsplit(host_url)
    base = f"{p.scheme}://{p.netloc}"
    if base in _ROBOTS:
        return _ROBOTS[base]
    rules: list | None
    try:
        req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            rules = parse(r.read(512 * 1024).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        rules = [] if e.code in (404, 410) or (400 <= e.code < 500 and e.code not in (401, 403, 429)) else None
    except Exception:  # noqa: BLE001 — unreachable: refuse
        rules = None
    _ROBOTS[base] = rules
    return rules


def check(url: str):
    if not url.startswith(EXPORTS):
        raise Refused(f"{url}: only published export files under {EXPORTS} are fetched")
    rules = robots_rules(url)
    if rules is None:
        raise Refused(f"{url}: robots.txt unreachable or refusing; nothing fetched (fail closed)")
    if not decide(rules, url_path(url)):
        raise Refused(f"{url}: disallowed by robots.txt (RFC 9309)")


# ---------------------------------------------------------------- fetch
def get_json(url: str) -> dict:
    check(url)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
        return json.loads(r.read())


def download(url: str, dest: Path, pause: float = 1.5) -> int:
    check(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    n = 0
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=900) as r, open(tmp, "wb") as o:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            o.write(b); n += len(b)
    os.replace(tmp, dest)
    time.sleep(pause)
    return n


def stream_ndjson(url: str) -> Iterator[dict]:
    """Rows of a gzipped NDJSON export, streamed (nothing saved)."""
    check(url)
    d, buf = zlib.decompressobj(16 + zlib.MAX_WBITS), b""
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=900) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            buf += d.decompress(chunk)
            *lines, buf = buf.split(b"\n")
            for line in lines:
                if line.strip():
                    yield json.loads(line)
        buf += d.flush()
        if buf.strip():
            yield json.loads(buf)


def ndjson(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
