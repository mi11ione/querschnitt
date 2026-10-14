"""S8 shared: population, language rule, S3 E6 prompt (verbatim copy), keyword regex, levels."""
import gzip, json, re, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
OPD = '/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd'
S3 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s3-accuracy'
S4 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s4-blindcheck'
LO, HI = '2026-01-01', '2026-10-06'
FP_EXPECTED = 'vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840'
MODEL = 'swiss-ai/apertus-v1.5-8b'
TAG_PREFIX = 'bern2-s8-'
CAP = 3.00

# verbatim copy of S3 run.py E6 (bern/ideation/spikes/s3-accuracy/run.py lines 74-87)
E6 = {"de": ("Betrifft das folgende parlamentarische Geschäft das Thema «Digitalisierung» (digitale Transformation der Verwaltung, "
             "E-Government, digitale Infrastruktur, Daten, Cybersicherheit, digitale Souveränität)?",
             "Geschäft", "Titel", "Langtitel", "Ja, das Geschäft betrifft Digitalisierung", "Nein, anderes Thema",
             "Antworte nur mit dem Buchstaben als JSON: {\"antwort\": \"<Buchstabe>\"}", "antwort"),
      "fr": ("L'objet parlementaire suivant concerne-t-il le thème « numérique » (transformation numérique de l'administration, "
             "cyberadministration, infrastructure numérique, données, cybersécurité, souveraineté numérique) ?",
             "Objet", "Titre", "Titre long", "Oui, l'objet concerne le numérique", "Non, autre thème",
             "Réponds uniquement par la lettre en JSON : {\"reponse\": \"<lettre>\"}", "reponse"),
      "it": ("Il seguente oggetto parlamentare riguarda il tema «digitalizzazione» (trasformazione digitale dell'amministrazione, "
             "e-government, infrastruttura digitale, dati, cibersicurezza, sovranità digitale)?",
             "Oggetto", "Titolo", "Titolo lungo", "Sì, l'oggetto riguarda la digitalizzazione", "No, altro tema",
             "Rispondi solo con la lettera in JSON: {\"risposta\": \"<lettera>\"}", "risposta")}

def build_prompt(lang, title, title_long, order):
    """exact S3 e6a/e6b branch. order 'a' = yes=A, 'b' = yes=B. returns (user, prefill)."""
    q, item, ti, tl, yes, no, fmt, key = E6[lang]
    opts = [("A", yes), ("B", no)] if order == 'a' else [("A", no), ("B", yes)]
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {title_long[:400]}" if title_long and title_long != title else '')
    u = f"{q}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\n{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "'

KW = re.compile(json.load(open(f'{S4}/keyword_baseline.json'))['kw'], re.I)
def kw_text(title, title_long):
    return title[:400] + ("\n" + title_long[:400] if title_long and title_long != title else '')

def load_bodies():
    B = {}
    for l in gzip.open(f'{OPD}/bodies.ndjson.gz'):
        b = json.loads(l); B[b['body_key']] = b
    return B

def level(key, B):
    if key == 'CHE': return 'federal'
    t = (B.get(key) or {}).get('type')
    if t == 'canton' and re.fullmatch(r'[A-Z]{2}', key): return 'cantonal'
    if key.isdigit() and t in ('city', 'municipality'): return 'communal'
    return 'other'

def pick_lang(a, B):
    """prompt language + text language. main = body lang; title in main if non-empty, else de->fr->it; rm/missing -> de prompt."""
    main = ((B.get(a['body_key']) or {}).get('lang') or '').lower()
    has = lambda l: bool((a.get('title_' + l) or '').strip())
    if main in ('de', 'fr', 'it') and has(main): return main, main
    for l in ('de', 'fr', 'it'):
        if has(l): return l, l
    if has('rm'): return 'de', 'rm'
    return 'de', None

PARL_FALLBACK = {'CHE': 'Schweizerische Bundesversammlung', 'LIE': 'Landtag des Fürstentums Liechtenstein'}
def parl_name(key, B):
    b = B.get(key) or {}
    return b.get('legislative_name') or PARL_FALLBACK.get(key) or f"Parlament {b.get('name') or key}"

def item_of(a, B):
    lang, tl_ = pick_lang(a, B)
    title = (a.get('title_' + tl_) or '') if tl_ else ''
    tlong = (a.get('title_long_' + tl_) or '') if tl_ else ''
    d = a['begin_date'][:10]
    y, w, _ = datetime.date.fromisoformat(d).isocalendar()
    typ = a.get(f'type_name_{tl_}') if tl_ else None
    typ = typ or a.get('type_name_de') or a.get('type_name_fr') or a.get('type_name_it') or a.get(f'type_harmonized_{lang}') or a.get('type_harmonized_de') or ''
    return dict(id=a['id'], body=a['body_key'], level=level(a['body_key'], B), lang=lang, text_lang=tl_, title=title, title_long=tlong,
                date=d, week=f"{y}-W{w:02d}", type=typ, in_window=LO <= d <= HI, kw=bool(KW.search(kw_text(title, tlong))) if title else False)

def dvs_ids():
    D = json.load(open(f'{S3}/data/dvs.json'))
    return [x['opd_affair_id'] for x in D['pos']]

def load_items():
    """window affairs (+ the 30 DVS items even if outside the window), sorted newest first."""
    B = load_bodies(); dv = set(dvs_ids()); out = []
    for l in gzip.open(f'{OPD}/affairs.ndjson.gz'):
        a = json.loads(l); d = (a.get('begin_date') or '')[:10]
        if (d and LO <= d <= HI) or a['id'] in dv:
            it = item_of(a, B); it['on_dvs_list'] = a['id'] in dv; out.append(it)
    out.sort(key=lambda x: (x['date'], x['id']), reverse=True)
    return out, B
