// Small helpers: DOM, numbers (never rounded up), dates and weeks, the two UI languages.
export const $ = (s, r = document) => r.querySelector(s);
export const $$ = (s, r = document) => [...r.querySelectorAll(s)];
export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
export const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export const SVGNS = 'http://www.w3.org/2000/svg';
export function s(tag, attrs = {}) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
  return e;
}

// ---- language
export const UI = { lang: 'de' };
const NF = { de: new Intl.NumberFormat('de-CH'), fr: new Intl.NumberFormat('fr-CH') };
export const num = n => (n == null || Number.isNaN(n)) ? '–' : NF[UI.lang].format(n);
// shares: truncated, never rounded up
export function pct(x, d = 1) {
  if (x == null || Number.isNaN(x)) return '–';
  const f = 10 ** d, v = Math.floor(x * 100 * f + 1e-9) / f;
  return v.toLocaleString(UI.lang === 'fr' ? 'fr-CH' : 'de-CH', { minimumFractionDigits: d, maximumFractionDigits: d }) + ' %';
}
export function p3(x) { // probabilities: truncated to 3 decimals
  if (x == null || Number.isNaN(x)) return '–';
  const v = Math.floor(x * 1000 + 1e-9) / 1000;
  return v.toFixed(3);
}

// ---- dates: day numbers and Monday-based weeks
export const dayNum = iso => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / 864e5;
export const isoOfDay = d => new Date(d * 864e5).toISOString().slice(0, 10);
export const mondayOf = d => d - ((new Date(d * 864e5).getUTCDay() + 6) % 7);
export function isoWeek(d) {
  const dt = new Date(d * 864e5), day = (dt.getUTCDay() + 6) % 7;
  dt.setUTCDate(dt.getUTCDate() - day + 3);
  const y = dt.getUTCFullYear(), jan4 = new Date(Date.UTC(y, 0, 4));
  return [y, 1 + Math.round(((dt - jan4) / 864e5 - 3 + ((jan4.getUTCDay() + 6) % 7)) / 7)];
}
export function fmtDate(iso) {
  if (!iso) return '–';
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(2, 4)}`;
}
export const MONTHS = {
  de: ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'],
  fr: ['janv', 'févr', 'mars', 'avr', 'mai', 'juin', 'juil', 'août', 'sept', 'oct', 'nov', 'déc'],
};

export const T = {
  de: {
    anb: 'Anbindung', anbTable: 'Tabelle topics in OpenParlData', anbCols: 'Spalten', anbMachine: 'Maschine (inferred)', anbDecision: 'Entscheid (confirmed)', anbHop: 'Laden mit Apache Hop', anbSample: 'Beispiel', anbNew: 'neue Geschäfte', anbQueue: 'Warteschlange', anbDrain: 'abgebaut in', anbCut: 'Modell-Endpunkt war unterbrochen: die Warteschlange hielt die Geschäfte, bis derselbe Build wieder antwortete.', anbFoot: 'Speicher im Betrieb (docker stats, CI)',
    ueber: 'Überblick', karte: 'Karte', neu: 'Neues Thema', pruef: 'Prüfstand',
    bigScored: 'Geschäfte bewertet', bigWeeks: 'Wochen', bigWaiting: 'warten auf eine Person', thisWeek: 'Diese Woche', atlasLeg: 'Anteil an den bewerteten Geschäften des Kantons',
    affairs: 'Geschäfte', parls: 'Parlamente', scored: 'bewertet', of: 'von', build: 'Build', night: 'letzte Nacht', pending: 'zu prüfen',
    static: 'statisch', live: 'live', fixture: 'Fixture',
    federal: 'Bund', cantonal: 'Kantone', communal: 'Gemeinden', other: 'FL',
    lvl1: { federal: 'Bund', cantonal: 'Kanton', communal: 'Gemeinde', other: 'Liechtenstein' },
    same: n => `${n} gleichlautende Geschäfte`, sameNote: '1 / 2 entscheidet für alle', sameDec: n => `gilt für ${n} Geschäfte`, lines: 'Zeilen', pendingAll: 'zu prüfen, alle Themen (Export)', meta: 'Geschäft', read1: 'Reihenfolge 1', read2: 'Reihenfolge 2', readEx: 'mit Beispielen', readNoEx: 'ohne Beispiele', readsTip: 'Dieselbe Frage zweimal gestellt: bei Bundesgeschäften einmal mit fünf ähnlichen, von der APS-Redaktion eingeordneten Geschäften als Beispiel und einmal ohne; sonst mit den Themen in zwei Reihenfolgen. Grau: die Antwort jeder Lesart; schwarz: ihr erstes Thema.', cutoff: 'Schwelle', chapterP: 'p roh', overview: 'Überblick', weeks: 'Wochen nach Ebene', notable: 'Auffällig', acrossLv: (n) => `gleiche Woche, ${n} Ebenen`, newest: 'neu', matrix: 'Querschnitt', mapMode: 'Karte', matrixHint: 'Anteil der bewerteten Geschäfte eines Parlaments im Kapitel', gemAgg: 'Gemeinden', confusion: 'Verwechslungen (D4, ausgeliefert)', gold: 'APS-Redaktion', pred: 'Querschnitt', lanesT: 'Spuren', dark: 'dunkler Teil', rowsGold: 'Zeilen: APS-Redaktion', colsPred: 'Spalten: Querschnitt', agree: 'Lesarten einig', disagree: 'uneinig', noneOpen: 'keine offenen', noneOpenWeek: 'Keine offenen Geschäfte in dieser Woche. [‹] geht zurück.', noneTab: 'Nichts in diesem Reiter.', theme: 'Thema', themes: 'Geschäfte nach Thema', goldMatch: 'stimmt mit dem Kanton überein', theme1: 'Thema 1', theme12: 'Thema 1 oder 2', bsCredit: 'Thema laut Kantons- und Stadtentwicklung Basel-Stadt, CC BY 4.0', cantonTheme: 'Kanton', scoredPeriod: 'bewertet', ownSchemes: 'Eigene Schemata der Parlamente', savedTopics: 'Gespeicherte Themen', savedMark: 'gespeichert', dir: 'Direktion', beGroup: 'Grossratsgeschäfte nach federführender Direktion', beField: 'Feld des Grossen Rates', schemes: 'Schemata', bilingual: 'DE/FR-Lesarten', topic: 'Thema', topicPh: 'Thema wählen oder tippen', adhoc: 'Ad-hoc-Themen', chapters: 'APS-Kapitel', saved: 'Gespeichert (dieser Browser)',
    period: 'Zeitraum', all: 'alle', reset: 'zurücksetzen', hits: 'Treffer', notScored: 'noch nicht bewertet',
    coverage: 'bewertet', covered: 'erfasst ab', titleOnly: 'nur Titel', share: 'Anteil',
    hatch: 'schraffiert: unter 25 % bewertet oder ab 50 % nur Titel', tick: 'wartet auf eine Person', ramp: 'Anteil am Parlament',
    list: 'Liste', pult: 'Pult',
    tabs: { neu: 'neu diese Woche', todo: 'zu prüfen', ok: 'übernommen', changed: 'Status geändert', done: 'erledigt' },
    notSuggested: 'nicht als dieses Kapitel vorgeschlagen', overwrite: (d, by, at, k) => `${d} von ${by}, ${at} · [${k}] nochmals = überschreiben · Esc = behalten`,
    correct: 'richtig ist', noCorrection: 'ohne Korrektur weiter', corrected: 'korrigiert', undoLocal: 'nur lokal rückgängig: der Server kennt kein Undo',
    suggested: 'vorgeschlagen', allGroup: 'Suche', periodRead: 'liest', stopped: (r, n, why) => `gestoppt bei ${r} / ${n}${why ? ` (${why})` : ''}`,
    periods: { week: 'letzte Woche', month: 'letzter Monat', y2526: '2025–26' }, utc: 'Ortszeit',
    week: 'KW', newW: 'neu', newAff: 'neue Geschäfte', budget: 'Budget', perWeek: '/Woche',
    type: 'Typ', status: 'Status', party: 'Partei', search: 'Suche', searchPh: 'Titel, Name; a|b = oder',
    shown: 'angezeigt', export: 'CSV', selParl: 'Parlament', clear: 'aufheben',
    accept: 'übernehmen', reject: 'verwerfen', skip: 'überspringen', undo: 'rückgängig',
    who: 'Name', whoAsk: 'Name für die Entscheidung',
    decided: { confirmed: 'übernommen', rejected: 'verworfen' }, localSaved: 'lokal gespeichert (statisch)', apiSaved: 'gespeichert, API',
    apiErr: 'API-Fehler', by: 'von',
    evidence: 'Beleg', fullText: 'ganzer Text', noEvidence: 'kein Zitat gespeichert', text: 'Text', titleLong: 'Langer Titel',
    topicSec: 'Thema', chapter: 'APS-Kapitel', subtopics: 'Unterthemen', lane: 'Spur',
    lanes: { pass: 'ohne Prüfung', readings_agree: 'ohne Prüfung', please_check: 'bitte prüfen' }, readAgree: 'Lesarten einig', readDisagree: 'Lesarten uneinig', langsAgree: 'DE und FR einig', langsDisagree: 'DE und FR uneinig', notMeasured: 'nicht gemessen', bigShare: 'an eine Person', bigPass: 'ohne Prüfung', perWeek: n => `≈ ${n} pro Woche`, lede: n => `Geschäfte aus ${n} Schweizer Parlamenten, von Apertus einem Thema zugeordnet – mit dem Hinweis, wann eine Person prüfen soll, und wo vorhanden dem Satz, der es belegt.`, shipped: 'ausgeliefert: p ≥ 0.7', laneCheck: 'bitte prüfen: p < 0.7',
    readings: 'Lesarten', prov: 'Herkunft', model: 'Modell', page: 'Seite des Parlaments', similar: 'Ähnliche Geschäfte',
    kw: 'Stichwort', kwYes: 'Stichwortliste trifft', kwNo: 'Stichwortliste trifft nicht',
    yes: 'ja', no: 'nein', flagged: 'markiert', read: 'gelesen', secs: 's',
    summary: 'Auswahl', perLevel: 'nach Ebene', topParl: 'Parlamente mit den meisten Treffern', none: 'keine Treffer in der Auswahl',
    ntPh: 'Thema in einem Satz, in jeder Sprache', ntEx: 'Beispiele (optional, ein Titel pro Zeile)', ntTerms: 'Begriffe',
    ntStatic: 'Braucht den Live-Dienst: ?api=http://127.0.0.1:8000', ntRun: 'Enter startet', ntSave: 'speichern', ntSaved: 'gespeichert',
    ntPeriod: 'letzte Woche', ntWait: 'wartet auf Entscheidungen',
    human: 'Menschliche Labels', judge: 'KI-Richter', design: 'Design', result: 'Ergebnis', ci: '95-%-Intervall',
    baseline: 'Basislinie, gleiche Items', split: 'Split', file: 'Datei', cpTitle: 'Abdeckung und Präzision', refCurve: 'grau, zum Vergleich',
    cpX: 'Abdeckung', cpY: 'Präzision', fromFixture: 'aus Fixture',
    keys: [['j/k', 'bewegen'], ['1', 'übernehmen'], ['2', 'verwerfen'], ['0', 'überspringen'], ['l', 'Pult'], ['/', 'suchen'], ['t', 'Thema'], ['Esc', 'schliessen'], ['d/f', 'DE/FR']],
    method: (n, topic, per, sc, build) => `Querschnitt: ${n} Geschäfte zum Thema «${topic}», ${per}; im Zeitraum bewertet, pro Parlament: ${sc}; Build ${build}; maschinelle Vorschläge, wahrscheinlich unvollständig.`,
    prov1: 'Daten: OpenParlData.ch', geo: 'Grenzen: BFS GEOSTAT / swisstopo (swiss-maps 4.7.0)', engine: 'Modell',
  },
  fr: {
    anb: 'Intégration', anbTable: 'Table topics dans OpenParlData', anbCols: 'colonnes', anbMachine: 'machine (inferred)', anbDecision: 'décision (confirmed)', anbHop: 'Chargement avec Apache Hop', anbSample: 'exemple', anbNew: 'nouveaux objets', anbQueue: 'file', anbDrain: 'résorbée en', anbCut: 'Le point d\u2019accès du modèle était interrompu : la file a gardé les objets jusqu\u2019à ce que le même build réponde à nouveau.', anbFoot: 'Mémoire en service (docker stats, CI)',
    ueber: 'Aperçu', karte: 'Carte', neu: 'Nouveau thème', pruef: 'Banc d’essai',
    bigScored: 'objets évalués', bigWeeks: 'semaines', bigWaiting: 'attendent une personne', thisWeek: 'Cette semaine', atlasLeg: 'part des objets évalués du canton',
    affairs: 'objets', parls: 'parlements', scored: 'évalués', of: 'sur', build: 'Build', night: 'la nuit dernière', pending: 'à vérifier',
    static: 'statique', live: 'en ligne', fixture: 'Fixture',
    federal: 'Confédération', cantonal: 'Cantons', communal: 'Communes', other: 'FL',
    lvl1: { federal: 'Confédération', cantonal: 'Canton', communal: 'Commune', other: 'Liechtenstein' },
    same: n => `${n} objets identiques`, sameNote: '1 / 2 décide pour tous', sameDec: n => `vaut pour ${n} objets`, lines: 'lignes', pendingAll: 'à vérifier, tous thèmes (export)', meta: 'Objet', read1: 'ordre 1', read2: 'ordre 2', readEx: 'avec exemples', readNoEx: 'sans exemples', readsTip: 'La même question posée deux fois : pour les objets fédéraux, une fois avec cinq objets semblables classés par la rédaction APS comme exemples et une fois sans ; sinon avec les thèmes dans deux ordres. Gris : la réponse de chaque lecture ; noir : son premier thème.', cutoff: 'seuil', chapterP: 'p brut', overview: 'Aperçu', weeks: 'Semaines par niveau', notable: 'À noter', acrossLv: (n) => `même semaine, ${n} niveaux`, newest: 'nouveau', matrix: 'Querschnitt', mapMode: 'Carte', matrixHint: 'part des objets évalués d\u2019un parlement dans le chapitre', gemAgg: 'Communes', confusion: 'Confusions (D4, livré)', gold: 'rédaction APS', pred: 'Querschnitt', lanesT: 'Voies', dark: 'partie foncée', rowsGold: 'lignes : rédaction APS', colsPred: 'colonnes : Querschnitt', agree: 'lectures concordantes', disagree: 'discordantes', noneOpen: 'aucun en suspens', noneOpenWeek: 'Aucun objet en suspens cette semaine. [‹] recule.', noneTab: 'Rien dans cet onglet.', theme: 'Thème', themes: 'Objets par thème', goldMatch: 'concorde avec le canton', theme1: 'thème 1', theme12: 'thème 1 ou 2', bsCredit: 'Thème selon Kantons- und Stadtentwicklung Basel-Stadt, CC BY 4.0', cantonTheme: 'Canton', scoredPeriod: 'évalué', ownSchemes: 'Schémas propres des parlements', savedTopics: 'Thèmes enregistrés', savedMark: 'enregistré', dir: 'Direction', beGroup: 'Objets du Grand Conseil par direction compétente', beField: 'Champ du Grand Conseil', schemes: 'Schémas', bilingual: 'lectures DE/FR', topic: 'Thème', topicPh: 'Choisir ou taper un thème', adhoc: 'Thèmes ad hoc', chapters: 'Chapitres APS', saved: 'Enregistrés (ce navigateur)',
    period: 'Période', all: 'tous', reset: 'réinitialiser', hits: 'résultats', notScored: 'pas encore évalué',
    coverage: 'évalués', covered: 'couvert depuis', titleOnly: 'titres seuls', share: 'part',
    hatch: 'hachuré : moins de 25 % évalués ou 50 % titres seuls et plus', tick: 'attend une personne', ramp: 'part du parlement',
    list: 'Liste', pult: 'Pupitre',
    tabs: { neu: 'nouveaux cette semaine', todo: 'à vérifier', ok: 'acceptés', changed: 'statut modifié', done: 'traités' },
    notSuggested: 'pas proposé pour ce chapitre', overwrite: (d, by, at, k) => `${d} par ${by}, ${at} · [${k}] encore = remplacer · Esc = garder`,
    correct: 'correct', noCorrection: 'continuer sans correction', corrected: 'corrigé', undoLocal: 'annulé localement seulement : le serveur ne connaît pas l\u2019annulation',
    suggested: 'suggéré', allGroup: 'Recherche', periodRead: 'lit', stopped: (r, n, why) => `arrêté à ${r} / ${n}${why ? ` (${why})` : ''}`,
    periods: { week: 'semaine dernière', month: 'mois dernier', y2526: '2025–26' }, utc: 'heure locale',
    week: 'sem.', newW: 'nouveaux', newAff: 'nouveaux objets', budget: 'budget', perWeek: '/semaine',
    type: 'Type', status: 'Statut', party: 'Parti', search: 'Recherche', searchPh: 'titre, nom ; a|b = ou',
    shown: 'affichés', export: 'CSV', selParl: 'Parlement', clear: 'annuler',
    accept: 'accepter', reject: 'rejeter', skip: 'passer', undo: 'annuler',
    who: 'Nom', whoAsk: 'Nom pour la décision',
    decided: { confirmed: 'accepté', rejected: 'rejeté' }, localSaved: 'enregistré localement (statique)', apiSaved: 'enregistré, API',
    apiErr: 'Erreur API', by: 'par',
    evidence: 'Extrait', fullText: 'texte entier', noEvidence: 'aucune citation enregistrée', text: 'Texte', titleLong: 'Titre long',
    topicSec: 'Thème', chapter: 'Chapitre APS', subtopics: 'Sous-thèmes', lane: 'Voie',
    lanes: { pass: 'sans vérification', readings_agree: 'sans vérification', please_check: 'à vérifier' }, readAgree: 'lectures concordantes', readDisagree: 'lectures discordantes', langsAgree: 'DE et FR concordent', langsDisagree: 'DE et FR divergent', notMeasured: 'non mesuré', bigShare: 'à une personne', bigPass: 'sans vérification', perWeek: n => `≈ ${n} par semaine`, lede: n => `Objets de ${n} parlements suisses, classés par Apertus dans un thème – avec l\u2019indication du moment où une personne doit vérifier et, si disponible, la phrase qui le justifie.`, shipped: 'livré : p ≥ 0,7', laneCheck: 'à vérifier : p < 0,7',
    readings: 'lectures', prov: 'Provenance', model: 'Modèle', page: 'Page du parlement', similar: 'Objets similaires',
    kw: 'mot-clé', kwYes: 'la liste de mots-clés trouve', kwNo: 'la liste de mots-clés ne trouve pas',
    yes: 'oui', no: 'non', flagged: 'signalés', read: 'lus', secs: 's',
    summary: 'Sélection', perLevel: 'par niveau', topParl: 'Parlements avec le plus de résultats', none: 'aucun résultat dans la sélection',
    ntPh: 'Le thème en une phrase, dans n’importe quelle langue', ntEx: 'Exemples (facultatif, un titre par ligne)', ntTerms: 'Termes',
    ntStatic: 'Nécessite le service en ligne : ?api=http://127.0.0.1:8000', ntRun: 'Entrée lance', ntSave: 'enregistrer', ntSaved: 'enregistré',
    ntPeriod: 'semaine dernière', ntWait: 'attend les décisions',
    human: 'Étiquettes humaines', judge: 'Juge IA', design: 'Design', result: 'Résultat', ci: 'Intervalle 95 %',
    baseline: 'Référence, mêmes objets', split: 'Split', file: 'Fichier', cpTitle: 'Couverture et précision', refCurve: 'gris, pour comparaison',
    cpX: 'couverture', cpY: 'précision', fromFixture: 'de la fixture',
    keys: [['j/k', 'naviguer'], ['1', 'accepter'], ['2', 'rejeter'], ['0', 'passer'], ['l', 'pupitre'], ['/', 'chercher'], ['t', 'thème'], ['Esc', 'fermer'], ['d/f', 'DE/FR']],
    method: (n, topic, per, sc, build) => `Querschnitt : ${n} objets sur le thème « ${topic} », ${per} ; part évaluée dans la période, par parlement : ${sc} ; build ${build} ; suggestions automatiques, probablement incomplètes.`,
    prov1: 'Données : OpenParlData.ch', geo: 'Limites : OFS GEOSTAT / swisstopo (swiss-maps 4.7.0)', engine: 'Modèle',
  },
};
export const t = () => T[UI.lang];

export function debounce(fn, ms) { let id; return (...a) => { clearTimeout(id); id = setTimeout(() => fn(...a), ms); }; }
export function toast(msg) {
  let el = document.querySelector('.toast');
  if (!el) { el = h('div', { class: 'toast', role: 'status' }); document.body.append(el); }
  el.textContent = msg; el.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, 2200);
}
export function download(name, text, type = 'text/csv;charset=utf-8') {
  const a = h('a', { href: URL.createObjectURL(new Blob(['﻿' + text], { type })), download: name });
  document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}
