"""S3 measurement runs. Usage: python3 -I run.py <phase> [workers<=8]
Rows -> raw/<phase>.jsonl (resume-safe). Worker processes (gw's per-call ledger scan is CPU-bound; S1 finding).
Phases (Curia, 300 affairs = data/curia300.json):
  e1n  DE names, identity order        e1d  DE names+descriptions, identity order
  e2n  DE names, permuted order B      e2d  DE names+descriptions, permuted order B
  e3a/e3b  DE label memory (k=K neighbours, BM25 titles, pre-2024-11 pool), orders id / B; desc per DESC_E3
  e4{fr,it}{a,b}  best design in FR/IT (only items with title+text in that language)
  e5a/e5b APS 24+none on 298 APS-gold affairs (S1 m1_prompt), orders id / S1-PERM
  e5t  L2 subtopic given true chapter      e5p  L2 subtopic given predicted chapter (from e5 avg)
  e6a/e6b Digitalisierung yes/no (2-code M1, both code orders) on 30 DVS + 300 random
  e6f  free generation (no list / with list) on 40 affairs"""
import json, os, sys, math, random, hashlib, re
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s3lib import *  # noqa
import s1lib

K = 5
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']
DESC_E3 = os.environ.get('S3_DESC_E3', '1') == '1'
DESC_E4 = os.environ.get('S3_DESC_E4', '1') == '1'
E4_MEM = os.environ.get('S3_E4_MEM', '1') == '1'
ITEMS = json.load(open(f'{DATA}/curia300.json'))
BYID = {it['curia_id']: it for it in ITEMS}
PERMS = dict(a=PERM_ID, b=PERM_B)
S1PERM = list(range(25)); random.Random(7).shuffle(S1PERM)   # S1's M4 permutation

def lang_ok(it, lang):
    x = it['lang'][lang]
    return bool(x['title']) and bool(x['text']) and x['text_lang'] in (lang, None) and not x['title'].startswith(('Titre suit', 'Titolo segue'))

def tasks(phase):
    if phase in ('e1n', 'e1d', 'e2n', 'e2d'):
        return [dict(key=f"{phase}-{it['curia_id']}", cid=it['curia_id']) for it in ITEMS]
    if phase in ('e1x1', 'e1x2'):
        return [dict(key=f"{phase}-{it['curia_id']}", cid=it['curia_id']) for it in ITEMS if it['split'] == 'test']
    if phase in ('e1m', 'e3m'):
        return [dict(key=f"{phase}-{it['curia_id']}", cid=it['curia_id']) for it in ITEMS]
    if phase in ('e3a', 'e3b'):
        return [dict(key=f"{phase}-{it['curia_id']}", cid=it['curia_id']) for it in ITEMS]
    if phase[:2] == 'e4':
        lang = phase[2:4]
        return [dict(key=f"{phase}-{it['curia_id']}", cid=it['curia_id']) for it in ITEMS if lang_ok(it, lang)]
    if phase in ('e5a', 'e5b'):
        A = json.load(open(f'{DATA}/aps.json'))
        return [dict(key=f"{phase}-{a['opd_affair_id']}", oid=a['opd_affair_id']) for a in A]
    if phase in ('e5t', 'e5p'):
        A = json.load(open(f'{DATA}/aps.json'))
        ch_true = {a['opd_affair_id']: APS_CODES.index(a['chapter_code']) for a in A
                   if a['subtopic_name'] in s1lib.SUBS[APS_CODES.index(a['chapter_code'])]}   # DE captures with a DE subtopic
        if phase == 'e5t':
            return [dict(key=f"e5t-{o}", oid=o, ch=c) for o, c in ch_true.items()]
        pr = e5_pred()
        return [dict(key=f"e5p-{o}", oid=o, ch=c) for o, c in pr.items() if c < 24 and c != ch_true.get(o)]
    if phase in ('e6a', 'e6b'):
        D = json.load(open(f'{DATA}/dvs.json'))
        return [dict(key=f"{phase}-{x['opd_affair_id']}", oid=x['opd_affair_id'], pos=p) for p, L in (("pos", D['pos']), ("neg", D['neg'])) for x in L]
    if phase == 'e6f':
        H = lambda s: hashlib.sha256(str(s).encode()).hexdigest()
        sel = sorted((it['curia_id'] for it in ITEMS if it['split'] == 'test'), key=H)[:40]
        return [dict(key=f"e6f-{arm}-{c}", cid=c, arm=arm) for c in sel for arm in ('free', 'list')]
    raise SystemExit(phase)

