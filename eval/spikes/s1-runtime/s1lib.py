"""S1 shared code: APS scheme (de/fr/it), prompt builders, instrumented gateway call, log-prob readers.
All Public AI traffic goes through gw.chat (budget gateway). We only *observe* urllib.request.urlopen to time the HTTP
round trip and count HTTP status codes (429 etc.); gw.py itself is untouched."""
import json, os, sys, time, threading, math, urllib.request, urllib.error
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/gateway')
import gw  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
MODEL = 'swiss-ai/apertus-v1.5-8b'
TOTAL_CAP = 3.00

# ------------------------------------------------------------------ instrumentation (observe only)
_tl = threading.local()
_orig_urlopen = urllib.request.urlopen
def _urlopen(req, *a, **k):
    rec = getattr(_tl, 'attempts', None)
    t0 = time.time()
    try:
        r = _orig_urlopen(req, *a, **k)
        if rec is not None: rec.append(dict(t0=t0, t1=time.time(), status=getattr(r, 'status', 200)))
        return r
    except urllib.error.HTTPError as e:
        if rec is not None: rec.append(dict(t0=t0, t1=time.time(), status=e.code))
        raise
    except Exception as e:
        if rec is not None: rec.append(dict(t0=t0, t1=time.time(), status=type(e).__name__))
        raise
urllib.request.urlopen = _urlopen

_lock = threading.Lock()
def log(path, row):
    with _lock:
        with open(path, 'a') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')

def spent_s1():
    return sum(v for k, v in gw.spent_summary().items() if k.startswith('bern-s1-'))

def call(messages, tag, max_tokens=1, **extra):
    """One gateway call with receipts. Returns (choice, rec)."""
    assert not any(m['role'] == 'system' for m in messages)
    for attempt in range(6):
        _tl.attempts = []
        t0 = time.time()
        try:
            choice, meta = gw.chat(messages, model=MODEL, max_tokens=max_tokens, temperature=0.0, tag=tag,
                                   tag_cap_usd=1.2, full=True, **extra)
            break
        except Exception as e:
            if 'BUDGET' in str(e) or attempt == 5: raise
            time.sleep(10 * (attempt + 1))
    wall = time.time() - t0
    resp = meta.get('resp') or {}
    att = _tl.attempts
    http = sum(a['t1'] - a['t0'] for a in att)
    rec = dict(tag=tag, cached=meta.get('cached'), model=resp.get('model'), fp=resp.get('system_fingerprint'),
               pt=meta['prompt_tokens'], ct=meta['completion_tokens'], usd=meta['usd'], gw_secs=meta.get('secs'),
               wall=round(wall, 3), http=round(http, 3), http_last=round(att[-1]['t1'] - att[-1]['t0'], 3) if att else None,
               statuses=[a['status'] for a in att], t_start=round(t0, 3), t_http0=round(att[0]['t0'], 3) if att else None,
               t_http1=round(att[-1]['t1'], 3) if att else None)
    if rec['model'] and rec['model'] != MODEL:
        rec['model_mismatch'] = True
    return choice, meta, rec

# ------------------------------------------------------------------ APS scheme
CH_DE = ["Politische Grundfragen", "Rechtsordnung", "Institutionen und Volksrechte", "Föderativer Aufbau", "Wahlen",
         "Aussenpolitik", "Landesverteidigung", "Wirtschaftspolitik", "Geld, Währung und Kredit", "Landwirtschaft",
         "Öffentliche Finanzen", "Energie", "Verkehr und Kommunikation", "Raumplanung und Wohnungswesen", "Umweltschutz",
         "Bevölkerung und Arbeit", "Gesundheit, Sozialhilfe, Sport", "Sozialversicherungen", "Soziale Gruppen",
         "Bildung und Forschung", "Kultur, Sprache, Kirchen", "Medien", "Parteien", "Verbände"]
CH_FR = ["Problèmes politiques fondamentaux", "Ordre juridique", "Institutions et droits populaires", "Structures fédéralistes",
         "Elections", "Politique étrangère", "Armée", "Politique économique", "Crédit et monnaie", "Agriculture",
         "Finances publiques", "Energie", "Transports et communications", "Aménagement du territoire et logement",
         "Protection de l'environnement", "Population et travail", "Santé, assistance sociale, sport", "Assurances sociales",
         "Groupes sociaux", "Enseignement et recherche", "Culture, langues, églises", "Médias", "Partis", "Associations"]
