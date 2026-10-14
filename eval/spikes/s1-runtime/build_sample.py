"""S1: build a stratified sample of OPD affairs (federal/cantonal/communal x de/fr/it, some title-only) plus a fresh
pool for throughput runs, and compute the on-disk text-coverage statistics. Run with python3 -I. No network."""
import gzip, json, glob, os, random, re, collections
OUT = os.path.dirname(os.path.abspath(__file__))
OPD = '/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd'
W = '/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a'
rng = random.Random(20261013)

bodies = {}
for l in gzip.open(f'{OPD}/bodies.ndjson.gz', 'rt'):
    d = json.loads(l); bodies[d['body_key']] = d

def level(bk):
    if bk == 'CHE': return 'federal'
    t = (bodies.get(bk) or {}).get('type')
    if t == 'canton' or (len(bk) == 2 and bk.isalpha()): return 'cantonal'
    if bk.isdigit() or t == 'municipality': return 'communal'
    return 'other'

affairs = {}
for l in gzip.open(f'{OPD}/affairs.ndjson.gz', 'rt'):
    d = json.loads(l)
    affairs[d['id']] = {k: d.get(k) for k in ('id', 'body_key', 'number', 'title_de', 'title_fr', 'title_it',
                                              'title_long_de', 'title_long_fr', 'title_long_it', 'type_name_de',
                                              'type_harmonized_de', 'begin_date')}
N = len(affairs)

# --- coverage: which affairs have a substantive text (texts table) or a document (docs table) in OPD
SUBST_SKIP = {'Titel des Geschäftes'}
has_text = set()
f = gzip.open(f'{W}/data/census/texts.tsv.gz', 'rt'); f.readline()
for l in f:
    p = l.rstrip('\n').split('\t')
    if len(p) >= 6 and p[3] not in SUBST_SKIP and p[5].isdigit() and int(p[5]) > 200:
        has_text.add(int(p[2]))
has_doc = set()
f = gzip.open(f'{W}/data/census/docs.tsv.gz', 'rt'); hdr = f.readline().rstrip('\n').split('\t')
for l in f:
    p = l.rstrip('\n').split('\t')
    if len(p) < 7 or not p[2]: continue
    if p[5] == 'ok' and p[6].isdigit() and int(p[6]) > 200:
        has_doc.add(int(p[2]))

# --- on-disk extracted PDF texts: sha12 -> path; doc id -> sha12; doc id -> affair
sha_path = {os.path.basename(p)[:12]: p for p in glob.glob(f'{W}/.work/text/*.json')}
aff_docs = collections.defaultdict(list)
url_sha = {}
for l in open(f'{W}/.work/adapters/url_cache.jsonl'):
    try: d = json.loads(l)
    except Exception: continue
    sh = (d.get('meta') or {}).get('sha256')
    if sh and sh[:12] in sha_path: url_sha[d['url']] = sh[:12]
for l in gzip.open(f'{W}/.work/convert/docs_index.jsonl.gz', 'rt'):
    if not l.strip(): continue
    d = json.loads(l)
    if d['a'] and d['url'] in url_sha: aff_docs[d['a']].append((0, url_sha[d['url']], d['name']))
for p in glob.glob(f'{W}/.work/adapters/state/*.jsonl'):
    for l in open(p):
        try: d = json.loads(l)
        except Exception: continue
        for t in d.get('tried') or []:
            sh = ((t or {}).get('meta') or {}).get('sha256')
            if sh and sh[:12] in sha_path and d.get('affair_id'):
                aff_docs[d['affair_id']].append((1, sh[:12], t.get('title') or ''))
ondisk = {a for a in aff_docs if a in affairs}

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', s).strip()

def pdf_text(a):
    for did, sh, name in sorted(aff_docs[a]):
        d = json.load(open(sha_path[sh]))
        t = clean(' '.join(d['pages']))
        if len(t) > 300: return t[:1500], f'pdf:{sh}'
    return None, None

def lang_of(a):
    langs = [x for x in ('de', 'fr', 'it') if a.get(f'title_{x}')]
    return langs

