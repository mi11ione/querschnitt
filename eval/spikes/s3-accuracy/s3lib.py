"""S3 shared code: Curia 28 Sachbereiche (de/fr/it) + descriptions, prompt builders (S1 M1 shape), readers, metrics.
Gateway access reuses S1's instrumented `call` (gw.chat, full=True, no system message, model -8b only)."""
import json, os, sys, math, random, re, html, collections
sys.path.append('/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s1-runtime')
import s1lib  # noqa: E402  (patches urllib.urlopen for HTTP status observation; gw.py untouched)
from s1lib import call as _call, wilson, gw, MODEL  # noqa: E402,F401

OUT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(OUT, 'data'); RAW = os.path.join(OUT, 'raw')
D2 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data'
S3_CAP = 3.00

def spent_s3():
    return sum(v for k, v in gw.spent_summary().items() if k.startswith('bern-s3-'))

def call(messages, tag, **kw):
    assert tag.startswith('bern-s3-')
    assert not any(m['role'] == 'system' for m in messages)
    return _call(messages, tag, **kw)

# ------------------------------------------------------------------ Curia 28 (+ none)
TN = json.load(open(f'{D2}/curia_tagnames.json'))['tagname']
TAGS = sorted(int(k) for k in TN['de'])            # 28 Curia tag ids
NONE_ID = 0
LABELS = TAGS + [NONE_ID]                           # 29 labels; index 28 = none/procedural
NL = len(LABELS)
CODES29 = [chr(ord('A') + i) for i in range(26)] + ['Ä', 'Ö', 'Ü']   # all single tokens (probe_tok.py)
CODES_DIG = [chr(ord('A') + i) for i in range(26)] + ['1', '2', '3']   # code-slot test (e1x1)
CODES_LOW = [chr(ord('A') + i) for i in range(26)] + ['a', 'b', 'c']   # code-slot test (e1x2)
NONE_NAME = {"de": "Kein Sachthema (Wahl oder Ernennung von Personen, Verfahrensfragen des Rats)",
             "fr": "Aucun thème (élection ou nomination de personnes, procédure du conseil)",
             "it": "Nessun tema (elezione o nomina di persone, procedura del consiglio)"}
def lname(t, lang):
    return NONE_NAME[lang] if t == NONE_ID else TN[lang][str(t)]