# IT: APS has no Italian names; our translation (stated in results.md)
CH_IT = ["Questioni politiche fondamentali", "Ordinamento giuridico", "Istituzioni e diritti popolari", "Struttura federalista",
         "Elezioni", "Politica estera", "Difesa nazionale", "Politica economica", "Moneta, valuta e credito", "Agricoltura",
         "Finanze pubbliche", "Energia", "Trasporti e comunicazioni", "Pianificazione del territorio e alloggio",
         "Protezione dell'ambiente", "Popolazione e lavoro", "Sanità, assistenza sociale, sport", "Assicurazioni sociali",
         "Gruppi sociali", "Istruzione e ricerca", "Cultura, lingue, chiese", "Media", "Partiti", "Associazioni"]
NONE = {"de": "Kein Sachthema (Wahl oder Ernennung von Personen, Einbürgerung, Rücktritt, Verfahrensfragen des Rats)",
        "fr": "Aucun thème politique (élection ou nomination de personnes, naturalisation, démission, procédure du conseil)",
        "it": "Nessun tema politico (elezione o nomina di persone, naturalizzazione, dimissioni, procedura del consiglio)"}
CHAPTERS = {"de": CH_DE + [NONE["de"]], "fr": CH_FR + [NONE["fr"]], "it": CH_IT + [NONE["it"]]}
NCH = 25  # index 24 = no policy topic
CODES = [chr(ord('A') + i) for i in range(NCH)]  # A..Y

SUB_DE = {
 0: "Verfassungsfragen; Nationale Identität; Landes- und Weltausstellungen; Staatsjubiläen; Image der Schweiz im Ausland; Stimmung in der Bevölkerung",
 1: "Bürgerrecht; Niederlassungsrecht; Stimm- und Wahlrecht; Datenschutz und Statistik; Grundrechte; Öffentliche Ordnung; Innere Sicherheit; Kriminalität; Polizei; Äussere Sicherheit; Rechtshilfe; Strafrecht; Privatrecht",
 2: "Bundesrat; Regierungspolitik; Bundesverwaltung - Organisation; Bundesverwaltung - Personal; Parlamentsmandat; Parlamentsorganisation; Organisation der Bundesrechtspflege; Volksrechte; Wahl- und Abstimmungsverfahren",
 3: "Beziehungen zwischen Bund und Kantonen; Interkantonale Zusammenarbeit; Städte, Regionen, Gemeinden; Territorialfragen; Jurafrage",
 4: "Wahlen in kantonale Parlamente; Wahlen in kantonale Regierungen; Kantonale Ersatzwahlen; Kommunale Wahlen; Kommunale Ersatzwahlen; Eidgenössische Wahlen; Ständeratsersatzwahlen",
 5: "Beziehungen zur EU; Beziehungen zu internationalen Organisationen; Zwischenstaatliche Beziehungen; Gute Dienste; Auslandschweizer; Entwicklungspolitik; Aussenwirtschaftspolitik",
 6: "Landesverteidigung und Gesellschaft; Militäreinsätze; Militärorganisation; Ausrüstung und Beschaffung; Zivildienst und Dienstverweigerung; Bevölkerungsschutz",
 7: "Konjunkturlage- und politik; Strukturpolitik; Wettbewerb; Gesellschaftsrecht; Wirtschaftsordnung",
 8: "Finanzmarkt; Geldpolitik; Makroprudenzielle Regulierung; Nationalbank; Internationale Finanzinstitutionen; Wettbewerbsfähigkeit; Banken; Börsen; Versicherungen; Kapitalmarkt",
 9: "Agrarpolitik; Internationale Landwirtschaftspolitik; Landwirt (Beruf); Landwirtschaft und Umweltschutz; Agrarprodukte; Tierische Produktion; Pflanzliche Produktion; Lebensmittel; Tierhaltung, -versuche und -schutz; Forstwirtschaft; Fischerei; Jagd",
 10: "Direkte Steuern; Indirekte Steuern; Finanz- und Ausgabenordnung; Finanzplan und Sanierungsmassnahmen; Staatsrechnung; Voranschlag; Finanzausgleich; Finanzhaushalt der Kantone und Gemeinden",
 11: "Energiepolitik; Netz und Vertrieb; Wasserkraft; Kernenergie; Alternativenergien; Erdöl und Erdgas",
 12: "Verkehrspolitik; Strassenverkehr; Eisenbahn; Agglomerationsverkehr, öffentlicher Verkehr; Schiffahrt; Luftfahrt; Post und Telekommunikation",
 13: "Mietwesen; Raumplanung; Bodenrecht; Wohnungsbau und -eigentum; Wohnqualität",
 14: "Naturschutz; Naturgefahren; Gewässerschutz; Luftreinhaltung; Lärmschutz; Bodenschutz; Allgemeiner Umweltschutz; Klimapolitik; Abfälle",
 15: "Bevölkerungsentwicklung; Arbeitsmarkt; Löhne; Arbeitszeit; Kollektive Arbeitsbeziehungen; Arbeitnehmerschutz; Arbeitsrecht",
 16: "Gesundheitspolitik; Ärzte und Pflegepersonal; Medikamente; Epidemien; Medizinische Forschung; Suchtmittel; Sozialhilfe; Sport",
 17: "Alters- und Hinterlassenenversicherung (AHV); Invalidenversicherung (IV); Ergänzungsleistungen (EL); Erwerbsersatzordnung (EO); Berufliche Vorsorge; Private Vorsorge; Krankenversicherung; Unfallversicherung; Arbeitslosenversicherung (ALV)",
 18: "Migrationspolitik; Asylpolitik; Familienpolitik; Frauen und Gleichstellungspolitik; Kinder- und Jugendpolitik; Alterspolitik; Menschen mit Behinderungen; LGBTQIA+",
 19: "Grundschulen; Mittelschulen; Berufsbildung; Hochschulen; Forschung",
 20: "Kulturpolitik; Urheberrecht; Heimatschutz und Denkmalpflege; Archive, Bibliotheken, Museen; Buchmarkt; Musik; Film; Sprachen; Fahrende; Kirchen und religionspolitische Fragen",
 21: "Radio und Fernsehen; Presse; Medienpolitische Grundfragen; Telekommunikation; Neue Medien; Meinungsforschung",
 22: "Parteiensystem; Grosse Parteien; Linke und ökologische Parteien; Liberale Parteien; Konservative und Rechte Parteien; Andere Parteien",
 23: "Industrie, Handel und Unternehmer; Arbeitgeber; Landwirtschaft; Gewerbe, Dienstleistungen, Konsum; Arbeitnehmer, Gewerkschaften; Gesundheit; Sozialwesen, Soziale Gruppen; Raumplanung und Wohnungswesen; Verkehr; Energie; Natur und Umwelt; Bildung; Kultur, Medien und Sprachen; Kirche, Religion; Freizeit, Tourismus, Gastgewerbe; Überparteiliche politische Interessen / Think Tanks",
}
SUBS = {k: [x.strip() for x in v.split(';')] for k, v in SUB_DE.items()}
assert sum(len(v) for v in SUBS.values()) == 190, sum(len(v) for v in SUBS.values())

