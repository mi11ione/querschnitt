"""Stream OPD's split `docs` export (published downloads at files.openparldata.ch/exports/docs/, no API) and keep, per
document attached to an affair, its metadata and the first 2,000 characters of its extracted text. Nothing else is stored.
Usage: python tools/stream_docs.py <index.json> <out.jsonl.gz>   (resumable per file: <out>.done lists finished files)"""
import gzip, json, os, re, sys, time, urllib.request, zlib

UA = "querschnitt-build/0.1 (Hack Apertus; open-source)"
idx, out = sys.argv[1], sys.argv[2]
files = next(f for f in json.load(open(idx))["files"] if f["entity"] == "docs")["files"]
done_p = out + ".done"
done = set(open(done_p).read().split()) if os.path.exists(done_p) else set()
TAG = re.compile(r"<[^>]+>")


def clean(s):
    return re.sub(r"\s+", " ", TAG.sub(" ", s or "")).strip()


class Lines:
    """Iterate lines of a gzip stream from an HTTP response without saving the file."""
    def __init__(self, r):
        self.r, self.d, self.buf = r, zlib.decompressobj(16 + zlib.MAX_WBITS), b""

    def __iter__(self):
        while True:
            chunk = self.r.read(1 << 20)
            if not chunk:
                break
            self.buf += self.d.decompress(chunk)
            *lines, self.buf = self.buf.split(b"\n")
            yield from lines
        self.buf += self.d.flush()
        if self.buf.strip():
            yield self.buf


for f in sorted(files, key=lambda g: g["size"]):
    if f["filename"] in done:
        continue
    t0, n, kept = time.time(), 0, []
    req = urllib.request.Request(f["url"], headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=900) as r:
        for line in Lines(r):
            if not line.strip():
                continue
            d = json.loads(line); n += 1
            if not d.get("affair_id") or not d.get("text"):
                continue
            t = clean(d["text"])
            if len(t) <= 200:
                continue
            kept.append(dict(id=d["id"], a=d["affair_id"], b=d["body_key"], name=d.get("name"), cat=d.get("category_harmonized"),
                             cat_raw=d.get("category_de") or d.get("category_fr") or d.get("category_it"), lang=d.get("language"),
                             date=(d.get("date") or "")[:10], url=d.get("url"), url_oparl=d.get("url_oparl"), n=len(t), head=t[:2000]))
    with gzip.open(out, "at") as o:
        for k in kept:
            o.write(json.dumps(k, ensure_ascii=False) + "\n")
    with open(done_p, "a") as o:
        o.write(f["filename"] + "\n")
    print(f["filename"], n, len(kept), round(time.time() - t0, 1), flush=True)
    time.sleep(1.5)
print("DONE", flush=True)
