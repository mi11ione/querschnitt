"""S13 + S8b summaries -> results.json (results.md written by hand from it). Usage: python3 -I analyse.py"""
import json, os, collections, sys
H = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s13-timing'
sys.path.insert(0, H)
from s13 import TOPICS, items
N = len(items())


def s13(topic):
    p = f'{H}/raw/s13_{topic}.jsonl'
    if not os.path.exists(p):
        return None
    R = [json.loads(l) for l in open(p)]
    runs = [json.loads(l) for l in open(f'{H}/raw/s13_runs.jsonl') if json.loads(l)['topic'] == topic]
    st = [r for r in runs if r['event'] == 'start'][-1]; en = [r for r in runs if r['event'] == 'end']
    T = sorted(r['t_done'] - st['t'] for r in R)
    wall = (en[-1]['t'] - st['t']) if en else None
    http = [h for r in R for h in r['http']]
    lat = sorted(r['latency'] for r in R)
    fl = [r for r in R if r['p_yes'] >= 0.5]
    return dict(topic=topic, n=len(R), n_target=N, complete=len(R) == N, workers=st['workers'],
                t_first50_s=T[49] if len(T) >= 50 else None, t_all_s=T[-1] if len(R) == N else None, wall_s=wall,
                decisions_per_s=len(R) / T[-1] if T else None, http_attempts=len(http), http_attempts_per_s=len(http) / T[-1] if T else None,
                n_429=sum(1 for h in http if h == 429), calls_with_429=sum(1 for r in R if 429 in r['http']),
                other_non200=sum(1 for h in http if h not in (200, 429)),
                latency_s=dict(median=lat[len(lat) // 2], p90=lat[int(.9 * len(lat))], max=lat[-1]),
                flags=len(fl), flags_by_level_lang=dict(sorted(collections.Counter(f"{r['level']}/{r['lang']}" for r in fl).items())),
                flags_p_ge_0_9=sum(1 for r in R if r['p_yes'] >= 0.9),
                fps=sorted({r['fp'] for r in R}), served=sorted({r['served'] for r in R}), usd=sum(r['usd'] for r in R),
                cached_any=any(r['cached'] for r in R))


res = dict(s13={t: s13(t) for t in TOPICS}, s13_population=dict(n=N, filter='items_cache date 2026-09-30..2026-10-06, in_window'))
if os.path.exists(f'{H}/s8b.json'):
    res['s8b'] = json.load(open(f'{H}/s8b.json'))
res['s8b_local'] = json.load(open(f'{H}/s8b_local.json')) if os.path.exists(f'{H}/s8b_local.json') else None
json.dump(res, open(f'{H}/results.json', 'w'), indent=1, ensure_ascii=False, default=float)
print(json.dumps(res, indent=1, ensure_ascii=False, default=float))
