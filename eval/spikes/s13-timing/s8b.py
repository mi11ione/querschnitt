"""S8b text lever (PREREG-ADDENDA 2026-10-13 21:20). S8 packet items, level federal, joined OPD id -> Curia id (S2 oracle_curia),
Curia DE clean-pool text = SubmittedText (+ ReasonText), HTML-stripped, first 1,500 chars. One call (order a, yes=A) with the S8 E6
prompt; item block = title + long title + "Text: <first 1,500 chars>" (label per prompt language). Compared against S8 gold,
paired with title-only order-a (key p_a >= 0.5) on the same items. Usage: python3 -I s8b.py -> raw/s8b.jsonl, s8b.json"""
import gzip, html, json, math, re, sys, random, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
import pai
S8 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s8-dvs'
sys.path.insert(0, S8)
from common import E6, FP_EXPECTED, MODEL
H = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s13-timing'
D2 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data'
TAG, TAG_CAP, TOTAL_CAP = 'bern2-s8b-text', 0.25, 0.60
TXT = {'de': 'Text', 'fr': 'Texte', 'it': 'Testo'}

K = {r['pid']: r for r in map(json.loads, open(f'{S8}/key.jsonl'))}
IT = {x['id']: x for x in json.load(open(f'{S8}/items_cache.json'))}


def rd(p):
    d = {}
    for line in open(p):
        x = line.rstrip('\n').split('\t')
        if len(x) >= 2 and x[0].startswith('D') and x[1].strip():
            d[x[0]] = 'Q' if (len(x) > 2 and x[2].strip() == '?') else x[1].strip().upper()
    return d


A, B, C = rd(f'{S8}/ann_A.tsv'), rd(f'{S8}/ann_B.tsv'), rd(f'{S8}/ann_C.tsv')
gold = lambda i: A[i] if A.get(i) in ('Y', 'N') and A.get(i) == B.get(i) else C.get(i)


def strip(h):
    if not h or h == 'None':
        return ''
    h = re.sub(r'<(br|/p|/h\d|/li|/div)[^>]*>', ' ', h, flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()


def texts():
    fed = {k['oid']: pid for pid, k in K.items() if k['level'] == 'federal'}
    o2c = {}
    for l in gzip.open(f'{D2}/oracle_curia.jsonl.gz'):
        r = json.loads(l)
        if r['opd_affair_id'] in fed:
            o2c[r['opd_affair_id']] = str(r['curia_id'])
    T = {}
    for l in gzip.open(f'{D2}/curia_cleanpool_texts_de.jsonl.gz'):
        r = json.loads(l); T.setdefault(str(r['ID']), r)
    out = {}
    for oid, pid in fed.items():
        c = o2c.get(oid)
        if c and c in T:
            t = (strip(T[c].get('SubmittedText')) + ' ' + strip(T[c].get('ReasonText'))).strip()
            if t:
                out[pid] = t[:1500]
    return dict(n_federal=len(fed), n_mapped=len(o2c), n_textrec=sum(1 for c in o2c.values() if c in T), n_text=len(out)), out


def build(pid, text):
    it = IT[K[pid]['oid']]; lang = it['lang']; q, item, ti, tl, yes, no, fmt, key = E6[lang]
    title, tlong = it['title'], it['title_long']
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {tlong[:400]}" if tlong and tlong != title else '') + f"\n{TXT[lang]}: {text}"
    u = f"{q}\n\nA = {yes}\nB = {no}\n\n{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "'


def one(pid, text):
    u, pre = build(pid, text)
    ch, meta = pai.chat([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], model=MODEL, max_tokens=1,
                        tag=TAG, tag_cap_usd=TAG_CAP, nocache=True, logprobs=True, top_logprobs=20,
                        continue_final_message=True, add_generation_prompt=False)
    fp = meta['resp'].get('system_fingerprint')
    d = pai.read_codes(ch, ['A', 'B']); pa, pb = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
    return dict(pid=pid, oid=K[pid]['oid'], lang=IT[K[pid]['oid']]['lang'], p_text=pa / (pa + pb), codes=d, http=meta['http'],
                served=meta['resp'].get('model'), fp=fp, pt=meta['prompt_tokens'], usd=meta['usd'], text_chars=len(text))


def prf(sel, key):
    tp = sum(1 for i in sel if key(i) and gold(i) == 'Y'); fp = sum(1 for i in sel if key(i) and gold(i) == 'N')
    fn = sum(1 for i in sel if (not key(i)) and gold(i) == 'Y')
    P = tp / (tp + fp) if tp + fp else 0.0; R = tp / (tp + fn) if tp + fn else 0.0
    return dict(F1=(2 * P * R / (P + R) if P + R else 0.0), P=P, R=R, tp=tp, fp=fp, fn=fn)


def analyse(R, ids, label):
    ids = [i for i in ids if i in R and gold(i) in ('Y', 'N')]
    before = lambda i: K[i]['p_a'] >= 0.5
    after = lambda i: R[i]['p_text'] >= 0.5
    b, a = prf(ids, before), prf(ids, after)
    rng = random.Random(13); dF, dR = [], []
    for _ in range(2000):
        s = [rng.choice(ids) for _ in ids]; x, y = prf(s, after), prf(s, before)
        dF.append(x['F1'] - y['F1']); dR.append(x['R'] - y['R'])
    dF.sort(); dR.sort()
    return dict(label=label, n=len(ids), n_gold_Y=sum(gold(i) == 'Y' for i in ids), title_only=b, title_text=a,
                dF1=a['F1'] - b['F1'], dF1_ci95=(dF[50], dF[1949]), dRecall=a['R'] - b['R'], dRecall_ci95=(dR[50], dR[1949]),
                flips_N_to_Y=sum(1 for i in ids if after(i) and not before(i)), flips_Y_to_N=sum(1 for i in ids if before(i) and not after(i)),
                bootstrap='paired, 2000, seed 13, percentile')


if __name__ == '__main__':
    stats, TX = texts(); print(stats)
    assert pai.spent(TAG) + pai.spent('bern2-s13-timing') < TOTAL_CAP - 0.05
    out = f'{H}/raw/s8b.jsonl'
    try: done = {json.loads(l)['pid'] for l in open(out)}
    except FileNotFoundError: done = set()
    lock = threading.Lock()
    with ThreadPoolExecutor(3) as ex, open(out, 'a') as f:
        for fu in as_completed([ex.submit(one, p, t) for p, t in sorted(TX.items()) if p not in done]):
            r = fu.result()
            with lock: f.write(json.dumps(r) + '\n'); f.flush()
            if r['fp'] != FP_EXPECTED:
                raise SystemExit(f"FINGERPRINT MISMATCH {r['fp']}")
    R = {json.loads(l)['pid']: json.loads(l) for l in open(out)}
    res = dict(stats=stats, fps=sorted({r['fp'] for r in R.values()}), usd=sum(r['usd'] for r in R.values()),
               all=analyse(R, list(TX), 'federal, all with text'),
               de_only=analyse(R, [p for p in TX if IT[K[p]['oid']]['lang'] == 'de'], 'federal, prompt de'),
               note='unweighted (packet design weights not applied); text is Curia DE for every item, prompt language = item language')
    json.dump(res, open(f'{H}/s8b.json', 'w'), indent=1, default=float); print(json.dumps(res, indent=1, default=float))
