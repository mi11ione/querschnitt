"""Task E: range-fetch the first bytes of the BFH DE vectorizer and list pickle globals WITHOUT unpickling."""
import io, pickletools, sys, os, time, urllib.request, zlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polite
D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data/bfh/raw"
src = "https://huggingface.co/kapllan/omikuji-bonsai-parliament-spacy-de-all_topics-input_long/resolve/main/vectorizer"
assert polite.allowed(src)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None
op = urllib.request.build_opener(NoRedirect)
try:
    op.open(urllib.request.Request(src, headers={"User-Agent": polite.UA}, method="HEAD"))
    loc = src
except urllib.error.HTTPError as e:
    loc = e.headers["Location"]
host = urllib.parse.urlsplit(loc)
print("redirect host", host.netloc, "robots allowed:", polite.allowed(loc))
if not polite.allowed(loc):
    sys.exit("robots disallow cdn")
time.sleep(1.5)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8_000_000
r = urllib.request.urlopen(urllib.request.Request(loc, headers={"User-Agent": polite.UA, "Range": f"bytes=0-{N-1}"}), timeout=120)
b = r.read()
open(f"{D}/vectorizer_de_head.bin", "wb").write(b)
print("got", len(b), "status", r.status, "head", b[:16])
data = b
if b[:2] == b"\x78\x9c" or b[:2] == b"\x78\x01" or b[:2] == b"\x78\xda":
    data = zlib.decompressobj().decompress(b)
    print("zlib-compressed joblib; decompressed head", len(data))
globs, strs = collections.Counter(), []
try:
    for opcode, arg, pos in pickletools.genops(io.BytesIO(data)):
        if opcode.name in ("GLOBAL", "STACK_GLOBAL", "INST"):
            globs[(opcode.name, arg)] += 1
        if opcode.name in ("SHORT_BINUNICODE", "BINUNICODE", "UNICODE") and isinstance(arg, str) and len(strs) < 400:
            strs.append(arg)
except Exception as e:
    print("stopped parsing at", repr(e)[:120])
print("GLOBAL refs:", dict(globs))
print("first strings:", [s for s in strs if len(s) < 60][:250])
