"""S8 scoring. python3 -I run.py a|b  [workers=3]. a: yes=A on all items; b: yes=B only where 0.1<p_a<0.9.
Rows -> raw/<order>.jsonl (resume by affair id). Throughput every 500 calls -> raw/throughput.jsonl. Stops on foreign fingerprint."""
import sys, os, json, math, time, threading, statistics
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
from common import *
import pai

order = sys.argv[1]; W = int(sys.argv[2]) if len(sys.argv) > 2 else 3
assert order in ('a', 'b') and W <= 3
TAG = f'bern2-s8-{order}'
OUT = f'{HERE}/raw/{order}.jsonl'; TP = f'{HERE}/raw/throughput.jsonl'
I = [x for x in json.load(open(f'{HERE}/items_cache.json')) if x['title']]
if order == 'b':
    pa = {json.loads(l)['id']: json.loads(l)['p_yes'] for l in open(f'{HERE}/raw/a.jsonl')}
    I = [x for x in I if x['id'] in pa and 0.1 < pa[x['id']] < 0.9]
done = {json.loads(l)['id'] for l in open(OUT)} if os.path.exists(OUT) else set()
todo = [x for x in I if x['id'] not in done]
print(order, 'items', len(I), 'todo', len(todo), flush=True)
lock = threading.Lock(); stop = threading.Event()
win = dict(t0=time.time(), secs=[], n429=0, nerr=0, n=0); total = dict(n=0)

def spent_tags():
    return sum(v for k, v in pai._read_ledger()[1].items() if k.startswith(TAG_PREFIX))

def one(x):
    if stop.is_set(): return
    u, p = build_prompt(x['lang'], x['title'], x['title_long'], order)
    t0 = time.time()
    try:
        ch, meta = pai.chat([{"role": "user", "content": u}, {"role": "assistant", "content": p}], model=MODEL, max_tokens=1,
                            tag=TAG, tag_cap_usd=CAP - 0.40 if order == 'a' else 0.60, logprobs=True, top_logprobs=20,
                            continue_final_message=True, add_generation_prompt=False)
    except Exception as e:
        with lock:
            win['nerr'] += 1
            open(f'{HERE}/raw/errors.jsonl', 'a').write(json.dumps(dict(id=x['id'], order=order, err=repr(e)[:300])) + '\n')
        if 'BUDGET' in str(e): stop.set()
        return
    fp = meta['resp'].get('system_fingerprint'); served = meta['resp'].get('model')
    d = pai.read_codes(ch, ["A", "B"]); pa_, pb_ = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
    py = (pa_ if order == 'a' else pb_) / (pa_ + pb_)
    row = dict(id=x['id'], body=x['body'], lang=x['lang'], p_yes=py, codes=d, fp=fp, served=served, latency=round(time.time() - t0, 3),
               secs=meta.get('secs'), http=meta.get('http'), cached=meta.get('cached'), pt=meta.get('prompt_tokens'), ts=round(t0, 3))
    with lock:
        if fp != FP_EXPECTED:
            open(f'{HERE}/raw/foreign_fp.jsonl', 'a').write(json.dumps(row) + '\n'); stop.set(); return
        open(OUT, 'a').write(json.dumps(row, ensure_ascii=False) + '\n')
        win['n'] += 1; total['n'] += 1
        if not meta.get('cached'):
            win['secs'].append(meta.get('secs') or 0); win['n429'] += sum(1 for s in meta.get('http') or [] if s == 429)
        if win['n'] >= 500:
            dt = time.time() - win['t0']; s = sorted(win['secs']) or [0]
            rec = dict(ts=round(time.time()), order=order, calls=win['n'], wall_s=round(dt, 1), req_per_s=round(win['n'] / dt, 3),
                       http_p50=round(statistics.median(s), 3), http_p95=round(s[int(0.95 * (len(s) - 1))], 3), n429=win['n429'],
                       errors=win['nerr'], done_total=len(done) + total['n'], workers=W)
            open(TP, 'a').write(json.dumps(rec) + '\n'); print(rec, flush=True)
            win.update(t0=time.time(), secs=[], n429=0, nerr=0, n=0)

with ThreadPoolExecutor(W) as ex:
    list(ex.map(one, todo))
print('finished', order, 'new rows', total['n'], 'stop', stop.is_set(), 'spent s8', round(spent_tags(), 4), flush=True)