def e5_pred():
    """average of e5a/e5b chapter probs -> predicted chapter per affair"""
    acc = {}
    for ph in ('e5a', 'e5b'):
        for l in open(f'{RAW}/{ph}.jsonl'):
            r = json.loads(l); v = acc.setdefault(r['oid'], [0.0] * 25)
            for i, p in enumerate(r['p']): v[i] += p / 2
    return {o: max(range(25), key=lambda i: v[i]) for o, v in acc.items()}

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

FREE = {"free": ("Welches politische Sachthema behandelt das folgende Geschäft der Bundesversammlung? Nenne das Thema in höchstens drei Wörtern. "
                 "Wenn es kein Sachthema hat, antworte «kein Thema».\n\nGeschäft:\n{blk}\n\nAntworte als JSON: {{\"thema\": \"<Thema>\"}}"),
        "list": ("Welchem Sachbereich (Curia Vista) gehört das folgende Geschäft der Bundesversammlung an?\n\nSachbereiche:\n{lst}\n\n"
                 "Geschäft:\n{blk}\n\nAntworte nur mit dem Namen des Sachbereichs als JSON: {{\"sachbereich\": \"<Name>\"}}")}

_N = 0
def run(t):
    phase = t['key'].split('-')[0]; tag = f'bern-s3-{phase}'
    global _N
    _N += 1
    if _N % 25 == 1 and spent_s3() > S3_CAP - 0.10: raise RuntimeError('S3 cap')
    try:
        if phase in ('e1n', 'e1d', 'e2n', 'e2d', 'e3a', 'e3b') or phase[:2] == 'e4':
            it = BYID[t['cid']]
            if phase[:2] == 'e4':
                lang = phase[2:4]; perm = PERMS[phase[4]]; desc = DESC_E4; mem = E4_MEM
            else:
                lang = 'de'; perm = PERM_B if phase in ('e2n', 'e2d', 'e3b') else PERM_ID
                desc = phase in ('e1d', 'e2d') or (phase[:2] == 'e3' and DESC_E3); mem = phase[:2] == 'e3'
            x = it['lang'][lang]
            ex = [(n['title'], n['tags']) for n in x['nb'][:K]] if mem else None
            u, p = curia_prompt(dict(title=x['title'], text=x['text']), lang, perm, desc=desc, examples=ex)
            d, raw, rec, gen = m1(u, p, tag, CODES29)
            row = dict(t, lang=lang, desc=desc, mem=mem, perm=('id' if perm == PERM_ID else 'B'), rec=rec, codes=d,
                       p=label_probs(d, perm), mass=round(sum(math.exp(v) for v in d.values()), 5), gen=gen)
        elif phase in ('e1x1', 'e1x2'):
            # code-slot test: E1 names+desc identity order, last three codes = digits / lowercase instead of umlauts
            it = BYID[t['cid']]; x = it['lang']['de']; cs = CODES_DIG if phase == 'e1x1' else CODES_LOW
            u, p = curia_prompt(dict(title=x['title'], text=x['text']), 'de', PERM_ID, desc=True, codes=cs)
            d, raw, rec, gen = m1(u, p, tag, cs)
            row = dict(t, lang='de', rec=rec, codes=d, p=label_probs(d, PERM_ID, cs), gen=gen)
        elif phase in ('e1m', 'e3m'):
            # multi-label generative variant: ask for all applicable codes (1-4, most important first) as a JSON list
            it = BYID[t['cid']]; x = it['lang']['de']; perm = PERM_ID
            ex = [(n['title'], n['tags']) for n in x['nb'][:K]] if phase == 'e3m' else None
            u, _ = curia_prompt(dict(title=x['title'], text=x['text']), 'de', perm, desc=True, examples=ex)
            u = u.replace(TC['de']['ask'], "Ordne das folgende Geschäft der Schweizer Bundesversammlung allen zutreffenden Sachbereichen (Curia Vista) zu: einem bis vier, den wichtigsten zuerst.")
            u = u.replace(TC['de']['fmt'], "Antworte nur mit den Buchstaben der Sachbereiche als JSON-Liste: {\"sachbereiche\": [\"<Buchstabe>\", ...]}")
            pre = '{"sachbereiche": ["'
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], tag, max_tokens=24,
                                 continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
            gen = (ch.get('message') or {}).get('content') or ''
            body = gen.split(']')[0]
            codes = [c for c in re.findall(r'"?\s*([A-ZÄÖÜ])\s*"?', body)]
            labs = []
            for c in codes:
                lab = LABELS[perm[CODES29.index(c)]]
                if lab not in labs: labs.append(lab)
            d, raw = read_codes(ch, CODES29)
            row = dict(t, rec=rec, gen=gen, labels=labs, first=label_probs(d, perm), lang='de')
        elif phase in ('e5a', 'e5b'):
            A = {a['opd_affair_id']: a for a in json.load(open(f'{DATA}/aps.json'))}
            a = A[t['oid']]; perm = list(range(25)) if phase == 'e5a' else S1PERM
            u, p = s1lib.m1_prompt(a, 'de', perm)
            d, raw, rec, gen = m1(u, p, tag, s1lib.CODES)
            pv = [0.0] * 25
            for c, l in d.items(): pv[perm[s1lib.CODES.index(c)]] = math.exp(l)
            s = sum(pv) or 1; pv = [v / s for v in pv]
            row = dict(t, rec=rec, codes=d, p=pv, gen=gen)
        elif phase in ('e5t', 'e5p'):
            A = {a['opd_affair_id']: a for a in json.load(open(f'{DATA}/aps.json'))}
            a = A[t['oid']]
            u, p, n = s1lib.l2_prompt(a, 'de', t['ch'])
            d, raw, rec, gen = m1(u, p, tag, s1lib.CODES[:n])
            top = s1lib.CODES.index(max(d, key=d.get)) if d else None
            row = dict(t, rec=rec, codes=d, top=top, top_name=s1lib.SUBS[t['ch']][top] if top is not None else None)
        elif phase in ('e6a', 'e6b'):
            D = json.load(open(f'{DATA}/dvs.json')); x = next(y for y in D[t['pos']] if y['opd_affair_id'] == t['oid'])
            lang = x['title_lang']; q, item, ti, tl, yes, no, fmt, key = E6[lang]
            opts = [("A", yes), ("B", no)] if phase == 'e6a' else [("A", no), ("B", yes)]
            blk = f"{ti}: {x['title'][:400]}" + (f"\n{tl}: {x['title_long'][:400]}" if x['title_long'] and x['title_long'] != x['title'] else '')
            u = f"{q}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\n{item}:\n{blk}\n\n{fmt}"
            d, raw, rec, gen = m1(u, '{"' + key + '": "', tag, ["A", "B"])
            pa, pb = math.exp(d.get('A', -50)), math.exp(d.get('B', -50))
            pyes = (pa if phase == 'e6a' else pb) / (pa + pb)
            row = dict(t, rec=rec, codes=d, p_yes=pyes, lang=lang)
        elif phase == 'e6f':
            it = BYID[t['cid']]; x = it['lang']['de']
            blk = item_block(dict(title=x['title'], text=x['text']), 'de')
            if t['arm'] == 'free':
                u = FREE['free'].format(blk=blk); pre = '{"thema": "'
            else:
                u = FREE['list'].format(blk=blk, lst="\n".join(f"- {lname(l, 'de')}" for l in LABELS)); pre = '{"sachbereich": "'
            ch, meta, rec = call([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], tag, max_tokens=24,
                                 continue_final_message=True, add_generation_prompt=False)
            gen = (ch.get('message') or {}).get('content') or ''
            row = dict(t, rec=rec, gen=gen, answer=gen.split('"')[0].strip(), gold=it['gold'])
        s1lib.log(f'{RAW}/{phase}.jsonl', row)
        return t['key'], 'ok'
    except Exception as e:
        s1lib.log(f'{RAW}/errors.jsonl', dict(t, err=repr(e)[:500]))
        return t['key'], repr(e)[:200]

def done(phase):
    p = f'{RAW}/{phase}.jsonl'
    return {json.loads(l)['key'] for l in open(p)} if os.path.exists(p) else set()

if __name__ == '__main__':
    phase = sys.argv[1]; workers = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    assert workers <= 8
    ts = [t for t in tasks(phase) if t['key'] not in done(phase)]
    if len(sys.argv) > 3: ts = ts[:int(sys.argv[3])]
    print(phase, 'todo', len(ts), flush=True)
    with Pool(workers) as pool:
        for i, (k, st) in enumerate(pool.imap_unordered(run, ts)):
            if st != 'ok' or i % 50 == 0: print(i, k, st, flush=True)
    print('spent bern-s3-*:', round(spent_s3(), 4), flush=True)