def mk(a, lang, text, src):
    return dict(id=a['id'], body=a['body_key'], level=level(a['body_key']), lang=lang,
                title=clean(a.get(f'title_{lang}')), title_long=clean(a.get(f'title_long_{lang}')),
                type=a.get('type_harmonized_de') or a.get('type_name_de'), text=text or '', text_src=src or 'title-only')

sample, used = [], set()
# federal with text: the 15 fed/texts files on disk (submitted text = 'member', else 'reason')
for p in sorted(glob.glob(f'{W}/.work/fed/texts/*.json')):
    d = json.load(open(p)); a = affairs.get(d['affair'])
    if not a: continue
    t = clean(d['rows'].get('member') or d['rows'].get('reason'))[:1500]
    sample.append(mk(a, d['slot'], t, 'fed_texts:member')); used.add(a['id'])

def pick(pool, k, lang_req=None):
    out = []
    rng.shuffle(pool)
    for a in pool:
        if len(out) >= k: break
        if a['id'] in used: continue
        L = lang_of(a)
        lang = lang_req if lang_req in L else (None if lang_req else (L[0] if L else None))
        if not lang: continue
        out.append((a, lang)); used.add(a['id'])
    return out

che = [a for a in affairs.values() if a['body_key'] == 'CHE']
for lang in ('de', 'fr', 'it'):
    for a, L in pick(che, 9, lang): sample.append(mk(a, L, None, None))     # federal title-only (text not on disk)

def lang_pref(a):
    L = lang_of(a)
    return L
for lev, quota in (('cantonal', 33), ('communal', 33)):
    pool = [affairs[i] for i in ondisk if level(affairs[i]['body_key']) == lev]
    bylang = collections.defaultdict(list)
    for a in pool:
        L = lang_of(a)
        if len(L) == 1: bylang[L[0]].append(a)
    per = {'de': quota // 3 + 3, 'fr': quota // 3, 'it': quota // 3 - 3}
    for lang, k in per.items():
        got = 0
        for a, L in pick(bylang[lang], k * 2, lang):
            if got >= k: break
            t, src = pdf_text(a['id'])
            if t: sample.append(mk(a, L, t, src)); got += 1
    # a few title-only cantonal/communal
    nontext = [a for a in affairs.values() if level(a['body_key']) == lev and a['id'] not in has_doc and a['id'] not in has_text]
    for a, L in pick(nontext, 4): sample.append(mk(a, L, None, None))

for i, s in enumerate(sample): s['sid'] = i
json.dump(sample, open(f'{OUT}/sample.json', 'w'), ensure_ascii=False, indent=0)

# fresh pool for throughput (disjoint from sample): affairs with on-disk text or title-only, mixed
fresh = []
pool = [affairs[i] for i in ondisk if i not in used]
for a, L in pick(pool, 200):
    t, src = pdf_text(a['id'])
    fresh.append(mk(a, L, t, src))
for a, L in pick(che, 60): fresh.append(mk(a, L, None, None))
rng.shuffle(fresh)
json.dump(fresh, open(f'{OUT}/fresh_pool.json', 'w'), ensure_ascii=False, indent=0)

lev_count = collections.Counter(level(a['body_key']) for a in affairs.values())
any_text = has_text | has_doc
cov = dict(n_affairs=N, by_level=dict(lev_count),
           with_substantive_text_row=len(has_text & affairs.keys()), with_doc_ok=len(has_doc & affairs.keys()),
           with_any_text_or_doc=len(any_text & affairs.keys()),
           title_only_share=round(1 - len(any_text & affairs.keys()) / N, 4),
           title_only_by_level={lv: round(1 - sum(1 for a in affairs.values() if level(a['body_key']) == lv and a['id'] in any_text) / c, 4)
                                for lv, c in lev_count.items()},
           ondisk_extracted_affairs=len(ondisk), fed_texts_ondisk=15,
           sample=dict(n=len(sample), by=collections.Counter(f"{s['level']}/{s['lang']}/{'text' if s['text'] else 'title'}" for s in sample)),
           fresh_pool=len(fresh))
json.dump(cov, open(f'{OUT}/coverage.json', 'w'), indent=1)
print(json.dumps(cov, indent=1))