# Descriptions: Parlamentsbibliothek sub-topics (BFH topics_hierarchy.json; finanzplatz merged into Finanzwesen,
# tierwelt into Umwelt, geschichte dropped). FR/IT = our translation of the same terms.
DESC = {"de": {
 4: "Exekutive, öffentliche Verwaltung, politische Rechte, Demokratie, Föderalismus, Parteien, Bürgerrecht, Verfassung, Volksabstimmung, Wahlen, Vergaberecht, Auslandschweizer, Service public",
 421: "Parlament der Schweiz, Ratsmitglieder, Parlamentsbetrieb, kantonale Parlamente",
 8: "Aussenpolitik, Diplomatie, internationale Beziehungen und Abkommen, Globalisierung, Grenze, internationale Organisationen und Zusammenarbeit",
 9: "Armee, Bewaffnung, innere Sicherheit, Zivilschutz, Bevölkerungsschutz, Zivildienst, Terrorismus, Friedenspolitik, Krieg, internationale Konflikte",
 10: "Beziehungen Schweiz–EU, Europarecht, Europäische Union, Europarat",
 12: "Verfahrensrecht, Urheberrecht, Verwaltungsrecht, Beschwerderecht",
 1211: "Zivilprozess, Familienrecht, Kinderrechte, Kindes- und Erwachsenenschutz, Personenrecht, Erbrecht, Sachenrecht, Obligationenrecht, Konkursrecht, Verträge",
 1216: "Strafrecht, Strafprozessordnung, Straftaten, Korruption",
 1221: "Gerichte, Justiz, Schiedsgerichtsbarkeit",
 1236: "Grundrechte, Datenschutz, Rassismus, Diskriminierung",
 1231: "Humanitäres Völkerrecht, internationale Strafjustiz, internationales Privatrecht, Staatssouveränität, internationale Rechtshilfe, Menschenrechte international",
 15: "Wirtschaftspolitik, Konsum, Tourismus, Unternehmen, Wettbewerb, Aussenwirtschaft, Handel, Privatversicherung, Produktion, Stiftungen",
 24: "Öffentliche Finanzen und Haushalt, Finanzausgleich, Zoll, Finanzmarkt, Finanzplatz, Geldwäscherei, Nationalbank, Geld- und Währungspolitik, Finanzrecht",
 2446: "Steuern, Abgaben, Steuerwettbewerb, Steuerhinterziehung",
 28: "Geschlechterfragen, Sport, Familie, Kinder und Jugend, Armut und Ungleichheit, Alter, Gesellschaft, Gewalt, Behinderung, Geldspiel",
 2811: "Asylpolitik, Flüchtlinge, Ausländerpolitik, Sans-Papiers, Migration",
 2831: "Kultur, Sprache, Religion",
 2836: "Sozialversicherungen, AHV, IV, berufliche Vorsorge, Unfall-, Arbeitslosen- und Mutterschaftsversicherung, Erwerbsersatz, Familienzulagen, Sozialhilfe, Sozialpolitik",
 2841: "Gesundheitspolitik, Krankenversicherung, Patienten, Pflege, Spitäler, Medizinalberufe, Sucht, Sterben und Tod, Heilmittel, Ernährung, Fortpflanzung",
 2846: "Miet- und Wohnungswesen, Raumplanung, Bauwesen und Immobilien",
 32: "Schule, Universitäten, Hochschulen, Fachhochschulen, Berufsbildung, Weiterbildung",
 34: "Presse, Radio und Fernsehen, Internet und soziale Medien, Telefonie, Post, Informatik, Information, Digitalisierung",
 36: "Forschung, Gentechnologie",
 44: "Arbeitsmarkt, Gewerkschaften, Arbeitslosigkeit, Arbeit",
 48: "Strassenverkehr, Schienenverkehr, Luftfahrt, Schifffahrt, Güterverkehr, öffentlicher Verkehr, Verkehrspolitik",
 52: "Umweltpolitik, Artenvielfalt, Katastrophen, Klima, Abfall, Wasser, Luft, Lärm, Wald, Berggebiete, Boden, Tierschutz, Tierversuche, Jagd und Fischerei",
 55: "Agrarpolitik, Agrarproduktion",
 66: "Erneuerbare Energie, Kernenergie, fossile Energie, Elektrizität, Energiepolitik"},
 "fr": {
 4: "exécutif, administration publique, droits politiques, démocratie, fédéralisme, partis, droit de cité, constitution, votations populaires, élections, marchés publics, Suisses de l'étranger, service public",
 421: "Parlement suisse, parlementaires, fonctionnement du parlement, parlements cantonaux",
 8: "politique extérieure, diplomatie, relations et accords internationaux, mondialisation, frontière, organisations et coopération internationales",
 9: "armée, armement, sécurité intérieure, protection civile, protection de la population, service civil, terrorisme, politique de paix, guerre, conflits internationaux",
 10: "relations Suisse–UE, droit européen, Union européenne, Conseil de l'Europe",
 12: "droit de procédure, droit d'auteur, droit administratif, droit de recours",
 1211: "procédure civile, droit de la famille, droits de l'enfant, protection de l'enfant et de l'adulte, droit des personnes, successions, droits réels, droit des obligations, faillite, contrats",
 1216: "droit pénal, procédure pénale, infractions, corruption",
 1221: "tribunaux, justice, arbitrage",
 1236: "droits fondamentaux, protection des données, racisme, discrimination",
 1231: "droit international humanitaire, justice pénale internationale, droit international privé, souveraineté, entraide judiciaire internationale, droits de l'homme",
 15: "politique économique, consommation, tourisme, entreprises, concurrence, économie extérieure, commerce, assurances privées, production, fondations",
 24: "finances publiques et budget, péréquation financière, douane, marché financier, place financière, blanchiment d'argent, Banque nationale, politique monétaire, droit financier",
 2446: "impôts, taxes, concurrence fiscale, fraude fiscale",
 28: "égalité des sexes, sport, famille, enfance et jeunesse, pauvreté et inégalités, personnes âgées, société, violence, handicap, jeux d'argent",
 2811: "politique d'asile, réfugiés, politique des étrangers, sans-papiers, migrations",
 2831: "culture, langues, religion",
 2836: "assurances sociales, AVS, AI, prévoyance professionnelle, assurance-accidents, assurance-chômage, assurance-maternité, allocations pour perte de gain, allocations familiales, aide sociale, politique sociale",
 2841: "politique de santé, assurance-maladie, patients, soins, hôpitaux, professions médicales, addictions, fin de vie, produits thérapeutiques, alimentation, procréation",
 2846: "bail et logement, aménagement du territoire, construction et immobilier",
 32: "école, universités, hautes écoles, hautes écoles spécialisées, formation professionnelle, formation continue",
 34: "presse, radio et télévision, internet et réseaux sociaux, téléphonie, poste, informatique, information, numérisation",
 36: "recherche, génie génétique",
 44: "marché du travail, syndicats, chômage, travail",
 48: "circulation routière, rail, aviation, navigation, transport de marchandises, transports publics, politique des transports",
 52: "politique environnementale, biodiversité, catastrophes, climat, déchets, eau, air, bruit, forêt, montagne, sol, protection des animaux, expérimentation animale, chasse et pêche",
 55: "politique agricole, production agricole",
 66: "énergies renouvelables, énergie nucléaire, énergies fossiles, électricité, politique énergétique"},
 "it": {
 4: "esecutivo, amministrazione pubblica, diritti politici, democrazia, federalismo, partiti, cittadinanza, costituzione, votazioni popolari, elezioni, appalti pubblici, Svizzeri all'estero, servizio pubblico",
 421: "Parlamento svizzero, parlamentari, funzionamento del parlamento, parlamenti cantonali",
 8: "politica estera, diplomazia, relazioni e accordi internazionali, globalizzazione, frontiera, organizzazioni e cooperazione internazionali",
 9: "esercito, armamenti, sicurezza interna, protezione civile, protezione della popolazione, servizio civile, terrorismo, politica di pace, guerra, conflitti internazionali",
 10: "relazioni Svizzera–UE, diritto europeo, Unione europea, Consiglio d'Europa",
 12: "diritto procedurale, diritto d'autore, diritto amministrativo, diritto di ricorso",
 1211: "procedura civile, diritto di famiglia, diritti del fanciullo, protezione dei minori e degli adulti, diritto delle persone, successioni, diritti reali, diritto delle obbligazioni, fallimento, contratti",
 1216: "diritto penale, procedura penale, reati, corruzione",
 1221: "tribunali, giustizia, arbitrato",
 1236: "diritti fondamentali, protezione dei dati, razzismo, discriminazione",
 1231: "diritto internazionale umanitario, giustizia penale internazionale, diritto internazionale privato, sovranità, assistenza giudiziaria internazionale, diritti umani",
 15: "politica economica, consumo, turismo, imprese, concorrenza, economia esterna, commercio, assicurazioni private, produzione, fondazioni",
 24: "finanze pubbliche e bilancio, perequazione finanziaria, dogana, mercato finanziario, piazza finanziaria, riciclaggio di denaro, Banca nazionale, politica monetaria, diritto finanziario",
 2446: "imposte, tasse, concorrenza fiscale, evasione fiscale",
 28: "parità dei sessi, sport, famiglia, infanzia e gioventù, povertà e disuguaglianza, anziani, società, violenza, disabilità, giochi in denaro",
 2811: "politica d'asilo, rifugiati, politica degli stranieri, sans-papiers, migrazioni",
 2831: "cultura, lingue, religione",
 2836: "assicurazioni sociali, AVS, AI, previdenza professionale, assicurazione infortuni, disoccupazione e maternità, indennità di perdita di guadagno, assegni familiari, aiuto sociale, politica sociale",
 2841: "politica sanitaria, assicurazione malattie, pazienti, cure, ospedali, professioni mediche, dipendenze, fine vita, agenti terapeutici, alimentazione, procreazione",
 2846: "locazione e alloggio, pianificazione del territorio, edilizia e immobili",
 32: "scuola, università, scuole universitarie, scuole universitarie professionali, formazione professionale, formazione continua",
 34: "stampa, radio e televisione, internet e social media, telefonia, posta, informatica, informazione, digitalizzazione",
 36: "ricerca, ingegneria genetica",
 44: "mercato del lavoro, sindacati, disoccupazione, lavoro",
 48: "traffico stradale, ferrovia, aviazione, navigazione, trasporto merci, trasporti pubblici, politica dei trasporti",
 52: "politica ambientale, biodiversità, catastrofi, clima, rifiuti, acqua, aria, rumore, bosco, montagna, suolo, protezione degli animali, sperimentazione animale, caccia e pesca",
 55: "politica agricola, produzione agricola",
 66: "energie rinnovabili, energia nucleare, energie fossili, elettricità, politica energetica"}}
