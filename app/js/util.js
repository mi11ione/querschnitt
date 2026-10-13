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
    karte: 'Karte', neu: 'Neues Thema', pruef: 'Prüfstand',
    affairs: 'Geschäfte', parls: 'Parlamente', scored: 'bewertet', of: 'von', build: 'Build', night: 'letzte Nacht', pending: 'zu prüfen',
    static: 'statisch', live: 'live', fixture: 'Fixture',
    federal: 'Bund', cantonal: 'Kantone', communal: 'Gemeinden', other: 'FL',
    lvl1: { federal: 'Bund', cantonal: 'Kanton', communal: 'Gemeinde', other: 'Liechtenstein' },
    topic: 'Thema', topicPh: 'Thema wählen oder tippen', adhoc: 'Ad-hoc-Themen', chapters: 'APS-Kapitel', saved: 'Gespeichert (dieser Browser)',
    period: 'Zeitraum', all: 'alle', reset: 'zurücksetzen', hits: 'Treffer', notScored: 'noch nicht bewertet',
    coverage: 'bewertet', covered: 'erfasst ab', titleOnly: 'nur Titel', share: 'Anteil',
    hatch: 'schraffiert: unter 25 % bewertet oder ab 50 % nur Titel', tick: 'wartet auf eine Person', ramp: 'Anteil am Parlament',
    list: 'Liste', pult: 'Pult',
    tabs: { todo: 'zu prüfen', ok: 'übernommen', changed: 'Status geändert', done: 'erledigt' },
    week: 'KW', newW: 'neu', budget: 'Budget', perWeek: '/Woche',
    type: 'Typ', status: 'Status', party: 'Partei', search: 'Suche', searchPh: 'Titel, Name; a|b = oder',
    shown: 'angezeigt', export: 'CSV', selParl: 'Parlament', clear: 'aufheben',
    accept: 'übernehmen', reject: 'verwerfen', skip: 'überspringen', undo: 'rückgängig',
    who: 'Name', whoAsk: 'Name für die Entscheidung',
    decided: { confirmed: 'übernommen', rejected: 'verworfen' }, localSaved: 'lokal gespeichert (statisch)', apiSaved: 'gespeichert, API',
    apiErr: 'API-Fehler', by: 'von',
    evidence: 'Beleg', fullText: 'ganzer Text', noEvidence: 'kein Zitat gespeichert', text: 'Text', titleLong: 'Langer Titel',
    topicSec: 'Thema', chapter: 'APS-Kapitel', subtopics: 'Unterthemen', lane: 'Spur',
    lanes: { readings_agree: 'Lesarten einig', please_check: 'bitte prüfen' },
    readings: 'Lesarten', prov: 'Herkunft', model: 'Modell', page: 'Seite des Parlaments', similar: 'Ähnliche Geschäfte',
    kw: 'Stichwort', kwYes: 'Stichwortliste trifft', kwNo: 'Stichwortliste trifft nicht',
    yes: 'ja', no: 'nein', flagged: 'markiert', read: 'gelesen', secs: 's',
    summary: 'Auswahl', perLevel: 'nach Ebene', topParl: 'Parlamente mit den meisten Treffern', none: 'keine Treffer in der Auswahl',
    ntPh: 'Thema in einem Satz, in jeder Sprache', ntEx: 'Beispiele (optional, ein Titel pro Zeile)', ntTerms: 'Begriffe',
    ntStatic: 'Braucht den Live-Dienst: ?api=http://127.0.0.1:8000', ntRun: 'Enter startet', ntSave: 'speichern', ntSaved: 'gespeichert',
    ntPeriod: 'letzte Woche', ntWait: 'wartet auf Entscheidungen',
    human: 'Menschliche Labels', judge: 'KI-Richter', design: 'Design', result: 'Ergebnis', ci: '95-%-Intervall',
    baseline: 'Basislinie, gleiche Items', split: 'Split', file: 'Datei', cpTitle: 'Abdeckung und Präzision',
    cpX: 'Abdeckung', cpY: 'Präzision', fromFixture: 'aus Fixture',
    keys: [['j/k', 'bewegen'], ['1', 'übernehmen'], ['2', 'verwerfen'], ['0', 'überspringen'], ['l', 'Pult'], ['/', 'suchen'], ['t', 'Thema'], ['Esc', 'schliessen'], ['d/f', 'DE/FR']],
    method: (n, topic, per, sc, build) => `Querschnitt: ${n} Geschäfte zum Thema «${topic}», ${per}; bewertet ${sc}; Build ${build}; maschinelle Vorschläge, wahrscheinlich unvollständig.`,
    prov1: 'Daten: OpenParlData.ch', geo: 'Grenzen: BFS GEOSTAT / swisstopo (swiss-maps 4.7.0)', engine: 'Modell',
  },
  fr: {
    karte: 'Carte', neu: 'Nouveau thème', pruef: 'Banc d’essai',
    affairs: 'objets', parls: 'parlements', scored: 'évalués', of: 'sur', build: 'Build', night: 'la nuit dernière', pending: 'à vérifier',
    static: 'statique', live: 'en ligne', fixture: 'Fixture',
    federal: 'Confédération', cantonal: 'Cantons', communal: 'Communes', other: 'FL',
    lvl1: { federal: 'Confédération', cantonal: 'Canton', communal: 'Commune', other: 'Liechtenstein' },
    topic: 'Thème', topicPh: 'Choisir ou taper un thème', adhoc: 'Thèmes ad hoc', chapters: 'Chapitres APS', saved: 'Enregistrés (ce navigateur)',
    period: 'Période', all: 'tous', reset: 'réinitialiser', hits: 'résultats', notScored: 'pas encore évalué',
    coverage: 'évalués', covered: 'couvert depuis', titleOnly: 'titres seuls', share: 'part',
    hatch: 'hachuré : moins de 25 % évalués ou 50 % titres seuls et plus', tick: 'attend une personne', ramp: 'part du parlement',
    list: 'Liste', pult: 'Pupitre',
    tabs: { todo: 'à vérifier', ok: 'acceptés', changed: 'statut modifié', done: 'traités' },
    week: 'sem.', newW: 'nouveaux', budget: 'budget', perWeek: '/semaine',
    type: 'Type', status: 'Statut', party: 'Parti', search: 'Recherche', searchPh: 'titre, nom ; a|b = ou',
    shown: 'affichés', export: 'CSV', selParl: 'Parlement', clear: 'annuler',
    accept: 'accepter', reject: 'rejeter', skip: 'passer', undo: 'annuler',
    who: 'Nom', whoAsk: 'Nom pour la décision',
    decided: { confirmed: 'accepté', rejected: 'rejeté' }, localSaved: 'enregistré localement (statique)', apiSaved: 'enregistré, API',
    apiErr: 'Erreur API', by: 'par',
    evidence: 'Extrait', fullText: 'texte entier', noEvidence: 'aucune citation enregistrée', text: 'Texte', titleLong: 'Titre long',
    topicSec: 'Thème', chapter: 'Chapitre APS', subtopics: 'Sous-thèmes', lane: 'Voie',
    lanes: { readings_agree: 'lectures concordantes', please_check: 'à vérifier' },
    readings: 'lectures', prov: 'Provenance', model: 'Modèle', page: 'Page du parlement', similar: 'Objets similaires',
    kw: 'mot-clé', kwYes: 'la liste de mots-clés trouve', kwNo: 'la liste de mots-clés ne trouve pas',
    yes: 'oui', no: 'non', flagged: 'signalés', read: 'lus', secs: 's',
    summary: 'Sélection', perLevel: 'par niveau', topParl: 'Parlements avec le plus de résultats', none: 'aucun résultat dans la sélection',
    ntPh: 'Le thème en une phrase, dans n’importe quelle langue', ntEx: 'Exemples (facultatif, un titre par ligne)', ntTerms: 'Termes',
    ntStatic: 'Nécessite le service en ligne : ?api=http://127.0.0.1:8000', ntRun: 'Entrée lance', ntSave: 'enregistrer', ntSaved: 'enregistré',
    ntPeriod: 'semaine dernière', ntWait: 'attend les décisions',
    human: 'Étiquettes humaines', judge: 'Juge IA', design: 'Design', result: 'Résultat', ci: 'Intervalle 95 %',
    baseline: 'Référence, mêmes objets', split: 'Split', file: 'Fichier', cpTitle: 'Couverture et précision',
    cpX: 'couverture', cpY: 'précision', fromFixture: 'de la fixture',
    keys: [['j/k', 'naviguer'], ['1', 'accepter'], ['2', 'rejeter'], ['0', 'passer'], ['l', 'pupitre'], ['/', 'chercher'], ['t', 'thème'], ['Esc', 'fermer'], ['d/f', 'DE/FR']],
    method: (n, topic, per, sc, build) => `Querschnitt : ${n} objets sur le thème « ${topic} », ${per} ; évalués ${sc} ; build ${build} ; suggestions automatiques, probablement incomplètes.`,
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
