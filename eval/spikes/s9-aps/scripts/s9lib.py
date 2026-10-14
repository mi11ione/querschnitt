"""S9 shared code. Reuses ideation-1 S1 (APS scheme, prompt builders: s1lib) and S5 (L1 variant (c), joint L2 prompt, S1
permutation: s5lib) verbatim. s1lib is loaded with a stub `gw` module (no gateway import) and its urlopen observer is undone;
every model call goes through ideation2 lib/pai.py (pai.chat) with S5's exact payload (model, messages, max_tokens=1,
temperature=0.0, continue_final_message, add_generation_prompt=False, logprobs, top_logprobs=20)."""
import json, math, os, random, re, sys, types, urllib.request, collections, html as _html
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, RAW = f"{HERE}/data", f"{HERE}/raw"
IDE = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes"
S2D, S3, S5 = f"{IDE}/s2-oracles/data", f"{IDE}/s3-accuracy", f"{IDE}/s5-aps"
sys.path.insert(0, "/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib")
import pai  # noqa: E402

_orig = urllib.request.urlopen
sys.modules.setdefault("gw", types.ModuleType("gw"))      # s1lib does `import gw`; never used here
sys.path.insert(0, f"{IDE}/s1-runtime")
import s1lib  # noqa: E402
urllib.request.urlopen = _orig                              # undo s1lib's observer
MODEL = "swiss-ai/apertus-v1.5-8b"
BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
TAG_CAP = 5.00
CODES = s1lib.CODES; SUBS = s1lib.SUBS; CH_DE = s1lib.CH_DE; CH_FR = s1lib.CH_FR
# ---- copied verbatim from s5lib (cannot import s5lib: it pulls s3lib -> gateway)
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']
S1PERM = list(range(25)); random.Random(7).shuffle(S1PERM)
CODES_EXT = [chr(ord('A') + i) for i in range(26)] + ['a', 'b', 'c', 'd', 'e']


def q1_prompt(a, perm, desc=True):
    """s5lib.q1_prompt verbatim (DE)."""
    t = s1lib.T['de']; names = s1lib.CHAPTERS['de']
    def nm(ci):
        s = names[ci]
        if desc and ci < 24: s += f" ({'; '.join(SUBS[ci])})"
        return s
    themes = "\n".join(f"{s1lib.CODES[i]} = {nm(perm[i])}" for i in range(25))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{s1lib.affair_block(a, 'de')}\n\n{t['fmt_code']}"
    return user, '{"' + t['key'] + '": "'


Q2_NONE = "Keines dieser Unterthemen passt"
def q2_options(chs):
    return [(c, s) for c in chs for s in SUBS[c]]

def q2_prompt(a, chs):
    """s5lib.q2_prompt verbatim."""
    opts = q2_options(chs); codes = CODES_EXT[:len(opts) + 1]
    names = s1lib.CHAPTERS['de']
    lines, k = [], 0
    for c in chs:
        lines.append(f"Thema «{names[c]}»:")
        for s in SUBS[c]:
            lines.append(f"{codes[k]} = {s}"); k += 1
    lines.append(f"{codes[k]} = {Q2_NONE}")
    ths = ", ".join(f"«{names[c]}»" for c in chs)
    user = (f"Das folgende parlamentarische Geschäft gehört zu einem der Themen {ths} der Année Politique Suisse. "
            f"Ordne es genau einem Unterthema zu.\n\nUnterthemen:\n" + "\n".join(lines) +
            f"\n\nGeschäft:\n{s1lib.affair_block(a, 'de')}\n\n"
            "Antworte nur mit dem Buchstaben des Unterthemas als JSON: {\"unterthema\": \"<Buchstabe>\"}")
    return user, '{"unterthema": "', opts, codes


def q2_chapters(p):
    """run.py q2_chapters verbatim: top-3 (excl. none) if their subtopics total <= 26, else top-2."""
    order = [i for i in sorted(range(25), key=lambda i: -p[i]) if i < 24]
    top3 = order[:3]
    return top3 if sum(len(SUBS[c]) for c in top3) <= 26 else order[:2]


# ---- D2: FR prompt = S1 FR template + FR chapter names + DE subtopic names (pre-registered: FR prompt, FR chapter names)
def q1_prompt_fr(a, perm):
    t = s1lib.T['fr']; names = s1lib.CHAPTERS['fr']
    def nm(ci):
        s = names[ci]
        if ci < 24: s += f" ({'; '.join(SUBS[ci])})"
        return s
    themes = "\n".join(f"{s1lib.CODES[i]} = {nm(perm[i])}" for i in range(25))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{s1lib.affair_block(a, 'fr')}\n\n{t['fmt_code']}"
    return user, '{"' + t['key'] + '": "'


