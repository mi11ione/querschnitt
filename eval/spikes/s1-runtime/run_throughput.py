"""S1 throughput: M1 requests on fresh (never-sent) affairs at concurrency c (worker processes).
Usage: python3 -I run_throughput.py <c> <n> <offset>. Rows -> raw/tp.jsonl"""
import json, os, sys, time
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s1lib import *  # noqa

F = json.load(open(os.path.join(OUT, 'fresh_pool.json')))
RUN = None

def one(i):
    a = F[i]
    u, p = m1_prompt(a, a['lang'])
    try:
        ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": p}], 'bern-s1-tp',
                             max_tokens=1, continue_final_message=True, add_generation_prompt=False, logprobs=True,
                             top_logprobs=20)
        d, raw = code_dist(ch, NCH)
        row = dict(run=RUN, i=i, rec=rec, top=(max(d, key=d.get) if d else None), err=None)
    except Exception as e:
        row = dict(run=RUN, i=i, rec=None, err=repr(e)[:300])
    log(os.path.join(OUT, 'raw', 'tp.jsonl'), row)
    return row

def init(run):
    global RUN; RUN = run

if __name__ == '__main__':
    c, n, off = map(int, sys.argv[1:4]); assert c <= 8
    run = f'c{c}-n{n}-o{off}-{int(time.time())}'
    if spent_s1() > TOTAL_CAP - 0.1: raise SystemExit('cap')
    t0 = time.time()
    with Pool(c, initializer=init, initargs=(run,)) as pool:
        rows = pool.map(one, range(off, off + n), chunksize=1)
    print(run, 'wall', round(time.time() - t0, 1), 'errors', sum(1 for r in rows if r['err']),
          'cached', sum(1 for r in rows if r['rec'] and r['rec']['cached']))
