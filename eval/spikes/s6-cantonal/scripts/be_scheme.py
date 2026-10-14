"""S6 A2 scheme: the 8 Bern cantonal directorates (structure since 2020) with a one-line public remit each, DE + FR.
Remits WRITTEN BY THE AGENT from general knowledge of the Bern cantonal administration (not an official text).
Keyword stems per directorate written BEFORE any A2 model output or sample label was looked at (frozen 13 Oct 2026)."""

DIRS = ['BKD', 'BVD', 'DIJ', 'FIN', 'GSI', 'SID', 'STA', 'WEU']   # display order A..H (alphabetical, DE abbreviations); I = none
FR_ABBR = {'BKD': 'INC', 'BVD': 'DTT', 'DIJ': 'DIJ', 'FIN': 'FIN', 'GSI': 'DSSI', 'SID': 'DSE', 'STA': 'CHA', 'WEU': 'DEEE'}

NAME = {
 'de': {'BKD': 'Bildungs- und Kulturdirektion', 'BVD': 'Bau- und Verkehrsdirektion', 'DIJ': 'Direktion für Inneres und Justiz',
        'FIN': 'Finanzdirektion', 'GSI': 'Gesundheits-, Sozial- und Integrationsdirektion', 'SID': 'Sicherheitsdirektion',
        'STA': 'Staatskanzlei', 'WEU': 'Wirtschafts-, Energie- und Umweltdirektion'},
 'fr': {'BKD': "Direction de l'instruction publique et de la culture", 'BVD': 'Direction des travaux publics et des transports',
        'DIJ': "Direction de l'intérieur et de la justice", 'FIN': 'Direction des finances',
        'GSI': "Direction de la santé, des affaires sociales et de l'intégration", 'SID': 'Direction de la sécurité',
        'STA': 'Chancellerie d\'Etat', 'WEU': "Direction de l'économie, de l'énergie et de l'environnement"},
}
REMIT = {
 'de': {'BKD': 'Volksschule, Mittelschulen, Berufsbildung, Hochschulen, Kultur und Denkmalpflege',
        'BVD': 'Strassen, öffentlicher Verkehr, Wasserbau, Wasser und Abfall, kantonale Gebäude und Grundstücke, Geoinformation',
        'DIJ': 'Gemeinden und Raumordnung, Kindes- und Erwachsenenschutz, Jugendamt, Sozialversicherungen, Kirchen, Grundbuch und Handelsregister, Regierungsstatthalterämter',
        'FIN': 'Kantonsfinanzen, Voranschlag und Finanzplan, Steuern, Finanzausgleich, Personal des Kantons, Informatik und Organisation',
        'GSI': 'Gesundheit und Spitäler, Sozialhilfe, Integration, Familie, Menschen mit Behinderungen, Alter, Betreuung von Asylsuchenden und Flüchtlingen',
        'SID': 'Polizei, Migration und Personenstand, Justizvollzug, Strassenverkehr und Schifffahrt (Fahrzeuge, Ausweise), Bevölkerungsschutz, Sport und Militär',
        'STA': 'Stabsstelle von Regierungsrat und Grossem Rat: Regierungsgeschäfte, Wahlen und Abstimmungen, Kommunikation, Zweisprachigkeit und Übersetzung, Aussenbeziehungen',
        'WEU': 'Wirtschaft und Arbeitsmarkt, Landwirtschaft und Natur, Wald und Naturgefahren, Energie, Umwelt und Klima'},
 'fr': {'BKD': "école obligatoire, écoles moyennes, formation professionnelle, hautes écoles, culture et monuments historiques",
        'BVD': "routes, transports publics, aménagement des eaux, eau et déchets, bâtiments et immeubles cantonaux, géoinformation",
        'DIJ': "communes et aménagement du territoire, protection de l'enfant et de l'adulte, office des mineurs, assurances sociales, Eglises, registre foncier et registre du commerce, préfectures",
        'FIN': "finances cantonales, budget et plan financier, impôts, péréquation financière, personnel cantonal, informatique et organisation",
        'GSI': "santé et hôpitaux, aide sociale, intégration, famille, personnes en situation de handicap, personnes âgées, prise en charge des requérants d'asile et des réfugiés",
        'SID': "police, migrations et état civil, exécution judiciaire, circulation routière et navigation (véhicules, permis), protection de la population, sport et affaires militaires",
        'STA': "état-major du Conseil-exécutif et du Grand Conseil : affaires gouvernementales, élections et votations, communication, bilinguisme et traduction, relations extérieures",
        'WEU': "économie et marché du travail, agriculture et nature, forêts et dangers naturels, énergie, environnement et climat"},
}
NONE = {'de': 'Keine dieser Direktionen (Geschäft des Grossen Rates selbst, z. B. Wahlen, Ratsorgane, Verfahren)',
        'fr': "Aucune de ces directions (affaire du Grand Conseil lui-même, p. ex. élections, organes du Conseil, procédure)"}
CODES = list('ABCDEFGHI')

T = {'de': dict(ask="Welche Direktion des Kantons Bern ist für das folgende Geschäft des Grossen Rates federführend?",
                head="Direktionen", item="Geschäft", title="Titel",
                fmt="Antworte nur mit dem Buchstaben der Direktion als JSON: {\"direktion\": \"<Buchstabe>\"}", key="direktion"),
     'fr': dict(ask="Quelle direction du canton de Berne est compétente pour l'objet suivant du Grand Conseil ?",
                head="Directions", item="Objet", title="Titre",
                fmt="Réponds uniquement par la lettre de la direction en JSON : {\"direction\": \"<lettre>\"}", key="direction")}


