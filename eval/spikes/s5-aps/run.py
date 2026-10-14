"""S5 measurement runs. Usage: python3 -I run.py <phase> [workers<=8] [limit]
Rows -> raw/<phase>.jsonl (resume-safe), errors -> raw/errors.jsonl. Worker processes (gw's ledger scan is CPU-bound).
  q1a/q1b  APS 24+none, chapter names + subtopic names, order identity / S1 permutation (297 APS-gold affairs)
  q2a/q2b  joint L2 over the subtopics of the top-3 (or top-2) chapters of the Q1 L1 (S5_L1 env, default q1avg),
           chapter blocks in L1 order / reversed (262 affairs with a main subtopic in the 190)
  q4a/q4b  Curia yes/no verification of the top-6 labels of S3 E3 2-order average, yes=A / yes=B (300 Curia items)"""
import json, os, sys, math
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s5lib import *  # noqa

APS = {a['opd_affair_id']: a for a in json.load(open(f'{S3}/data/aps.json'))}   # 298 rows -> 297 unique (last wins, as S3)
ITEMS = json.load(open(f'{S3}/data/curia300.json')); BYID = {it['curia_id']: it for it in ITEMS}
L2_GOLD = {o: APS_CODES.index(a['chapter_code']) for o, a in APS.items()
           if a['subtopic_name'] in SUBS[APS_CODES.index(a['chapter_code'])]}


def load(path, key):
    return {json.loads(l)[key]: json.loads(l) for l in open(path)} if os.path.exists(path) else {}


def l1_probs(variant):
    """oid -> 25-vector of chapter probabilities. q1a/q1b single orders, q1avg arithmetic mean of both, e5avg = S3 E5 (geo)."""
    if variant in ('q1a', 'q1b'):
        return {o: r['p'] for o, r in load(f'{RAW5}/{variant}.jsonl', 'oid').items()}
    src = ('q1a', 'q1b') if variant.startswith('q1') else None
    if src:
        ra, rb = (load(f'{RAW5}/{s}.jsonl', 'oid') for s in src)
        if variant == 'q1avg':
            return {o: [(x + y) / 2 for x, y in zip(ra[o]['p'], rb[o]['p'])] for o in ra if o in rb}
    ra, rb = load(f'{S3}/raw/e5a.jsonl', 'oid'), load(f'{S3}/raw/e5b.jsonl', 'oid')
    out = {}
    for o in ra:
        la = [math.log(max(x, 1e-12)) for x in ra[o]['p']]; lb = [math.log(max(x, 1e-12)) for x in rb[o]['p']]
        g = [math.exp((x + y) / 2) for x, y in zip(la, lb)]; s = sum(g); out[o] = [v / s for v in g]
    return out


def q2_chapters(p):
    """top-3 chapters (excluding 'none') if their subtopics total <= 26, else top-2."""
    order = [i for i in sorted(range(25), key=lambda i: -p[i]) if i < 24]
    top3 = order[:3]
    return top3 if sum(len(SUBS[c]) for c in top3) <= 26 else order[:2]


def q4_cands(k=6):
    ra, rb = load(f'{S3}/raw/e3a.jsonl', 'cid'), load(f'{S3}/raw/e3b.jsonl', 'cid')
    out = {}
    for c in ra:
        p = [(x + y) / 2 for x, y in zip(ra[c]['p'], rb[c]['p'])]
        out[c] = [LABELS[i] for i in sorted(range(NL - 1), key=lambda i: -p[i])[:k]]   # 28 tags, 'none' excluded
    return out


def tasks(phase):
    if phase in ('q1a', 'q1b'):
        return [dict(key=f"{phase}-{o}", oid=o) for o in APS]
    if phase in ('q2a', 'q2b'):
        P = l1_probs(os.environ.get('S5_L1', 'q1avg'))
        out = []
        for o in L2_GOLD:
            chs = q2_chapters(P[o])
            if phase == 'q2b': chs = list(reversed(chs))
            out.append(dict(key=f"{phase}-{o}", oid=o, chs=chs, l1=os.environ.get('S5_L1', 'q1avg')))
        return out
    if phase in ('q4a', 'q4b'):
        C = q4_cands()
        return [dict(key=f"{phase}-{c}-{t}", cid=c, tag_id=t, rank=r) for c in C for r, t in enumerate(C[c])]
    raise SystemExit(phase)


_N = 0
def run(t):
    phase = t['key'].split('-')[0]; tag = f'bern-s5-{phase}'
    global _N
    _N += 1
    if _N % 40 == 1 and spent_s5() > S5_CAP - 0.10: raise RuntimeError('S5 cap')
    try:
        if phase in ('q1a', 'q1b'):
            a = APS[t['oid']]; perm = list(range(25)) if phase == 'q1a' else S1PERM
            u, p = q1_prompt(a, perm)
            d, raw, rec = m1_5(u, p, tag, s1lib.CODES)
            pv = [0.0] * 25
            for c, l in d.items(): pv[perm[s1lib.CODES.index(c)]] = math.exp(l)
            s = sum(pv) or 1; pv = [v / s for v in pv]
            row = dict(t, rec=rec, codes=d, p=pv, mass=round(sum(math.exp(v) for v in d.values()), 5))
        elif phase in ('q2a', 'q2b'):
            a = APS[t['oid']]
            u, p, opts, codes = q2_prompt(a, t['chs'])
            d, raw, rec = m1_5(u, p, tag, codes)
            pv = [0.0] * (len(opts) + 1)
            for c, l in d.items(): pv[codes.index(c)] = math.exp(l)
            s = sum(pv) or 1; pv = [v / s for v in pv]
            row = dict(t, rec=rec, codes=d, opts=opts, p=pv, mass=round(sum(math.exp(v) for v in d.values()), 5))
        elif phase in ('q4a', 'q4b'):
            x = BYID[t['cid']]['lang']['de']
            u, p = q4_prompt(dict(title=x['title'], text=x['text']), t['tag_id'], yes_first=(phase == 'q4a'))
            d, raw, rec = m1_5(u, p, tag, ["A", "B"])
            pa, pb = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
            row = dict(t, rec=rec, codes=d, p_yes=(pa if phase == 'q4a' else pb) / (pa + pb))
        s1lib.log(f'{RAW5}/{phase}.jsonl', row)
        return t['key'], 'ok'
    except Exception as e:
        s1lib.log(f'{RAW5}/errors.jsonl', dict(t, err=repr(e)[:500]))
        return t['key'], repr(e)[:200]


def done(phase):
    p = f'{RAW5}/{phase}.jsonl'
    return {json.loads(l)['key'] for l in open(p)} if os.path.exists(p) else set()


if __name__ == '__main__':
    phase = sys.argv[1]; workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    assert workers <= 8
    ts = [t for t in tasks(phase) if t['key'] not in done(phase)]
    if len(sys.argv) > 3: ts = ts[:int(sys.argv[3])]
    print(phase, 'todo', len(ts), flush=True)
    with Pool(workers) as pool:
        for i, (k, st) in enumerate(pool.imap_unordered(run, ts)):
            if st != 'ok' or i % 50 == 0: print(i, k, st, flush=True)
    print('spent bern-s5-*:', round(spent_s5(), 4), flush=True)