assert all(set(DESC[l]) == set(TAGS) for l in DESC)

TC = {
 "de": dict(key="sachbereich", ask="Ordne das folgende Geschäft der Schweizer Bundesversammlung dem passendsten Sachbereich (Curia Vista) zu.",
            themes="Sachbereiche", item="Geschäft", title="Titel", text="Text (Auszug)",
            fmt="Antworte nur mit dem Buchstaben des Sachbereichs als JSON: {\"sachbereich\": \"<Buchstabe>\"}",
            ex_head="Frühere Geschäfte mit ihren Sachbereichen (zur Orientierung):", ex_lab="Sachbereiche"),
 "fr": dict(key="domaine", ask="Attribue l'objet suivant de l'Assemblée fédérale suisse au domaine thématique (Curia Vista) le plus approprié.",
            themes="Domaines", item="Objet", title="Titre", text="Texte (extrait)",
            fmt="Réponds uniquement par la lettre du domaine en JSON : {\"domaine\": \"<lettre>\"}",
            ex_head="Objets antérieurs avec leurs domaines (pour orientation) :", ex_lab="Domaines"),
 "it": dict(key="settore", ask="Assegna il seguente oggetto dell'Assemblea federale svizzera al settore tematico (Curia Vista) più appropriato.",
            themes="Settori", item="Oggetto", title="Titolo", text="Testo (estratto)",
            fmt="Rispondi solo con la lettera del settore in JSON: {\"settore\": \"<lettera>\"}",
            ex_head="Oggetti precedenti con i loro settori (come orientamento):", ex_lab="Settori"),
}