# ---- D3: label memory in the S3 E3 shape (examples block between themes and item; example label = code + chapter name)
EX_HEAD = "Frühere Geschäfte mit ihren Themen (zur Orientierung):"
EX_LAB = "Thema"
def q1_prompt_mem(a, perm, examples):
    """examples: list of (title, chapter index)."""
    t = s1lib.T['de']; names = s1lib.CHAPTERS['de']; inv = {perm[i]: i for i in range(25)}
    def nm(ci):
        s = names[ci]
        if ci < 24: s += f" ({'; '.join(SUBS[ci])})"
        return s
    themes = "\n".join(f"{s1lib.CODES[i]} = {nm(perm[i])}" for i in range(25))
    ex = "\n".join(f"- {ti}\n  → {EX_LAB}: {s1lib.CODES[inv[c]]} ({names[c]})" for ti, c in examples)
    user = (f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{EX_HEAD}\n{ex}\n\n{t['item']}:\n{s1lib.affair_block(a, 'de')}"
            f"\n\n{t['fmt_code']}")
    return user, '{"' + t['key'] + '": "'


def payload_messages(user, prefill):
    return [{"role": "user", "content": user}, {"role": "assistant", "content": prefill}]

CALL_KW = dict(max_tokens=1, temperature=0.0, continue_final_message=True, add_generation_prompt=False, logprobs=True,
               top_logprobs=20)

def m1(user, prefill, tag, codes):
    ch, meta = pai.chat(payload_messages(user, prefill), model=MODEL, tag=tag, tag_cap_usd=TAG_CAP, **CALL_KW)
    d = pai.read_codes(ch, codes)
    resp = meta.get("resp") or {}
    rec = dict(tag=tag, cached=meta.get("cached"), model=resp.get("model"), fp=resp.get("system_fingerprint"),
               pt=meta["prompt_tokens"], ct=meta["completion_tokens"], usd=meta["usd"], secs=meta.get("secs"),
               http=meta.get("http"))
    return d, rec


def probs_from_codes(d, perm, codes=CODES):
    pv = [0.0] * len(perm)
    for c, l in d.items(): pv[perm[codes.index(c)]] = math.exp(l)
    s = sum(pv) or 1
    return [v / s for v in pv]


def geo2(pa, pb):
    g = [math.exp((math.log(max(x, 1e-12)) + math.log(max(y, 1e-12))) / 2) for x, y in zip(pa, pb)]
    s = sum(g); return [v / s for v in g]


# ---- text handling (s3lib.clean verbatim)
def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return " ".join(_html.unescape(s).split())


TOK = re.compile(r"\w+")
STOP = set("der die das und oder für von mit des den dem ein eine einer eines zur zum auf aus bei nach über unter vom "
           "les des une pour par sur aux dans avec est que qui son ses leur "
           "della delle degli dei per con nel nella sul sulla che una gli alla allo".split())
def toks(s):
    return [w for w in TOK.findall((s or '').lower()) if len(w) >= 3 and w not in STOP and not w.isdigit()]


class BM25:  # s3-accuracy/build_data.py verbatim
    def __init__(self, docs, k1=1.2, b=0.75):
        self.docs = docs; self.N = len(docs); self.k1, self.b = k1, b
        self.len = [len(d) for d in docs]; self.avg = sum(self.len) / self.N
        self.inv = collections.defaultdict(list)
        for j, d in enumerate(docs):
            for w, c in collections.Counter(d).items(): self.inv[w].append((j, c))
        self.idf = {w: math.log(1 + (self.N - len(p) + 0.5) / (len(p) + 0.5)) for w, p in self.inv.items()}
    def top(self, q, k):
        sc = collections.defaultdict(float)
        for w in set(q):
            if w not in self.inv: continue
            idf = self.idf[w]
            for j, c in self.inv[w]:
                sc[j] += idf * c * (self.k1 + 1) / (c + self.k1 * (1 - self.b + self.b * self.len[j] / self.avg))
        return sorted(sc.items(), key=lambda x: -x[1])[:k]


def log(path, row, _lock=__import__("threading").Lock()):
    with _lock:
        with open(path, "a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load(path, key="oid"):
    out = {}
    if os.path.exists(path):
        for l in open(path):
            r = json.loads(l); out[r[key]] = r
    return out
