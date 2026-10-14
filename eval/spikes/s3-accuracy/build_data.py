"""Build S3 inputs (no network, no LLM):
 data/curia300.json  : 300 clean-pool affairs = BFH sample positions 0-99 (dev, inside BFH's dev 150) and 150-349 (test,
                       inside BFH's test 350); gold Curia tags, BFH scores, DE/FR/IT title+text, BM25 neighbours per language.
 data/aps.json       : 298 APS-gold affairs with OPD/Curia titles and Curia DE text where fetched.
 data/dvs.json       : 30 DVS positives + 300 random affairs (10 per positive, same body and begin year)."""
import gzip, json, math, os, random, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s3lib import D2, DATA, clean, guess_lang

bfh = [json.loads(l) for l in gzip.open(f'{D2}/bfh/baseline_predictions_de.jsonl.gz', 'rt')]
assert len(bfh) == 500
sel = [(i, 'dev') for i in range(0, 100)] + [(i, 'test') for i in range(150, 350)]
ids = {bfh[i]['curia_id'] for i, _ in sel}

oracle = {}
for l in gzip.open(f'{D2}/oracle_curia.jsonl.gz', 'rt'):
    r = json.loads(l); oracle[r['curia_id']] = r

texts = {}
for lang in ('de', 'fr', 'it'):
    for l in gzip.open(f'{D2}/curia_cleanpool_texts_{lang}.jsonl.gz', 'rt'):
        r = json.loads(l)
        if r['ID'] in ids:
            body = clean(r.get('SubmittedText')) or clean(r.get('InitialSituation')) or clean(r.get('Description'))
            reason = clean(r.get('ReasonText'))
            texts[(r['ID'], lang)] = dict(title=clean(r.get('Title')), text=" ".join(x for x in (body, reason) if x))

# ---- BM25 over pre-clean-pool tagged titles, per language
TOK = re.compile(r"\w+")
STOP = set("der die das und oder für von mit des den dem ein eine einer eines zur zum auf aus bei nach über unter vom "
           "les des une pour par sur aux dans avec est que qui son ses leur "
           "della delle degli dei per con nel nella sul sulla che una gli alla allo".split())
def toks(s):
    return [w for w in TOK.findall((s or '').lower()) if len(w) >= 3 and w not in STOP and not w.isdigit()]

class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.docs = docs; self.N = len(docs); self.k1, self.b = k1, b
        self.len = [len(d) for d in docs]; self.avg = sum(self.len) / self.N
        self.inv = collections.defaultdict(list)
        for j, d in enumerate(docs):
            for w, c in collections.Counter(d).items(): self.inv[w].append((j, c))
        self.idf = {w: math.log(1 + (self.N - len(p) + 0.5) / (len(p) + 0.5)) for w, p in self.inv.items()}
    def top(self, q, k):
        sc = collections.defaultdict(float)
        for w in set(q):
            if w not in self.inv: continue
            idf = self.idf[w]
            for j, c in self.inv[w]:
                sc[j] += idf * c * (self.k1 + 1) / (c + self.k1 * (1 - self.b + self.b * self.len[j] / self.avg))
        return sorted(sc.items(), key=lambda x: -x[1])[:k]

pool = [o for o in oracle.values() if not o['clean_pool'] and o['tags'] and o['submitted'] < '2024-11-06']
print('memory pool (tagged, submitted < 2024-11-06):', len(pool))
nb = {}
for lang in ('de', 'fr', 'it'):
    P = [o for o in pool if o['titles'].get(lang)]
    bm = BM25([toks(o['titles'][lang]) for o in P])
    print(lang, 'pool docs', len(P), flush=True)
    for cid in ids:
        tx = texts.get((cid, lang)) or {}
        title = tx.get('title') or oracle[cid]['titles'].get(lang) or ''
        q = toks(title) * 2 + toks((tx.get('text') or '')[:400])
        nb[(cid, lang)] = [dict(curia_id=P[j]['curia_id'], title=P[j]['titles'][lang], tags=P[j]['tags'], score=round(s, 2))
                           for j, s in bm.top(q, 8)]

items = []
for i, split in sel:
    b = bfh[i]; cid = b['curia_id']; o = oracle[cid]
    it = dict(curia_id=cid, split=split, bfh_pos=i, type=o['type'], gold=sorted(o['tags']), bfh=b['scores'],
              short_number=o['short_number'], submitted=o['submitted'], lang={})
    for lang in ('de', 'fr', 'it'):
        tx = texts.get((cid, lang)) or {}
        title = tx.get('title') or o['titles'].get(lang) or ''
        text = tx.get('text') or ''
        it['lang'][lang] = dict(title=title, text=text, text_lang=guess_lang(title + ' ' + text[:1500]),
                                nb=nb[(cid, lang)])
    items.append(it)
