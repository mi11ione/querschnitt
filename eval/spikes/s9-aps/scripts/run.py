"""S9 runner (resumable, 3 worker threads total, all designs). Re-builds items from disk each round while fetching continues.
  d0a  L1 (c) DE identity order           d0b  L1 (c) DE S1 permutation        (D0 = geometric mean of d0a, d0b)
  d1   joint L2 over D0-arithmetic top-3/top-2 chapters, top chapter first (1 call)
  d2fr L1 (c) FR prompt / FR chapter names / DE subtopic names, identity order, on the FR title + text
  d3m  L1 (c) DE identity order + 5 BM25 nearest gold affairs (DE titles; ideation-1 297 + other S9 items) with their chapter;
       runs only after both fetchers finished (pool frozen to data/d3_neighbours.json)
Rows -> raw/<phase>.jsonl with model + system_fingerprint; a different fingerprint stops the run (row -> raw/offbuild.jsonl)."""
import json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s9lib
from s9lib import (DATA, RAW, HERE, BUILD, CODES, CODES_EXT, S1PERM, q1_prompt, q1_prompt_fr, q1_prompt_mem, q2_prompt,
                   q2_chapters, m1, probs_from_codes, log, load, toks, BM25)
WORKERS = 3
STOP = threading.Event()
PHASES = ['d0a', 'd0b', 'd1', 'd2fr', 'd3m']


def fetch_done():
    ok = True
    for f in ('fetch_aps.log', 'fetch_curia.log'):
        p = f'{DATA}/{f}'
        ok &= os.path.exists(p) and any(l.startswith('DONE') for l in open(p))
    return ok


def neighbours(items):
    p = f'{DATA}/d3_neighbours.json'
    if os.path.exists(p):
        return {int(k): v for k, v in json.load(open(p)).items()}
    old = json.load(open(f'{DATA}/mem_ideation1.json'))
    pool = [dict(oid=m['oid'], title=m['title'], chapter=m['chapter'], src='ideation1') for m in old] + \
           [dict(oid=it['oid'], title=it['de']['title'], chapter=it['chapter'], src='s9') for it in items]
    bm = BM25([toks(x['title']) for x in pool])
    nb = {}
    for it in items:
        q = toks(it['de']['title']) * 2 + toks((it['de']['text'] or '')[:400])
        hits = [j for j, s in bm.top(q, 6 + 5) if pool[j]['oid'] != it['oid']][:5]
        nb[it['oid']] = [dict(oid=pool[j]['oid'], title=pool[j]['title'], chapter=pool[j]['chapter'], src=pool[j]['src']) for j in hits]
    json.dump(nb, open(p, 'w'), ensure_ascii=False)
    return nb


def item_text(it, lang):
    x = it[lang]; return dict(title=x['title'], title_long=x['title_long'], text=x['text'])