T = {
 "de": dict(key="kapitel", subkey="unterthema",
            ask="Ordne das folgende parlamentarische Geschäft genau einem Thema der Année Politique Suisse zu.",
            themes="Themen", item="Geschäft", title="Titel", tlong="Langtitel", text="Text (Auszug)",
            fmt_code="Antworte nur mit dem Buchstaben des Themas als JSON: {\"kapitel\": \"<Buchstabe>\"}",
            fmt_name="Antworte nur mit dem Namen des Themas als JSON: {\"kapitel\": \"<Thema>\"}",
            batch_ask="Ordne jedes der folgenden parlamentarischen Geschäfte genau einem Thema der Année Politique Suisse zu.",
            batch_fmt="Antworte mit einer Zeile pro Geschäft im Format <Nummer>: <Buchstabe>, ohne weiteren Text.",
            sub_ask="Das folgende parlamentarische Geschäft gehört zum Thema «{ch}». Ordne es genau einem Unterthema zu.",
            subs="Unterthemen", fmt_sub="Antworte nur mit dem Buchstaben des Unterthemas als JSON: {\"unterthema\": \"<Buchstabe>\"}"),
 "fr": dict(key="chapitre", subkey="sous_theme",
            ask="Attribue l'objet parlementaire suivant à exactement un thème de l'Année politique suisse.",
            themes="Thèmes", item="Objet", title="Titre", tlong="Titre long", text="Texte (extrait)",
            fmt_code="Réponds uniquement par la lettre du thème en JSON : {\"chapitre\": \"<lettre>\"}",
            fmt_name="Réponds uniquement par le nom du thème en JSON : {\"chapitre\": \"<thème>\"}",
            batch_ask="Attribue chacun des objets parlementaires suivants à exactement un thème de l'Année politique suisse.",
            batch_fmt="Réponds par une ligne par objet au format <numéro>: <lettre>, sans autre texte.",
            sub_ask="L'objet parlementaire suivant relève du thème « {ch} ». Attribue-le à exactement un sous-thème.",
            subs="Sous-thèmes", fmt_sub="Réponds uniquement par la lettre du sous-thème en JSON : {\"sous_theme\": \"<lettre>\"}"),
 "it": dict(key="capitolo", subkey="sottotema",
            ask="Assegna il seguente oggetto parlamentare a esattamente un tema dell'Année Politique Suisse.",
            themes="Temi", item="Oggetto", title="Titolo", tlong="Titolo lungo", text="Testo (estratto)",
            fmt_code="Rispondi solo con la lettera del tema in JSON: {\"capitolo\": \"<lettera>\"}",
            fmt_name="Rispondi solo con il nome del tema in JSON: {\"capitolo\": \"<tema>\"}",
            batch_ask="Assegna ciascuno dei seguenti oggetti parlamentari a esattamente un tema dell'Année Politique Suisse.",
            batch_fmt="Rispondi con una riga per oggetto nel formato <numero>: <lettera>, senza altro testo.",
            sub_ask="Il seguente oggetto parlamentare rientra nel tema «{ch}». Assegnalo a esattamente un sottotema.",
            subs="Sottotemi", fmt_sub="Rispondi solo con la lettera del sottotema in JSON: {\"sottotema\": \"<lettera>\"}"),
}