json.dump(items, open(f'{DATA}/curia300.json', 'w'), ensure_ascii=False)
for lang in ('de', 'fr', 'it'):
    c = collections.Counter(it['lang'][lang]['text_lang'] for it in items)
    print(lang, 'text-language of item:', dict(c), 'with text', sum(bool(it['lang'][lang]['text']) for it in items))

# kNN memory-only baseline sanity: share of items where a top-5 neighbour shares a gold tag
for lang in ('de', 'fr', 'it'):
    hit = sum(bool(set(it['gold']) & {t for n in it['lang'][lang]['nb'][:5] for t in n['tags']}) for it in items)
    print(lang, 'items with a gold tag among top-5 neighbours', hit, '/', len(items))

# ---- APS
aps = [json.loads(l) for l in open(f'{D2}/aps_gold_sample.jsonl')]
o2c = {o['opd_affair_id']: o for o in oracle.values()}
at = {}
p = f'{DATA}/aps_curia_texts_de.jsonl.gz'
for l in gzip.open(p, 'rt'):
    r = json.loads(l)
    body = clean(r.get('SubmittedText')) or clean(r.get('InitialSituation')) or clean(r.get('Description'))
    at[r['ID']] = dict(title=clean(r.get('Title')), text=" ".join(x for x in (body, clean(r.get('ReasonText'))) if x))
opd_need = {a['opd_affair_id'] for a in aps}
opd = {}
for l in gzip.open('/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz', 'rt'):
    if '"body_key":"CHE"' not in l: continue
    r = json.loads(l)
    if r['id'] in opd_need: opd[r['id']] = r
out = []
for a in aps:
    o = o2c.get(a['opd_affair_id']); r = opd.get(a['opd_affair_id'], {})
    tx = at.get(o['curia_id']) if o else None
    title = (tx or {}).get('title') or (o or {}).get('titles', {}).get('de') or r.get('title_de') or ''
    tl = r.get('title_long_de') or ''
    out.append(dict(opd_affair_id=a['opd_affair_id'], curia_number=a['curia_number'], chapter_name=a['chapter_name'],
                    chapter_code=a['chapter_code'], subtopic_name=a.get('subtopic_name'), join_quality=a['join_quality'],
                    keyword_chapters=a.get('keyword_chapters'), curia_tags=(o or {}).get('tags'),
                    title=title, title_long=tl if tl and tl != title else '', text=(tx or {}).get('text') or '',
                    has_curia_text=bool(tx and tx['text'])))
json.dump(out, open(f'{DATA}/aps.json', 'w'), ensure_ascii=False)
print('aps', len(out), 'with curia text', sum(x['has_curia_text'] for x in out), 'title-only', sum(not x['text'] for x in out))

# ---- DVS + random negatives
dvs = json.load(open(f'{D2}/dvs_items.json'))
pos_ids = {d['opd_affair_id'] for d in dvs}
bodies = {d['opd_body_key'] for d in dvs}
cand = collections.defaultdict(list); posrec = {}
for l in gzip.open('/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz', 'rt'):
    m = re.search(r'"body_key":"([^"]*)"', l)
    if not m or m.group(1) not in bodies: continue
    r = json.loads(l)
    yr = (r.get('begin_date') or '')[:4]
    slim = dict(opd_affair_id=r['id'], body=r['body_key'], year=yr, type=r.get('type_harmonized_en'),
                title=r.get('title_de') or r.get('title_fr') or r.get('title_it') or '',
                title_long=r.get('title_long_de') or r.get('title_long_fr') or '',
                title_lang='de' if r.get('title_de') else ('fr' if r.get('title_fr') else 'it'))
    if r['id'] in pos_ids: posrec[r['id']] = slim
    else: cand[(r['body_key'], yr)].append(slim)
rng = random.Random(20261013)
neg = []; used = set()
for d in dvs:
    pr = posrec[d['opd_affair_id']]
    c = [x for x in cand[(pr['body'], pr['year'])] if x['opd_affair_id'] not in used and x['title']]
    if len(c) < 10:  # fall back to neighbouring years of the same body
        for dy in (1, -1, 2, -2):
            c += [x for x in cand[(pr['body'], str(int(pr['year'] or 0) + dy))] if x['opd_affair_id'] not in used and x['title']]
    pick = rng.sample(c, min(10, len(c)))
    for x in pick: used.add(x['opd_affair_id'])
    neg += pick
pos = [dict(posrec[d['opd_affair_id']], dvs_title=d['title']) for d in dvs]
json.dump(dict(pos=pos, neg=neg), open(f'{DATA}/dvs.json', 'w'), ensure_ascii=False)
print('dvs pos', len(pos), 'neg', len(neg), collections.Counter(x['body'] for x in neg).most_common())