def run(t):
    if STOP.is_set(): return t['key'], 'stopped'
    ph = t['phase']; it = t['it']; tag = f'bern2-s9-{ph}'
    try:
        if ph in ('d0a', 'd0b', 'd2fr', 'd3m'):
            perm = S1PERM if ph == 'd0b' else list(range(25))
            if ph == 'd2fr': u, p = q1_prompt_fr(item_text(it, 'fr'), perm)
            elif ph == 'd3m': u, p = q1_prompt_mem(item_text(it, 'de'), perm, [(n['title'], n['chapter']) for n in t['nb']])
            else: u, p = q1_prompt(item_text(it, 'de'), perm)
            d, rec = m1(u, p, tag, CODES)
            row = dict(key=t['key'], oid=it['oid'], rec=rec, codes=d, p=probs_from_codes(d, perm),
                       mass=round(sum(__import__('math').exp(v) for v in d.values()), 5))
            if ph == 'd3m': row['nb'] = [dict(oid=n['oid'], chapter=n['chapter'], src=n['src']) for n in t['nb']]
        else:
            u, p, opts, codes = q2_prompt(item_text(it, 'de'), t['chs'])
            d, rec = m1(u, p, tag, codes)
            pv = [0.0] * (len(opts) + 1)
            for c, l in d.items(): pv[codes.index(c)] = __import__('math').exp(l)
            s = sum(pv) or 1
            row = dict(key=t['key'], oid=it['oid'], rec=rec, codes=d, chs=t['chs'], opts=opts, p=[v / s for v in pv],
                       mass=round(sum(__import__('math').exp(v) for v in d.values()), 5))
        if rec['fp'] != BUILD or rec['model'] != s9lib.MODEL:
            log(f'{RAW}/offbuild.jsonl', row); STOP.set()
            return t['key'], f"OFFBUILD {rec['model']} {rec['fp']}"
        log(f'{RAW}/{ph}.jsonl', row)
        return t['key'], 'ok'
    except Exception as e:
        log(f'{RAW}/errors.jsonl', dict(key=t['key'], err=repr(e)[:500], t=time.time()))
        if 'BUDGET' in str(e): STOP.set()
        return t['key'], repr(e)[:200]


def todo(items, final):
    done = {ph: set(load(f'{RAW}/{ph}.jsonl', 'key')) for ph in PHASES}
    d0a, d0b = load(f'{RAW}/d0a.jsonl'), load(f'{RAW}/d0b.jsonl')
    ts = {ph: [] for ph in PHASES}
    nb = neighbours(items) if final else None
    for it in items:
        o = it['oid']
        for ph in ('d0a', 'd0b'):
            k = f'{ph}-{o}'
            if k not in done[ph]: ts[ph].append(dict(key=k, phase=ph, it=it))
        if o in d0a and o in d0b and f'd1-{o}' not in done['d1']:
            pa = [(x + y) / 2 for x, y in zip(d0a[o]['p'], d0b[o]['p'])]
            ts['d1'].append(dict(key=f'd1-{o}', phase='d1', it=it, chs=q2_chapters(pa)))
        if it['fr']['title'] and f'd2fr-{o}' not in done['d2fr']:
            ts['d2fr'].append(dict(key=f'd2fr-{o}', phase='d2fr', it=it))
        if final and f'd3m-{o}' not in done['d3m'] and o in nb:
            ts['d3m'].append(dict(key=f'd3m-{o}', phase='d3m', it=it, nb=nb[o]))
    # D0 first (both orders interleaved), then D1, D2, D3
    d0 = [x for pair in zip(ts['d0a'], ts['d0b']) for x in pair] + ts['d0a'][len(ts['d0b']):] + ts['d0b'][len(ts['d0a']):]
    return d0 + ts['d1'] + ts['d2fr'] + ts['d3m']


if __name__ == '__main__':
    os.makedirs(RAW, exist_ok=True)
    rnd = 0
    while not STOP.is_set():
        final = fetch_done()
        subprocess.run([sys.executable, '-I', f'{HERE}/scripts/build_items.py'], check=True)
        items = json.load(open(f'{DATA}/items.json'))
        ts = todo(items, final)
        print(time.strftime('%H:%M:%S'), 'round', rnd, 'items', len(items), 'final', final, 'todo', len(ts), flush=True)
        if not ts:
            if final: break
            time.sleep(60); rnd += 1; continue
        ts = ts[:600]   # re-plan regularly so new items and D1 dependencies get picked up
        with ThreadPoolExecutor(WORKERS) as ex:
            for i, (k, st) in enumerate(ex.map(run, ts)):
                if st != 'ok' or i % 100 == 0: print(i, k, st, flush=True)
        rnd += 1
    print('END stop=', STOP.is_set(), 'spent bern2-s9-*:', round(sum(v for k, v in pai._read_ledger()[1].items() if k.startswith('bern2-s9-')), 4)
          if (pai := s9lib.pai) else '', flush=True)