def affair_block(a, lang, text_chars=1500):
    t = T[lang]
    lines = [f"{t['title']}: {a['title']}"]
    if a.get('title_long') and a['title_long'] != a['title']:
        lines.append(f"{t['tlong']}: {a['title_long'][:400]}")
    if a.get('text'):
        lines.append(f"{t['text']}: {a['text'][:text_chars]}")
    return "\n".join(lines)

def perm_identity():
    return list(range(NCH))

def m1_prompt(a, lang, perm=None):
    """perm[i] = chapter index listed under code CODES[i]."""
    perm = perm or perm_identity(); t = T[lang]; names = CHAPTERS[lang]
    themes = "\n".join(f"{CODES[i]} = {names[perm[i]]}" for i in range(NCH))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{affair_block(a, lang)}\n\n{t['fmt_code']}"
    prefill = '{"' + t['key'] + '": "'
    return user, prefill

def m2_prompt(a, lang):
    t = T[lang]; names = CHAPTERS[lang]
    themes = "\n".join(f"- {n}" for n in names)
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{affair_block(a, lang)}\n\n{t['fmt_name']}"
    return user, '{"' + t['key'] + '": "'

def l2_prompt(a, lang, ch):
    t = T[lang]; subs = SUBS[ch]
    lst = "\n".join(f"{CODES[i]} = {s}" for i, s in enumerate(subs))
    user = f"{t['sub_ask'].format(ch=CHAPTERS[lang][ch])}\n\n{t['subs']}:\n{lst}\n\n{t['item']}:\n{affair_block(a, lang)}\n\n{t['fmt_sub']}"
    return user, '{"' + t['subkey'] + '": "', len(subs)

def m3_prompt(items, lang):
    t = T[lang]; names = CHAPTERS[lang]
    themes = "\n".join(f"{CODES[i]} = {names[i]}" for i in range(NCH))
    blocks = "\n\n".join(f"{t['item']} {k + 1}:\n{affair_block(a, lang)}" for k, a in enumerate(items))
    user = f"{t['batch_ask']}\n\n{t['themes']}:\n{themes}\n\n{blocks}\n\n{t['batch_fmt']}"
    return user, "1: "

# ------------------------------------------------------------------ readers
def code_dist(choice, ncodes):
    """Map top_logprobs of the first generated token to code -> logprob. Token may carry a trailing quote/space."""
    lp = (choice.get('logprobs') or {}).get('content') or []
    if not lp: return None, None
    top = lp[0]['top_logprobs']
    out = {}
    raw = [(t['token'], t['logprob']) for t in top]
    for tok, l in raw:
        s = tok.strip().strip('"').strip()
        if len(s) == 1 and s in CODES[:ncodes]:
            out[s] = max(out.get(s, -1e9), l)
    return out, raw

def tail_logprob(prompt_logprobs, cont):
    """Sum logprobs of the trailing prompt tokens that cover `cont` (the actual tokens). If the first covering token
    straddles the boundary (prefix chars + label chars merged), it is included and flagged."""
    acc, lp, toks = "", 0.0, []
    for e in reversed(prompt_logprobs):
        if e is None: break
        vals = list(e.values())
        act = vals[0] if len(vals) == 1 else next((v for v in vals if v.get('rank') != 1), vals[0])
        acc = act['decoded_token'] + acc; lp += act['logprob']; toks.insert(0, act['decoded_token'])
        if len(acc) >= len(cont):
            if not acc.endswith(cont):
                raise ValueError(f'tail mismatch {acc[-len(cont)-5:]!r} vs {cont!r}')
            return lp, toks, len(acc) > len(cont)
    raise ValueError('ran out of tokens')

def wilson(k, n, z=1.96):
    if n == 0: return (float('nan'), float('nan'))
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))
