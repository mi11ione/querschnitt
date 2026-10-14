"""Task E: download the BFH DE omikuji model (trees + vectorizer, ~670 MB) with robots checks on hf and its CDN."""
import os, sys, time, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polite
D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data/bfh/raw/de"
os.makedirs(D + "/omikuji-model", exist_ok=True)
R = "https://huggingface.co/kapllan/omikuji-bonsai-parliament-spacy-de-all_topics-input_long/resolve/main/"
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
op = urllib.request.build_opener(NoRedirect)
for f in ["omikuji-model/settings.json", "omikuji-model/tree0.cbor", "omikuji-model/tree1.cbor", "omikuji-model/tree2.cbor", "vectorizer"]:
    dst = f"{D}/{f}"
    if os.path.exists(dst):
        continue
    url = R + f
    assert polite.allowed(url)
    time.sleep(1.5)
    try:
        op.open(urllib.request.Request(url, headers={"User-Agent": polite.UA}, method="HEAD"))
        loc = url
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") or url
        if loc.startswith("/"):
            loc = "https://huggingface.co" + loc
    if not polite.allowed(loc):
        sys.exit(f"robots disallow {loc}")
    time.sleep(1.5)
    with urllib.request.urlopen(urllib.request.Request(loc, headers={"User-Agent": polite.UA}), timeout=300) as r, open(dst + ".part", "wb") as fo:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            fo.write(c)
    os.rename(dst + ".part", dst)
    print(f, os.path.getsize(dst), flush=True)
print("DONE")
