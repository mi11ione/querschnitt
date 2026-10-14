"""S1 main measurement runs. Usage: python3 -I run_main.py <phase> [workers]
phases: m1, m4p (permuted), prior (content-free, exact per-code), m2 (exact per-label), m3 (batched), l2 (subtopics; needs m1)
Every row is appended to raw/<phase>.jsonl; reruns skip keys already done. Worker processes (not threads) because the
gateway's per-call ledger scan is CPU/GIL-bound (~1 s client overhead per call)."""
import json, os, sys, random, hashlib
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s1lib import *  # noqa

RAW = os.path.join(OUT, 'raw'); os.makedirs(RAW, exist_ok=True)
S = json.load(open(os.path.join(OUT, 'sample.json')))
PERM = list(range(NCH)); random.Random(7).shuffle(PERM)
assert sum(PERM[i] == i for i in range(NCH)) <= 1
H = lambda s: hashlib.sha256(str(s).encode()).hexdigest()
M4_SIDS = sorted((s['sid'] for s in S), key=H)[:60]
M2_SIDS = []
for L in ('de', 'fr', 'it'):
    M2_SIDS += sorted((s['sid'] for s in S if s['lang'] == L), key=lambda x: H(f'm2{x}'))[:5]
NA = dict(title='N/A', title_long='', text='')

def done(phase):
    p = os.path.join(RAW, f'{phase}.jsonl'); ks = set()
    if os.path.exists(p):
        for l in open(p): ks.add(json.loads(l)['key'])
    return ks

def tasks(phase):
    if phase == 'm1': return [dict(key=f"m1-{s['sid']}", sid=s['sid'], perm=None) for s in S]
    if phase == 'm4p': return [dict(key=f"m4p-{sid}", sid=sid, perm=PERM) for sid in M4_SIDS]
    if phase == 'prior':
        return [dict(key=f"prior-{L}-{pn}-{c}", lang=L, pname=pn, code=c) for L in ('de', 'fr', 'it')
                for pn in ('id', 'perm') for c in range(NCH)]
    if phase == 'm2': return [dict(key=f"m2-{sid}-{c}", sid=sid, c=c) for sid in M2_SIDS for c in range(NCH)]
    if phase == 'm3':
        out = []
        for L in ('de', 'fr', 'it'):
            sids = [s['sid'] for s in S if s['lang'] == L]
            nb = max(1, round(len(sids) / 9))
            for b in range(nb):
                out.append(dict(key=f"m3-{L}-{b}", lang=L, sids=sids[b::nb]))
        return out
    if phase == 'l2':
        m1 = {}
        for l in open(os.path.join(RAW, 'm1.jsonl')):
            r = json.loads(l); m1[r['sid']] = r['top']
        return [dict(key=f"l2-{sid}", sid=sid, ch=ch) for sid, ch in m1.items() if ch is not None and ch < 24]
    raise SystemExit(phase)

def run(t):
    phase = t['key'].split('-')[0]
    tag = f'bern-s1-{phase}'
    if spent_s1() > TOTAL_CAP - 0.05: raise RuntimeError('S1 total cap reached')
    try:
        if phase in ('m1', 'm4p'):
            a = S[t['sid']]; perm = t['perm'] or list(range(NCH))
            u, p = m1_prompt(a, a['lang'], perm)
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": p}], tag, max_tokens=1,
                                 continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
            d, raw = code_dist(ch, NCH)
            chap = {perm[CODES.index(c)]: l for c, l in d.items()}       # chapter index -> logprob
            top = max(chap, key=chap.get) if chap else None
            mass = sum(math.exp(l) for l in d.values())
            row = dict(t, rec=rec, codes=d, chap=chap, top=top, code_mass=round(mass, 5), raw=raw,
                       gen=(ch.get('message') or {}).get('content'), lang=a['lang'], level=a['level'],
                       has_text=bool(a['text']))
        elif phase == 'prior':
            perm = PERM if t['pname'] == 'perm' else list(range(NCH))
            u, p = m1_prompt(NA, t['lang'], perm)
            cont = CODES[t['code']]
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": p + cont}], tag,
                                 max_tokens=1, continue_final_message=True, add_generation_prompt=False, prompt_logprobs=1)
            pl = meta['resp'].get('prompt_logprobs') or ch.get('prompt_logprobs')
            lp, toks, straddle = tail_logprob(pl, cont)
            row = dict(t, rec=rec, lp=lp, toks=toks, straddle=straddle, chapter=perm[t['code']])
        elif phase == 'm2':
            a = S[t['sid']]
            u, p = m2_prompt(a, a['lang'])
            cont = CHAPTERS[a['lang']][t['c']] + '"}'
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": p + cont}], tag,
                                 max_tokens=1, continue_final_message=True, add_generation_prompt=False, prompt_logprobs=1)
            pl = meta['resp'].get('prompt_logprobs') or ch.get('prompt_logprobs')
            lp, toks, straddle = tail_logprob(pl, cont)
            row = dict(t, rec=rec, lp=lp, ntok=len(toks), toks=toks, straddle=straddle, lang=a['lang'])
        elif phase == 'm3':
            items = [S[i] for i in t['sids']]
            u, p = m3_prompt(items, t['lang'])
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": p}], tag,
                                 max_tokens=8 * len(items) + 8, continue_final_message=True, add_generation_prompt=False,
                                 logprobs=True, top_logprobs=20)
            content = (ch.get('logprobs') or {}).get('content') or []
            # walk the generated tokens; a code token is one that follows "<k>: " (prefill gives "1: " for k=1)
            text = p; per = {}
            for tok in content:
                import re
                m = re.search(r'(?:^|\n)(\d+):\s*$', text)
                s = tok['token'].strip()
                if m and len(s) == 1 and s in CODES:
                    k = int(m.group(1))
                    if 1 <= k <= len(items) and k not in per:
                        d = {}
                        for tt in tok['top_logprobs']:
                            x = tt['token'].strip()
                            if len(x) == 1 and x in CODES: d[x] = max(d.get(x, -1e9), tt['logprob'])
                        per[k] = dict(sid=items[k - 1]['sid'], codes=d, top=CODES.index(max(d, key=d.get)))
                text += tok['token']
            row = dict(t, rec=rec, gen=(ch.get('message') or {}).get('content'), per=per, n_items=len(items),
                       parsed=len(per))
        elif phase == 'l2':
            a = S[t['sid']]
            u, p, n = l2_prompt(a, a['lang'], t['ch'])
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": p}], tag, max_tokens=1,
                                 continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
            d, raw = code_dist(ch, n)
            row = dict(t, rec=rec, codes=d, top=(CODES.index(max(d, key=d.get)) if d else None), nsub=n,
                       code_mass=round(sum(math.exp(l) for l in d.values()), 5), lang=a['lang'])
        log(os.path.join(RAW, f'{phase}.jsonl'), row)
        return t['key'], 'ok'
    except Exception as e:
        log(os.path.join(RAW, f'errors.jsonl'), dict(t, err=repr(e)[:500]))
        return t['key'], repr(e)[:200]

if __name__ == '__main__':
    phase = sys.argv[1]; workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    assert workers <= 8
    ts = [t for t in tasks(phase) if t['key'] not in done(phase)]
    print(phase, 'todo', len(ts), flush=True)
    with Pool(workers) as pool:
        for i, (k, st) in enumerate(pool.imap_unordered(run, ts)):
            if st != 'ok' or i % 25 == 0: print(i, k, st, flush=True)
    print('spent bern-s1-*:', round(spent_s1(), 4), flush=True)