def item_block(a, lang, text_chars=1500):
    t = TC[lang]; lines = [f"{t['title']}: {a['title']}"]
    if a.get('text'): lines.append(f"{t['text']}: {a['text'][:text_chars]}")
    return "\n".join(lines)

def curia_prompt(a, lang, perm, desc=False, examples=None, codes=None):
    """perm[i] = label index (into LABELS) listed under CODES29[i]. examples: list of (title, [tag ids])."""
    CODES29 = codes or globals()['CODES29']
    t = TC[lang]; inv = {perm[i]: i for i in range(NL)}
    def nm(li):
        lab = LABELS[li]; s = lname(lab, lang)
        if desc and lab != NONE_ID: s += f" ({DESC[lang][lab]})"
        return s
    themes = "\n".join(f"{CODES29[i]} = {nm(perm[i])}" for i in range(NL))
    parts = [t['ask'], f"{t['themes']}:\n{themes}"]
    if examples:
        ex = []
        for k, (ti, tags) in enumerate(examples):
            codes = ", ".join(f"{CODES29[inv[LABELS.index(g)]]} ({lname(g, lang)})" for g in tags)
            ex.append(f"- {ti}\n  → {t['ex_lab']}: {codes}")
        parts.append(t['ex_head'] + "\n" + "\n".join(ex))
    parts += [f"{t['item']}:\n{item_block(a, lang)}", t['fmt']]
    return "\n\n".join(parts), '{"' + t['key'] + '": "'

