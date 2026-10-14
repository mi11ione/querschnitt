"""S6 A1: APS L1 (S5 variant c; second order only if first-order top p < 0.9) + joint L2 on 160 cantonal/communal affairs.
Usage: python3 -I run_a1.py [workers<=8] [limit]   -> ../raw/a1.jsonl (resume-safe), errors -> ../raw/errors.jsonl
Per affair: L1 order a (identity) -> [L1 order b (S1 permutation) if max p_a < 0.9] -> joint L2 over top-3/top-2 chapters
of the L1 arithmetic mean (top chapter first). Top-1 chapter = geometric mean of the orders used (S5 Q1 (c) geo)."""
import json, os, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6lib import *  # noqa

SAMPLE = {s['sid']: s for s in json.load(open(f'{S6}/sample.json'))}
OUTF = f'{RAW6}/a1.jsonl'
_N = 0


def run(sid):
    global _N
    _N += 1
    if _N % 20 == 1 and spent_s6() > S6_CAP - 0.10: raise RuntimeError('S6 cap')
    a = SAMPLE[sid]
    try:
        recs = []
        ua, pfa = l1_prompt(a, list(range(25)))
        da, _, ra = m1_6(ua, pfa, 'bern-s6-a1l1a', s1lib.CODES); recs.append(ra)
        pa = to_probs(da, s1lib.CODES, 25)
        pb, db = None, None
        if max(pa) < TAU:
            ub, pfb = l1_prompt(a, S1PERM)
            db, _, rb = m1_6(ub, pfb, 'bern-s6-a1l1b', s1lib.CODES); recs.append(rb)
            pb = to_probs(db, s1lib.CODES, 25, S1PERM)
            p_top1 = geo(pa, pb); p_short = [(x + y) / 2 for x, y in zip(pa, pb)]
        else:
            p_top1 = p_short = pa
        chs = l2_chapters(p_short)
        u2, pf2, opts, codes2 = l2_prompt(a, chs)
        d2, _, r2 = m1_6(u2, pf2, 'bern-s6-a1l2', codes2); recs.append(r2)
        p2 = to_probs(d2, codes2, len(opts) + 1)
        j = max(range(len(p2)), key=lambda i: p2[i])
        l2_ch = opts[j][0] if j < len(opts) else None
        l1_top1 = argsort_desc(p_top1)[0]
        row = dict(sid=sid, id=a['id'], level=a['level'], lang=a['lang'], body=a['body'], title_only=a['title_only'],
                   input_block=block(a), pa=pa, pb=pb, p_top1=p_top1, p_short=p_short, codes_a=da, codes_b=db,
                   l1_top1=l1_top1, l1_top1_p=p_top1[l1_top1], l1_top3=argsort_desc(p_short)[:3],
                   order_disagree=(None if pb is None else argsort_desc(pa)[0] != argsort_desc(pb)[0]),
                   l2_chs=chs, l2_opts=opts, l2_p=p2, l2_pick=j, l2_pick_p=p2[j],
                   l2_sub=(opts[j][1] if j < len(opts) else None), l2_chapter=l2_ch,
                   # final chapter: L1 'none' stays 'none'; else chapter of the chosen subtopic; L2 'none' -> L1 top-1
                   final=(24 if l1_top1 == 24 else (l2_ch if l2_ch is not None else l1_top1)),
                   recs=recs, mass_a=round(sum(math.exp(v) for v in da.values()), 5))
        s1lib.log(OUTF, row)
        return sid, 'ok'
    except Exception as e:
        s1lib.log(f'{RAW6}/errors.jsonl', dict(phase='a1', sid=sid, err=repr(e)[:500]))
        return sid, repr(e)[:200]


def done():
    return {json.loads(l)['sid'] for l in open(OUTF)} if os.path.exists(OUTF) else set()


if __name__ == '__main__':
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    assert workers <= 8
    ts = [s for s in sorted(SAMPLE) if s not in done()]
    if len(sys.argv) > 2: ts = ts[:int(sys.argv[2])]
    print('a1 todo', len(ts), flush=True)
    with Pool(workers) as pool:
        for i, (k, st) in enumerate(pool.imap_unordered(run, ts)):
            if st != 'ok' or i % 20 == 0: print(i, k, st, flush=True)
            if 'BUILD CHANGED' in st: pool.terminate(); break
    print('spent bern-s6-*:', round(spent_s6(), 4), flush=True)
