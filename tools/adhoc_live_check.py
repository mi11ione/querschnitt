"""Neues Thema end to end against a running API (real endpoint): POST /adhoc, read the SSE stream to the end, record the
timeline (first decision, first 10, all), flags and calls. Usage:
    python tools/adhoc_live_check.py http://127.0.0.1:8792 out.json '{"sentence": "...", "lang": "de", "limit": 40}' ...
Each JSON argument is one topic, run one after another."""
import json
import sys
import time
import urllib.request


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def stream(url):
    with urllib.request.urlopen(url, timeout=1800) as r:
        ev = {}
        for raw in r:
            line = raw.decode().rstrip("\n")
            if not line:
                if "data" in ev:
                    yield ev.get("event"), json.loads(ev["data"])
                ev = {}
            elif not line.startswith(":") and ": " in line:
                k, v = line.split(": ", 1)
                ev[k] = v


def main():
    base, out = sys.argv[1], sys.argv[2]
    results = []
    for spec in sys.argv[3:]:
        body = json.loads(spec)
        t0 = time.time()
        r = post(base + "/adhoc", body)
        t_topic = time.time() - t0
        print(f"\n{body['sentence']!r} -> {r['slug']} ({t_topic:.1f} s)\n  de: {r['topic']['question']['de']}\n  fr: {r['topic']['question']['fr']}"
              f"\n  it: {r['topic']['question']['it']}\n  terms: { {l: [x['term'] for x in v] for l, v in r['terms'].items()} }", flush=True)
        dec, prog, done = [], None, None
        for kind, d in stream(base + r["stream"]):
            if kind == "decision":
                dec.append(dict(d, wall=round(time.time() - t0, 2)))
                if len(dec) in (1, 10) or len(dec) % 20 == 0:
                    print(f"  {prog['line'] if prog else ''} · decision {len(dec)} at {dec[-1]['wall']} s", flush=True)
            elif kind == "progress":
                prog = d
            elif kind in ("done", "error"):
                done = d
        flagged = [d for d in dec if d["flag"]]
        res = dict(request=body, slug=r["slug"], topic=r["topic"], terms=r["terms"], period=r["period"], topic_s=round(t_topic, 2),
                   n=len(dec), flagged=len(flagged), first_s=dec[0]["wall"] if dec else None,
                   first10_s=dec[9]["wall"] if len(dec) >= 10 else None, all_s=dec[-1]["wall"] if dec else None,
                   newest_first=[d["date"] for d in dec[:5]], summary=done,
                   flagged_titles=[(d["p"], d["body"], d["lang"], d["title"][:120]) for d in sorted(flagged, key=lambda d: -d["p"])],
                   decisions=dec)
        print(f"  done: {len(dec)} read, {len(flagged)} flagged, first at {res['first_s']} s, all at {res['all_s']} s; summary {json.dumps({k: v for k, v in (done or {}).items() if k != 'generation'}, ensure_ascii=False)[:400]}")
        for p, b, l, t in res["flagged_titles"][:12]:
            print(f"    {p:.3f} {b:5} {l} {t}")
        results.append(res)
        with open(out, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
