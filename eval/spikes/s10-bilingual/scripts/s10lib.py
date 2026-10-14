"""S10 shared code. APS scheme, de/fr templates and affair_block are imported unchanged from S1 s1lib (with a stub `gw`
module so the shared gateway is never loaded, and s1lib's observe-only urlopen patch undone). l1_prompt / to_probs are
verbatim copies of S6 s6lib (S5 Q1 variant (c): each chapter followed by its APS subtopic names; DE subtopic names are
the only ones on disk, so the FR prompt also lists them in German, exactly as in S6). Model calls only via ideation2 pai.chat
with the payload S6 sent through gw.chat (model -8b, max_tokens 1, temperature 0, user + assistant prefill,
continue_final_message, add_generation_prompt False, logprobs, top_logprobs 20). No system messages."""
import sys, os, types, math, json, threading, urllib.request
_orig = urllib.request.urlopen
sys.modules.setdefault('gw', types.ModuleType('gw'))
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s1-runtime')
import s1lib  # noqa: E402
urllib.request.urlopen = _orig
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
import pai  # noqa: E402

S10 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(S10, 'raw')
MODEL = 'swiss-ai/apertus-v1.5-8b'
BUILD = 'vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840'
TAG_PREFIX = 'bern2-s10-'
CAP = 1.00
SUBS = s1lib.SUBS
CODES = s1lib.CODES
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']
code = lambda ci: '0' if ci == 24 else APS_CODES[ci]
_lock = threading.Lock()


def log(path, row):
    with _lock:
        with open(path, 'a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')


def affair(s, lang):
    return dict(title=s[f'title_{lang}'], title_long=s[f'title_long_{lang}'], lang=lang)


def block(a):
    return s1lib.affair_block(a, a['lang'])


def l1_prompt(a, perm):   # verbatim S6 s6lib.l1_prompt
    lang = a['lang']; t = s1lib.T[lang]; names = s1lib.CHAPTERS[lang]
    def nm(ci):
        s = names[ci]
        if ci < 24: s += f" ({'; '.join(SUBS[ci])})"
        return s
    themes = "\n".join(f"{s1lib.CODES[i]} = {nm(perm[i])}" for i in range(25))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{block(a)}\n\n{t['fmt_code']}"
    return user, '{"' + t['key'] + '": "'


def to_probs(d, codes, n, perm=None):   # verbatim S6
    pv = [0.0] * n
    for c, l in d.items():
        i = codes.index(c)
        pv[perm[i] if perm else i] = math.exp(l)
    s = sum(pv) or 1.0
    return [v / s for v in pv]


def argsort_desc(p):
    return sorted(range(len(p)), key=lambda i: -p[i])


def spent():
    tot, by = pai._read_ledger()
    return sum(v for k, v in by.items() if k.startswith(TAG_PREFIX))


def m1(user, prefill, tag):
    assert tag.startswith(TAG_PREFIX)
    ch, meta = pai.chat([{"role": "user", "content": user}, {"role": "assistant", "content": prefill}], model=MODEL,
                        max_tokens=1, temperature=0.0, tag=tag, tag_cap_usd=CAP, logprobs=True, top_logprobs=20,
                        continue_final_message=True, add_generation_prompt=False)
    resp = meta.get('resp') or {}
    rec = dict(tag=tag, served=resp.get('model'), fp=resp.get('system_fingerprint'), pt=meta['prompt_tokens'],
               usd=meta['usd'], cached=meta.get('cached'), http=meta.get('http'))
    if rec['fp'] != BUILD: raise RuntimeError(f"BUILD CHANGED: {rec['fp']}")
    if rec['served'] != MODEL: raise RuntimeError(f"MODEL MISMATCH: {rec['served']}")
    return pai.read_codes(ch, CODES), rec
