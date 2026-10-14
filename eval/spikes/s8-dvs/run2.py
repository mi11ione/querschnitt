"""S8 runner after the 18:23 UTC order change. python3 -I run2.py [workers=3]
One task per affair: order A (yes=A) if missing, then order B (yes=B) if 0.1<p_A<0.9 and B missing. Task list order = order.json.
Rows -> raw/a.jsonl, raw/b.jsonl (resumable). Throughput per 500 calls -> raw/throughput.jsonl. Stops on foreign fingerprint / budget."""
import sys, os, json, math, time, threading, statistics
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
from common import *
import pai
W = int(sys.argv[1]) if len(sys.argv) > 1 else 3; assert W <= 3
IT = {x['id']: x for x in json.load(open(f'{HERE}/items_cache.json'))}
O = json.load(open(f'{HERE}/order.json'))
def rd(p): return {json.loads(l)['id']: json.loads(l) for l in open(p)} if os.path.exists(p) else {}
RA, RB = rd(f'{HERE}/raw/a.jsonl'), rd(f'{HERE}/raw/b.jsonl')
first = sorted(RA, key=lambda i: (IT[i]['date'], i), reverse=True)
seq = list(dict.fromkeys(first + O['census_rest'] + O['dvs'] + O['srs']))  # dedupe (DVS ids also in srs), keep first
todo = [i for i in seq if i not in RA or (0.1 < RA[i]['p_yes'] < 0.9 and i not in RB)]
print('tasks', len(seq), 'todo', len(todo), flush=True)
lock = threading.Lock(); stop = threading.Event()
win = dict(t0=time.time(), secs=[], n429=0, nerr=0, n=0, na=0, nb=0)

def call(x, order):
    u, p = build_prompt(x['lang'], x['title'], x['title_long'], order)
    t0 = time.time()
    ch, meta = pai.chat([{"role": "user", "content": u}, {"role": "assistant", "content": p}], model=MODEL, max_tokens=1,
                        tag=f'bern2-s8-{order}', tag_cap_usd=2.40 if order == 'a' else 0.50, logprobs=True, top_logprobs=20,
                        continue_final_message=True, add_generation_prompt=False)
    fp = meta['resp'].get('system_fingerprint'); served = meta['resp'].get('model')
    d = pai.read_codes(ch, ["A", "B"]); pa_, pb_ = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
    py = (pa_ if order == 'a' else pb_) / (pa_ + pb_)
    row = dict(id=x['id'], body=x['body'], lang=x['lang'], p_yes=py, codes=d, fp=fp, served=served, latency=round(time.time() - t0, 3),
               secs=meta.get('secs'), http=meta.get('http'), cached=meta.get('cached'), pt=meta.get('prompt_tokens'), ts=round(t0, 3))
    with lock:
        if fp != FP_EXPECTED:
            open(f'{HERE}/raw/foreign_fp.jsonl', 'a').write(json.dumps(row) + '\n'); stop.set(); return None
        open(f'{HERE}/raw/{order}.jsonl', 'a').write(json.dumps(row, ensure_ascii=False) + '\n')
        (RA if order == 'a' else RB)[x['id']] = row
        win['n'] += 1; win['n' + order] += 1
        if not meta.get('cached'):
            win['secs'].append(meta.get('secs') or 0); win['n429'] += sum(1 for s in meta.get('http') or [] if s == 429)
        if win['n'] >= 500:
            dt = time.time() - win['t0']; s = sorted(win['secs']) or [0]
            rec = dict(ts=round(time.time()), order=f"a{win['na']}+b{win['nb']}", calls=win['n'], wall_s=round(dt, 1), req_per_s=round(win['n'] / dt, 3),
                       http_p50=round(statistics.median(s), 3), http_p95=round(s[int(0.95 * (len(s) - 1))], 3), n429=win['n429'],
                       errors=win['nerr'], workers=W)
            open(f'{HERE}/raw/throughput.jsonl', 'a').write(json.dumps(rec) + '\n'); print(rec, flush=True)
            win.update(t0=time.time(), secs=[], n429=0, nerr=0, n=0, na=0, nb=0)
    return py

def task(i):
    if stop.is_set(): return
    x = IT[i]
    try:
        pa = RA[i]['p_yes'] if i in RA else call(x, 'a')
        if pa is not None and 0.1 < pa < 0.9 and i not in RB: call(x, 'b')
    except Exception as e:
        with lock:
            win['nerr'] += 1
            open(f'{HERE}/raw/errors.jsonl', 'a').write(json.dumps(dict(id=i, err=repr(e)[:300], ts=time.time())) + '\n')
        if 'BUDGET' in str(e): stop.set()

with ThreadPoolExecutor(W) as ex:
    list(ex.map(task, todo))
print('finished', time.strftime('%H:%M:%S', time.gmtime()), 'stop', stop.is_set(), flush=True)
