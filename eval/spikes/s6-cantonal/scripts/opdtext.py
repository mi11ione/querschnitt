"""S6: load OPD affairs + map on-disk extracted cantonal/communal PDF texts (same mapping as S1 build_sample.py).
No network. Run with python3 -I."""
import gzip, json, glob, os, re, collections
OPD = '/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd'
W = '/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a'

bodies = {}
for l in gzip.open(f'{OPD}/bodies.ndjson.gz', 'rt'):
    d = json.loads(l); bodies[d['body_key']] = d


def level(bk):
    if bk == 'CHE': return 'federal'
    t = (bodies.get(bk) or {}).get('type')
    if t == 'canton' or (len(bk) == 2 and bk.isalpha()): return 'cantonal'
    if bk.isdigit() or t == 'municipality': return 'communal'
    return 'other'


def body_name(bk):
    b = bodies.get(bk) or {}
    for k in ('name_de', 'name', 'name_fr', 'name_it'):
        if b.get(k): return b[k] if isinstance(b[k], str) else str(b[k])
    return bk


def load_affairs():
    affairs = {}
    for l in gzip.open(f'{OPD}/affairs.ndjson.gz', 'rt'):
        d = json.loads(l)
        affairs[d['id']] = {k: d.get(k) for k in ('id', 'body_key', 'number', 'title_de', 'title_fr', 'title_it',
                                                  'title_long_de', 'title_long_fr', 'title_long_it', 'type_name_de',
                                                  'type_name_fr', 'type_name_it', 'type_harmonized_de', 'begin_date')}
    return affairs


def census_sets():
    has_text, has_doc = set(), set()
    f = gzip.open(f'{W}/data/census/texts.tsv.gz', 'rt'); f.readline()
    for l in f:
        p = l.rstrip('\n').split('\t')
        if len(p) >= 6 and p[3] != 'Titel des Geschäftes' and p[5].isdigit() and int(p[5]) > 200:
            has_text.add(int(p[2]))
    f = gzip.open(f'{W}/data/census/docs.tsv.gz', 'rt'); f.readline()
    for l in f:
        p = l.rstrip('\n').split('\t')
        if len(p) < 7 or not p[2]: continue
        if p[5] == 'ok' and p[6].isdigit() and int(p[6]) > 200:
            try: has_doc.add(int(p[2]))
            except ValueError: pass
    return has_text, has_doc


def doc_map():
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
        if d['a'] and d['url'] in url_sha: aff_docs[d['a']].append((0, url_sha[d['url']], d.get('name') or ''))
    for p in glob.glob(f'{W}/.work/adapters/state/*.jsonl'):
        for l in open(p):
            try: d = json.loads(l)
            except Exception: continue
            for t in d.get('tried') or []:
                sh = ((t or {}).get('meta') or {}).get('sha256')
                if sh and sh[:12] in sha_path and d.get('affair_id'):
                    aff_docs[d['affair_id']].append((1, sh[:12], t.get('title') or ''))
    return sha_path, aff_docs


def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', s).strip()


# "obvious answer-only documents": the government's / executive's reply, judged from the doc name or the opening
ANS_NAME = re.compile(r'antwort|beantwortung|stellungnahme des (regierungs|stadt|gemeinde)rat|réponse|reponse|risposta|'
                      r'rapport du conseil (d.etat|communal|municipal)|messaggio municipale.*risposta', re.I)
ANS_HEAD = re.compile(r'^.{0,300}?(antwort des (regierungs|stadt|gemeinde)rates|beantwortung der|der (regierungs|stadt|gemeinde)rat '
                      r'beantwortet|réponse du (conseil|gouvernement|municipal)|le conseil (d.etat|communal|municipal) répond|'
                      r'risposta del (consiglio|municipio)|il municipio risponde|il consiglio di stato risponde)', re.I)


INSTR = re.compile(r'anfrage|interpellation|motion|postulat|auftrag|vorstoss|erkundigt|fragen|interrogazion|interpellanz|mozion|'
                   r'chiede|domand|question|résolution|resolution|rappel|demande', re.I)
WORD = re.compile(r"[A-Za-zÀ-ÿ]{5,}")


def restates(t, title):
    """Answer document whose opening restates the affair: names the instrument and >= half of the title's long words."""
    if not INSTR.search(t): return False
    tw = {w.lower() for w in WORD.findall(title or '')}
    if not tw: return True
    low = t.lower()
    return sum(w in low for w in tw) >= max(1, len(tw) / 2)


def pdf_text(aid, sha_path, aff_docs, title='', n=1500):
    """Prefer the first non-answer document with > 300 chars; else the first answer document whose first n chars restate
    the affair (instrument named + title words); answer documents that do not ("obvious answer-only") are skipped.
    Returns (text, src, kind, n_answer_docs_skipped)."""
    skipped, seen, ans_ok = 0, set(), None
    for did, sh, name in sorted(aff_docs.get(aid, [])):
        if sh in seen: continue
        seen.add(sh)
        d = json.load(open(sha_path[sh]))
        t = clean(' '.join(d.get('pages') or []))
        if len(t) <= 300: continue
        if ANS_NAME.search(name or '') or ANS_HEAD.search(t[:400]):
            if ans_ok is None and restates(t[:n], title): ans_ok = (t[:n], f'pdf:{sh}')
            else: skipped += 1
            continue
        return t[:n], f'pdf:{sh}', 'doc', skipped
    if ans_ok: return ans_ok[0], ans_ok[1], 'answer-doc-restating', skipped
    return None, None, None, skipped
