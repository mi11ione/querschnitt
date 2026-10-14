"""P8.5 correction loop (lead, per PREREG S8): the first 60 packet ids in loop_order.json are an editor's first decisions
(gold Y/N). Every other packet item is re-scored once (order a, yes=A) with the 4 most similar of those 60 (BM25 on titles)
shown as labelled examples. Before = the item's existing order-a p (no examples). F1 vs gold on the remaining items,
paired bootstrap 2,000. Usage: python3 -I loop.py   -> raw/loop.jsonl, loop.json"""
import json, math, re, sys, random, collections, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
import pai
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s8-dvs')
from common import E6, FP_EXPECTED, MODEL
H = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s8-dvs'
K = {r['pid']: r for r in map(json.loads, open(f'{H}/key.jsonl'))}
IT = {}
for x in json.load(open(f'{H}/items_cache.json')):
    IT[x['id']] = x
order = json.load(open(f'{H}/loop_order.json'))['order']
def rd(p):
    d = {}
    for line in open(p):
        x = line.rstrip('\n').split('\t')
        if len(x) >= 2 and x[0].startswith('D') and x[1].strip():
            d[x[0]] = 'Q' if (len(x) > 2 and x[2].strip() == '?') else x[1].strip().upper()
    return d
A, B, C = rd(f'{H}/ann_A.tsv'), rd(f'{H}/ann_B.tsv'), rd(f'{H}/ann_C.tsv')
gold = lambda i: A[i] if A.get(i) in ('Y', 'N') and A.get(i) == B.get(i) else C.get(i)
ex_ids, test_ids = order[:60], order[60:]
tok = lambda s: [w for w in re.findall(r'\w+', (s or '').lower()) if len(w) >= 3]
docs = {i: tok(IT[K[i]['oid']]['title']) for i in ex_ids}
df = collections.Counter(w for d in docs.values() for w in set(d)); N = len(docs); avg = sum(map(len, docs.values())) / N
def bm25(q, d, k1=1.2, b=0.75):
    tf = collections.Counter(d); s = 0.0
    for w in set(q):
        if w in tf:
            idf = math.log(1 + (N - df[w] + .5) / (df[w] + .5))
            s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
    return s
HDR = {'de': 'Beispiele, von einer Redaktorin entschieden:', 'fr': 'Exemples décidés par une rédactrice :', 'it': 'Esempi decisi da una redattrice:'}
def prompt(i):
    it = IT[K[i]['oid']]; lang = it['lang']; q, item, ti, tl, yes, no, fmt, key = E6[lang]
    nn = sorted(ex_ids, key=lambda e: (-bm25(tok(it['title']), docs[e]), e))[:4]
    exs = "\n".join(f"- {ti}: {IT[K[e]['oid']]['title'][:300]} → {'A' if gold(e) == 'Y' else 'B'}" for e in nn)
    blk = f"{ti}: {it['title'][:400]}" + (f"\n{tl}: {it['title_long'][:400]}" if it['title_long'] and it['title_long'] != it['title'] else '')
    u = f"{q}\n\nA = {yes}\nB = {no}\n\n{HDR[lang]}\n{exs}\n\n{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "', nn
def one(i):
    u, pre, nn = prompt(i)
    ch, meta = pai.chat([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], model=MODEL, max_tokens=1,
                        tag='bern2-s8-loop', tag_cap_usd=0.30, logprobs=True, top_logprobs=20, continue_final_message=True,
                        add_generation_prompt=False)
    fp = meta['resp'].get('system_fingerprint'); assert fp == FP_EXPECTED, fp
    d = pai.read_codes(ch, ['A', 'B']); pa, pb = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
    return dict(pid=i, p_after=pa / (pa + pb), examples=nn, fp=fp)
if __name__ == '__main__':
    out = f'{H}/raw/loop.jsonl'
    try: done = {json.loads(l)['pid'] for l in open(out)}
    except FileNotFoundError: done = set()
    lock = threading.Lock()
    with ThreadPoolExecutor(3) as ex, open(out, 'a') as f:
        for fu in as_completed([ex.submit(one, i) for i in test_ids if i not in done]):
            r = fu.result()
            with lock: f.write(json.dumps(r) + '\n'); f.flush()
    R = {json.loads(l)['pid']: json.loads(l) for l in open(out)}
    ids = [i for i in test_ids if i in R and gold(i) in ('Y', 'N')]
    def f1(sel, key):
        tp = sum(1 for i in sel if key(i) and gold(i) == 'Y'); fp = sum(1 for i in sel if key(i) and gold(i) == 'N')
        fn = sum(1 for i in sel if (not key(i)) and gold(i) == 'Y')
        P = tp / (tp + fp) if tp + fp else 0; Rr = tp / (tp + fn) if tp + fn else 0
        return (2 * P * Rr / (P + Rr) if P + Rr else 0), P, Rr
    before = lambda i: K[i]['p_a'] >= 0.5
    after = lambda i: R[i]['p_after'] >= 0.5
    fb, fa = f1(ids, before), f1(ids, after)
    rng = random.Random(5); ds = []
    for _ in range(2000):
        s = [rng.choice(ids) for _ in ids]; ds.append(f1(s, after)[0] - f1(s, before)[0])
    ds.sort()
    res = dict(n=len(ids), before=dict(F1=round(fb[0], 3), P=round(fb[1], 3), R=round(fb[2], 3)),
               after=dict(F1=round(fa[0], 3), P=round(fa[1], 3), R=round(fa[2], 3)),
               dF1=round(fa[0] - fb[0], 3), dF1_ci=(round(ds[50], 3), round(ds[1949], 3)),
               gain=ds[50] > 0, note='unweighted, packet items outside the first 60; before = order-a p without examples')
    json.dump(res, open(f'{H}/loop.json', 'w'), indent=1); print(json.dumps(res))