def prompt(title, lang):
    t = T[lang]
    lines = []
    for i, d in enumerate(DIRS):
        ab = d if lang == 'de' else FR_ABBR[d]
        lines.append(f"{CODES[i]} = {ab} {NAME[lang][d]}: {REMIT[lang][d]}")
    lines.append(f"{CODES[8]} = {NONE[lang]}")
    user = f"{t['ask']}\n\n{t['head']}:\n" + "\n".join(lines) + f"\n\n{t['item']}:\n{t['title']}: {title}\n\n{t['fmt']}"
    return user, '{"' + t['key'] + '": "'


# ---------------------------------------------------------------- keyword baseline (frozen before results)
KW = {
 'de': {'BKD': ['schul', 'lehr', 'bildung', 'gymnas', 'hochschul', 'universit', 'kultur', 'museum', 'denkmal', 'kindergart', 'lernend', 'theater'],
        'BVD': ['strass', 'verkehr', 'bahn', 'bus', 'tram', 'velo', 'brücke', 'tunnel', 'umfahrung', 'gebäude', 'hochbau', 'tiefbau', 'wasserbau', 'abfall', 'abwasser', 'neubau', 'umbau'],
        'DIJ': ['gemeinde', 'raumplan', 'ortsplan', 'zone', 'kindesschutz', 'kesb', 'jugend', 'kirche', 'grundbuch', 'statthalter', 'sozialversicher', 'ergänzungsleist', 'prämienverbill'],
        'FIN': ['steuer', 'finanz', 'budget', 'voranschlag', 'personal', 'lohn', 'löhne', 'informatik', 'schulden', 'ausgleich', 'pensionskasse'],
        'GSI': ['gesund', 'spital', 'kranken', 'pflege', 'ärzt', 'sozialhilf', 'integration', 'familie', 'behindert', 'alter', 'asyl', 'flüchtl', 'psychiatr', 'notfall', 'kita'],
        'SID': ['polizei', 'sicherheit', 'gewalt', 'kriminal', 'migration', 'ausländer', 'gefängnis', 'strafvollzug', 'justizvollzug', 'führerausweis', 'bevölkerungsschutz', 'zivilschutz', 'militär', 'sport', 'feuerwehr'],
        'STA': ['wahl', 'abstimmung', 'staatskanzlei', 'kommunikation', 'zweisprach', 'übersetz', 'berner jura', 'moutier', 'grossrat', 'regierungsrat', 'legislatur', 'richtlinien'],
        'WEU': ['wirtschaft', 'arbeitsmarkt', 'arbeitslos', 'landwirtschaft', 'bauern', 'wald', 'natur', 'energie', 'strom', 'solar', 'wind', 'klima', 'umwelt', 'jagd', 'fischerei', 'tourismus', 'wasserkraft']},
 'fr': {'BKD': ['écol', 'ensei', 'formation', 'gymnas', 'haute école', 'universit', 'cultur', 'musée', 'monument', 'apprenti', 'théâtre'],
        'BVD': ['route', 'trafic', 'transport', 'train', 'ferrov', 'bus', 'tram', 'vélo', 'pont', 'tunnel', 'contournement', 'bâtiment', 'assainissement', 'déchets', 'eaux usées', 'construction', 'transformation'],
        'DIJ': ['commune', 'aménagement', 'zone', "protection de l'enfant", 'apea', 'jeunesse', 'église', 'registre foncier', 'préfe', 'assurances sociales', 'prestations complémentaires', 'réduction des primes'],
        'FIN': ['impôt', 'fiscal', 'financ', 'budget', 'personnel', 'salaire', 'informatique', 'dette', 'péréquation', 'caisse de pension'],
        'GSI': ['santé', 'hôpital', 'malad', 'soins', 'médec', 'aide sociale', 'intégration', 'famille', 'handicap', 'âgées', 'asile', 'réfugi', 'psychiatr', 'urgence', 'crèche'],
        'SID': ['police', 'sécurité', 'violence', 'criminal', 'migration', 'étranger', 'prison', 'exécution des peines', 'permis de conduire', 'protection de la population', 'protection civile', 'militaire', 'sport', 'pompier'],
        'STA': ['élection', 'votation', 'chancellerie', 'communication', 'bilinguisme', 'traduction', 'jura bernois', 'moutier', 'grand conseil', 'conseil-exécutif', 'législature', 'programme gouvernemental'],
        'WEU': ['économi', 'marché du travail', 'chômage', 'agricult', 'paysan', 'forêt', 'nature', 'énergie', 'électricité', 'solaire', 'éolien', 'climat', 'environnement', 'chasse', 'pêche', 'tourisme', 'hydraul']},
}


def keyword_pred(title, lang, prior):
    """Most stem hits; ties -> more frequent directorate in the eligible pool (prior order); no hit -> prior[0]."""
    low = (title or '').lower()
    sc = {d: sum(k in low for k in KW[lang][d]) for d in DIRS}
    best = max(sc.values())
    if best == 0: return prior[0], 0
    return next(d for d in prior if sc[d] == best), best
