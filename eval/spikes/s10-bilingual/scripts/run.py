"""S10 model run: per affair, L1 variant (c), identity order, DE prompt on the German title (+ long title) and FR prompt on
the French title (+ long title). Full 25-code distributions stored; pooled = arithmetic mean of the two probability vectors.
Usage: python3 -I run.py [workers<=3] [limit]  -> ../raw/l1.jsonl (resume-safe), errors -> ../raw/errors.jsonl"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s10lib import *  # noqa

SAMPLE = {s['sid']: s for s in json.load(open(f'{S10}/sample.json'))}
OUTF = f'{RAW}/l1.jsonl'
STOP = []


def run(sid):
    if STOP: return sid, 'stopped'
    s = SAMPLE[sid]
    try:
        if spent() > CAP - 0.05: raise RuntimeError('S10 cap')
        row = dict(sid=sid, id=s['id'], body=s['body'])
        recs = []
        for lang in ('de', 'fr'):
            a = affair(s, lang); u, pf = l1_prompt(a, list(range(25)))
            d, rec = m1(u, pf, f'bern2-s10-l1{lang}'); recs.append(rec)
            p = to_probs(d, CODES, 25)
            row.update({f'input_{lang}': block(a), f'codes_{lang}': d, f'p_{lang}': p,
                        f'top1_{lang}': argsort_desc(p)[0], f'mass_{lang}': round(sum(math.exp(v) for v in d.values()), 5)})
        pooled = [(x + y) / 2 for x, y in zip(row['p_de'], row['p_fr'])]
        row.update(p_pooled=pooled, top1_pooled=argsort_desc(pooled)[0], agree=row['top1_de'] == row['top1_fr'], recs=recs)
        log(OUTF, row)
        return sid, 'ok'
    except Exception as e:
        log(f'{RAW}/errors.jsonl', dict(sid=sid, err=repr(e)[:500]))
        if 'BUILD' in repr(e) or 'MODEL' in repr(e) or 'cap' in repr(e) or 'BUDGET' in repr(e): STOP.append(1)
        return sid, repr(e)[:200]


def done():
    return {json.loads(l)['sid'] for l in open(OUTF)} if os.path.exists(OUTF) else set()


if __name__ == '__main__':
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    assert workers <= 3
    ts = [k for k in sorted(SAMPLE) if k not in done()]
    if len(sys.argv) > 2: ts = ts[:int(sys.argv[2])]
    print('todo', len(ts), flush=True)
    with ThreadPoolExecutor(workers) as ex:
        for i, (k, st) in enumerate(ex.map(run, ts)):
            if st != 'ok' or i % 30 == 0: print(i, k, st, flush=True)
    print('spent bern2-s10-*:', round(spent(), 5), flush=True)