PERM_ID = list(range(NL))
PERM_B = list(range(NL)); random.Random(31).shuffle(PERM_B)
PERM_REV = list(reversed(range(NL)))

def read_codes(choice, codes):
    lp = (choice.get('logprobs') or {}).get('content') or []
    if not lp: return {}, []
    raw = [(t['token'], t['logprob']) for t in lp[0]['top_logprobs']]
    out = {}
    for tok, l in raw:
        s = tok.strip().strip('"').strip()
        if s in codes: out[s] = max(out.get(s, -1e9), l)
    return out, raw

def m1(messages_user, prefill, tag, codes):
    ch, meta, rec = call([{"role": "user", "content": messages_user}, {"role": "assistant", "content": prefill}], tag,
                         max_tokens=1, continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
    d, raw = read_codes(ch, codes)
    return d, raw, rec, (ch.get('message') or {}).get('content')

def label_probs(codes_lp, perm, codes=None):
    """code->logprob (top-20, censored codes = 0) -> normalised prob vector over LABELS (index space)."""
    p = [0.0] * NL
    for c, l in codes_lp.items():
        p[perm[(codes or CODES29).index(c)]] = math.exp(l)
    s = sum(p) or 1.0
    return [x / s for x in p]

# ------------------------------------------------------------------ text utils
def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return " ".join(html.unescape(s).split())

SW = {"de": ("der", "die", "und", "das", "nicht", "ist", "zu", "den", "mit"),
      "fr": ("le", "la", "les", "et", "des", "est", "du", "une", "pour"),
      "it": ("il", "che", "di", "della", "per", "una", "sono", "gli", "non")}
def guess_lang(text):
    w = re.findall(r"\w+", (text or "").lower())
    sc = {l: sum(x in v for x in w) for l, v in SW.items()}
    return max(sc, key=sc.get) if max(sc.values()) > 0 else None

# ------------------------------------------------------------------ metrics
def prf(pairs, labels=TAGS):
    tp = collections.Counter(); fp = collections.Counter(); fn = collections.Counter()
    for gold, pred in pairs:
        for t in pred: (tp if t in gold else fp)[t] += 1
        for t in gold:
            if t not in pred: fn[t] += 1
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    micro = 2 * TP / (2 * TP + FP + FN) if TP else 0.0
    per = [2 * tp[t] / (2 * tp[t] + fp[t] + fn[t]) if tp[t] else 0.0 for t in labels if tp[t] + fn[t] > 0]
    return dict(micro=micro, macro=sum(per) / len(per) if per else 0.0, P=TP / (TP + FP) if TP + FP else 0.0,
                R=TP / (TP + FN) if TP + FN else 0.0)

def boot(pairs, key='micro', n=1000, seed=1):
    rng = random.Random(seed); m = len(pairs); vals = []
    for _ in range(n):
        vals.append(prf([pairs[rng.randrange(m)] for _ in range(m)])[key])
    vals.sort(); return (round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n) - 1], 3))

def paired_boot(pairs_a, pairs_b, key='micro', n=1000, seed=2):
    rng = random.Random(seed); m = len(pairs_a); d = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]
        d.append(prf([pairs_a[i] for i in idx])[key] - prf([pairs_b[i] for i in idx])[key])
    d.sort(); return (round(d[int(0.025 * n)], 3), round(d[int(0.975 * n) - 1], 3))
