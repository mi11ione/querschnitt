"""Polite fetcher: RFC 9309 robots gate (gegenprobe.robots9309), one UA, >=1.2 s per host, backoff, fail closed on 429/5xx."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, "/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/src/gegenprobe")
import robots9309  # noqa: E402

UA = "hackapertus-research/0.1 (+contact via openparldata hackathon)"
MIN_GAP = 1.2
LOG = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data/robots_log.jsonl"

_last: dict[str, float] = {}
_robots: dict[str, tuple[str, list | None]] = {}  # host -> (verdict, rules or None)


class Blocked(Exception):
    pass


def _wait(host: str, gap: float = MIN_GAP) -> None:
    t = _last.get(host)
    if t is not None:
        d = gap - (time.monotonic() - t)
        if d > 0:
            time.sleep(d)
    _last[host] = time.monotonic()


def _raw(url: str, timeout: float = 60) -> tuple[int, bytes, dict]:
    host = urllib.parse.urlsplit(url).netloc
    _wait(host, _gap.get(host, MIN_GAP))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b"", dict(e.headers or {})


_gap: dict[str, float] = {}


def robots(scheme_host: str) -> tuple[str, list | None]:
    """scheme_host like 'https://ws.parlament.ch'. Returns (verdict, rules). rules None = allow-all; 'blocked' = deny-all."""
    if scheme_host in _robots:
        return _robots[scheme_host]
    url = scheme_host + "/robots.txt"
    try:
        st, body, hdr = _raw(url, timeout=30)
    except Exception as e:  # unreachable -> fail closed
        st, body = -1, str(e).encode()
    if st == 200:
        text = body.decode("utf-8", "replace")
        rules = robots9309.parse(text, UA)
        verdict = "200"
        # crawl-delay (not in RFC 9309, honour anyway)
        for line in text.splitlines():
            if line.lower().startswith("crawl-delay"):
                try:
                    _gap[urllib.parse.urlsplit(scheme_host).netloc] = max(MIN_GAP, float(line.split(":", 1)[1]))
                except ValueError:
                    pass
        res = (verdict, rules)
        raw_text = text
    elif 400 <= st < 500 and st != 429:
        res = (f"{st} (allow all)", None)
        raw_text = ""
    else:
        res = (f"{st} (fail closed: disallow all)", [(False, "/")])
        raw_text = ""
    _robots[scheme_host] = res
    with open(LOG, "a") as f:
        f.write(json.dumps({"host": scheme_host, "status": st, "verdict": res[0], "robots": raw_text[:20000],
                            "crawl_delay_used": _gap.get(urllib.parse.urlsplit(scheme_host).netloc),
                            "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    return res


def allowed(url: str) -> bool:
    p = urllib.parse.urlsplit(url)
    verdict, rules = robots(f"{p.scheme}://{p.netloc}")
    if rules is None:
        return True
    return robots9309.decide(rules, robots9309.url_path(url))


def get(url: str, timeout: float = 90, retries: int = 3) -> tuple[int, bytes]:
    if not allowed(url):
        raise Blocked(f"robots disallows {url}")
    delay = 5.0
    for attempt in range(retries + 1):
        try:
            st, body, hdr = _raw(url, timeout)
        except Exception as e:  # timeout / connection
            if attempt == retries:
                raise
            time.sleep(delay)
            delay *= 2
            continue
        if st == 429 or st >= 500:
            if st == 429:
                raise Blocked(f"429 on {url}: fail closed")
            if attempt == retries:
                raise Blocked(f"{st} on {url} after retries: fail closed")
            time.sleep(delay)
            delay *= 2
            continue
        return st, body
    raise RuntimeError("unreachable")


def get_json(url: str, **kw):
    st, body = get(url, **kw)
    if st != 200:
        raise RuntimeError(f"{st} {url}: {body[:300]!r}")
    return json.loads(body)
