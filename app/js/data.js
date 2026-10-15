// Data: static export (app/data/, CONTRACT §3) with a dev fallback (app/data-fixture/), the optional live API, topics,
// per-parliament statistics and the person's decisions.
import { dayNum, mondayOf } from './util.js';

const BASES = ['data/', 'data-fixture/'];
export const SRC = {}; // file -> base it came from

async function getJSON(url, tries = 2) {
  let r;
  try { r = await fetch(url, { cache: 'no-cache' }); } catch (e) { if (tries > 1) { await new Promise(f => setTimeout(f, 300)); return getJSON(url, tries - 1); } throw e; }
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}
async function loadFile(name, optional = false) {
  for (const b of BASES) {
    try { const j = await getJSON(b + name); SRC[name] = b; return j; } catch (e) { /* next */ }
  }
  if (optional) return null;
  throw new Error(`missing ${name}`);
}

const detailCache = new Map();
export async function detail(id) {
  const k = Math.floor(id / 1000);
  if (!detailCache.has(k)) {
    const base = SRC['affairs.json'] || BASES[0];
    detailCache.set(k, getJSON(`${base}detail/${k}.json`).catch(() => { detailCache.delete(k); return {}; }));
  }
  const d = await detailCache.get(k);
  return d[String(id)] || null;
}

// ---------------------------------------------------------------- API (same origin or ?api=)
export const API = { base: null, live: false, metrics: null };
export async function probeApi() {
  const q = new URLSearchParams(location.search).get('api');
  const cands = q ? [q.replace(/\/$/, '')] : [''];
  for (const b of cands) {
    try {
      const ctl = new AbortController(); const id = setTimeout(() => ctl.abort(), 1500);
      const r = await fetch(`${b}/health`, { signal: ctl.signal, cache: 'no-store' });
      clearTimeout(id);
      const ct = r.headers.get('content-type') || '';
      if (r.ok && ct.includes('json')) {
        API.base = b; API.live = true;
        try { API.metrics = await (await fetch(`${b}/metrics`)).json(); } catch (e) { /* optional */ }
        return true;
      }
    } catch (e) { /* static */ }
  }
  return false;
}
// writes carry the API's QS_WRITE_TOKEN when one is stored: localStorage.setItem('qs.token', '…') (SERVICE.md)
export async function apiPost(path, body) {
  const headers = { 'content-type': 'application/json' };
  try { const t = localStorage.getItem('qs.token'); if (t) headers.authorization = `Bearer ${t}`; } catch (e) { /* storage off */ }
  const r = await fetch(`${API.base}${path}`, { method: 'POST', headers, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// ---------------------------------------------------------------- the store
export const D = { meta: null, bodies: [], B: new Map(), scheme: null, pruef: null, geo: null, n: 0, c: null };

function laneBit(v) { return v === 1 || v === true || v === 'please_check' ? 1 : (v == null ? -1 : 0); }

export async function load() {
  const [meta, bodies, affairs, scheme, geo] = await Promise.all([
    loadFile('meta.json'), loadFile('bodies.json'), loadFile('affairs.json'), loadFile('scheme_aps.json'), loadFile('geo.json')]);
  const pruef = await loadFile('pruefstand.json', true);
  D.conf = await loadFile('pruef_confusion.json', true);
  D.meta = meta; D.scheme = scheme; D.geo = geo; D.pruef = pruef;
  // bodies
  D.bodies = bodies;
  for (const b of bodies) {
    if (b.key === 'CHE' && (!b.name_de || b.name_de === b.place_de)) { b.name_de = 'Bundesversammlung'; b.name_fr = 'Assemblée fédérale'; }
    if (b.key === 'LIE' && (!b.name_de || b.name_de === b.place_de || /Liechtenstein/.test(b.name_de))) { b.name_de = 'Landtag'; b.name_fr = 'Landtag'; }
    if (b.level === 'other' && b.key !== 'LIE') b.level = 'other';
    b.lang = (b.lang || '').toLowerCase() || null;
    if (b.covered_from != null && !(+b.covered_from >= 1800)) b.covered_from = null;
    D.B.set(b.key, b);
  }
  // affairs (columnar)
  const c = affairs.cols || affairs;
  const n = c.id.length; D.n = n;
  const bodyIdx = new Int16Array(n), bodyKeys = [], bmap = new Map();
  const day = new Int32Array(n), ch = new Int16Array(n), chp = new Float32Array(n), lane = new Int8Array(n);
  const dp = new Float32Array(n), df = new Uint8Array(n), dl = new Int8Array(n), kw = new Uint8Array(n), lvl = new Uint8Array(n);
  const LV = { federal: 0, cantonal: 1, communal: 2, other: 3 };
  let dmin = Infinity, dmax = -Infinity;
  for (let i = 0; i < n; i++) {
    const k = c.body[i];
    let bi = bmap.get(k);
    if (bi == null) { bi = bodyKeys.length; bmap.set(k, bi); bodyKeys.push(k); }
    bodyIdx[i] = bi;
    const b = D.B.get(k);
    lvl[i] = b ? (LV[b.level] ?? 3) : (k === 'CHE' ? 0 : /^[A-Z]{2}$/.test(k) ? 1 : /^\d+$/.test(k) ? 2 : 3);
    const dd = c.date[i] ? dayNum(c.date[i]) : NaN; day[i] = dd;
    if (dd < dmin) dmin = dd; if (dd > dmax) dmax = dd;
    ch[i] = c.ch && c.ch[i] != null ? c.ch[i] : -1;
    chp[i] = c.ch_p && c.ch_p[i] != null ? c.ch_p[i] : NaN;
    lane[i] = c.lane ? laneBit(c.lane[i]) : -1;
    dp[i] = c.dig_p && c.dig_p[i] != null ? c.dig_p[i] : NaN;
    df[i] = c.dig_flag && c.dig_flag[i] ? 1 : 0;
    dl[i] = c.dig_lane ? laneBit(c.dig_lane[i]) : -1;
    kw[i] = c.kw && c.kw[i] ? 1 : 0;
  }
  if (meta.until) dmax = Math.min(dmax, dayNum(meta.until)); // future-dated affairs stay listed, the period ends today
  if (meta.until) dmax = Math.min(dmax, dayNum(meta.until)); // future-dated affairs stay listed, the period ends today
  const w0 = mondayOf(dmin);
  const week = new Int16Array(n);
  for (let i = 0; i < n; i++) week[i] = Math.floor((day[i] - w0) / 7);
  D.c = { id: c.id, body: c.body, date: c.date, title: c.title, lang: c.lang, type_h: c.type_h || [], type: c.type || [], type_h_fr: c.type_h_fr || [],
    be: c.be || [], bi: c.bi || [], beLane: c.be_lane || [], own: c.own || [], ownGold: c.own_gold || [], adhoc: c.adhoc || [],
    state: c.state || [], party: c.party || [], submitter: c.submitter || [], number: c.number || [], subs: c.subs || [],
    bodyIdx, bodyKeys, day, week, ch, chp, lane, dp, df, dl, kw, lvl };
  D.w0 = w0; D.nWeeks = Math.floor((dmax - w0) / 7) + 1; D.dmax = dmax;
  // the main slice (meta.since …); extra affairs before it (e.g. Basel-Stadt 2019–24 for its own scheme) only show in their scheme's view
  D.dminAll = dmin; D.dmin = meta.since ? Math.max(dmin, dayNum(meta.since)) : dmin;
  D.mainW = Math.floor((D.dmin - w0) / 7); D.lastW = Math.floor((dmax - w0) / 7);
  D.rowOf = new Map(); for (let i = 0; i < n; i++) D.rowOf.set(c.id[i], i);
  D.anyCh = ch.some(v => v >= 0);
  // one set of counts for every screen (fact line, Überblick, Karte): affairs dated in the main period, meta.since …
  // export date (docs/APP.md «Zählweisen»). «aps» = with an APS chapter decision, «dig» = with a Digitalisierung
  // decision, «check» = APS rows in the please-check lane. meta.json's own counts also hold the future-dated affairs.
  const T = D.tally = { affairs: 0, aps: 0, dig: 0, check: 0 };
  for (let i = 0; i < n; i++) {
    if (day[i] < D.dmin || day[i] > dmax) continue;
    T.affairs++; if (ch[i] >= 0) { T.aps++; if (lane[i] === 1) T.check++; } if (!Number.isNaN(dp[i])) T.dig++;
  }
  buildTopics();
}

// ---------------------------------------------------------------- topics
export const TOPICS = [];
export const TOPIC_BY_ID = new Map();
function addTopic(tp) { TOPICS.push(tp); TOPIC_BY_ID.set(tp.id, tp); }

export const norm = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();

function buildTopics() {
  TOPICS.length = 0; TOPIC_BY_ID.clear();
  const c = D.c;
  const ad = (D.scheme && D.scheme.topics) || D.meta.topics || [{ id: 'adhoc/digitalisierung', names: { de: 'Digitalisierung', fr: 'numérique', it: 'digitalizzazione' }, aliases: [] }];
  for (const a of ad) {
    if (a.id !== 'adhoc/digitalisierung') continue; // further ad-hoc topics arrive as columns once the export carries them
    addTopic({ id: a.id, kind: 'adhoc', scheme: a.id, code: `${a.id}:yes`, names: a.names, aliases: [...(a.aliases || []), ...Object.values(a.names || {})],
      scored: i => !Number.isNaN(c.dp[i]), hit: i => c.df[i] === 1, p: i => c.dp[i], check: i => c.dl[i] === 1,
      coverage: b => b.n_affairs ? (b.n_dig ?? b.n_scored) / b.n_affairs : null });
  }
  // every affair, no topic: search across all of them
  addTopic({ id: 'all', kind: 'all', names: { de: 'alle Geschäfte', fr: 'tous les objets', it: 'tutti gli oggetti' }, aliases: ['alle', 'tous', 'all', 'tutti'],
    code: 'all', scored: () => true, hit: () => true, p: () => NaN, check: () => false, coverage: () => null, count: 0 });
  // scheme swap: Bern's directorates (Grand Council affairs only)
  const be = ((D.scheme && D.scheme.schemes) || []).find(x => x.id === 'be-directorates');
  if (be && c.be.length) {
    const opt = new Map(be.options.map((o, k) => [o.code, { ...o, k }]));
    addTopic({ id: 'be-directorates', kind: 'be', scheme: 'be-directorates', scope: be.body || 'BE', options: be.options, opt, prefix: 'be',
      names: { de: 'Kanton Bern: Direktionen', fr: 'Canton de Berne : directions', it: 'Canton Berna: direzioni' },
      aliases: ['Bern', 'Berne', 'Direktionen', 'directions', 'BE'], codeAt: i => c.be[i], codeOf: i => `be:${c.be[i]}`,
      scored: i => c.be[i] != null, hit: i => c.be[i] != null, p: () => NaN, check: i => c.beLane[i] === 1,
      coverage: b => b.n_affairs ? (b.n_scored || 0) / b.n_affairs : null });
  }
  // a parliament's own named scheme (Basel-Stadt's 46 Themen, Ticino's lead departments): column own = [schemeId, code,
  // lane], own_gold = the parliament's own label [code, second code]; the export names the scheme (names, unit, group,
  // source), else «<place>: <n> Themen»
  for (const sc of ((D.scheme && D.scheme.schemes) || []).filter(x => x.kind === 'named')) {
    const opt = new Map(sc.options.map((o, k) => [o.code, { ...o, k }]));
    const mine = i => { const o = c.own[i]; return o && o[0] === sc.id ? o : null; };
    let a = Infinity, z = -Infinity, da = Infinity, dz = -Infinity, gold = false, gold2 = false;
    for (let i = 0; i < D.n; i++) if (mine(i)) {
      if (c.week[i] < a) a = c.week[i]; if (c.week[i] > z) z = c.week[i]; if (c.day[i] < da) da = c.day[i]; if (c.day[i] > dz) dz = c.day[i];
      const g = c.ownGold[i]; if (g && g[0]) { gold = true; if (g[1]) gold2 = true; }
    }
    const place = (D.B.get(sc.body) || {}).place_de || sc.body, placeFr = (D.B.get(sc.body) || {}).place_fr || place;
    const names = sc.names || { de: `${place}: ${sc.options.length - 1} Themen`, fr: `${placeFr} : ${sc.options.length - 1} thèmes`, it: place };
    const unit = sc.unit || { de: 'Thema', fr: 'Thème' };
    addTopic({ id: sc.id, kind: 'be', named: true, scheme: sc.id, scope: sc.body, options: sc.options, opt, prefix: sc.id, names,
      unit, group: sc.group || null, source: sc.source || null,
      title: sc.title, aliases: [...new Set([place, placeFr, sc.body, ...Object.values(names), ...Object.values(sc.title || {}), ...(sc.names ? [] : ['Themen', 'thèmes'])])],
      dom: a <= z ? [a, z] : null, domDays: a <= z ? [da, dz] : null, gold, gold2,
      codeAt: i => { const o = mine(i); return o ? o[1] : null; }, codeOf: i => `${sc.id}:${(mine(i) || [])[1]}`,
      scored: i => !!mine(i), hit: i => !!mine(i), p: () => NaN, check: i => { const o = mine(i); return !!o && o[2] === 1; },
      coverage: () => null });
  }
  // saved ad-hoc topics: column adhoc = {slug: [p, flag, lane]}; scored over a narrower period than the slice
  for (const x of ((D.scheme && D.scheme.topics) || []).filter(x => x.id !== 'adhoc/digitalisierung')) {
    const slug = x.id.replace(/^adhoc\//, '');
    const P = new Float32Array(D.n).fill(NaN), F = new Uint8Array(D.n), Ln = new Int8Array(D.n);
    // the scored period: the weeks in which at least half of all affairs carry a decision (a topic file may say it: x.period)
    const sw = new Int32Array(D.nWeeks), aw = new Int32Array(D.nWeeks);
    for (let i = 0; i < D.n; i++) {
      if (c.day[i] >= D.dmin && c.day[i] <= D.dmax) aw[c.week[i]]++;
      const v = c.adhoc[i] && c.adhoc[i][slug]; if (!v) continue; P[i] = v[0]; F[i] = v[1] ? 1 : 0; Ln[i] = v[2] ? 1 : 0; sw[c.week[i]]++;
    }
    let a = Infinity, z = -Infinity;
    for (let w = 0; w < D.nWeeks; w++) if (aw[w] && sw[w] / aw[w] >= 0.5) { a = Math.min(a, D.w0 + w * 7); z = Math.max(z, Math.min(D.dmax, D.w0 + w * 7 + 6)); }
    if (x.period && x.period[0]) { a = dayNum(String(x.period[0]).slice(0, 10)); z = Math.min(D.dmax, dayNum(String(x.period[1]).slice(0, 10))); }
    const measured = !!x.measured || ((D.pruef && (D.pruef.rows || D.pruef)) || []).some(r => r.topic === x.id);
    addTopic({ id: x.id, kind: 'adhoc', saved: true, measured, scheme: x.id, code: `${x.id}:yes`, names: x.names || { de: slug, fr: slug }, aliases: [...Object.values(x.names || {}), slug],
      scoredDays: a <= z ? [a, z] : null, scored: i => !Number.isNaN(P[i]), hit: i => F[i] === 1, p: i => P[i], check: i => Ln[i] === 1, coverage: () => null, count: 0 });
  }
  const chs = (D.scheme && D.scheme.chapters) || [];
  chs.forEach((x, i) => {
    const idx = x.i ?? i;
    addTopic({ id: x.code, kind: 'chapter', scheme: 'aps', code: x.code, idx, names: { de: x.de, fr: x.fr || x.de, it: x.it || x.de }, aliases: [x.code.replace('aps:', '')],
      scored: j => c.ch[j] >= 0, hit: j => c.ch[j] === idx, p: j => c.chp[j], check: j => c.ch[j] === idx && c.lane[j] === 1,
      coverage: b => b.n_affairs ? (b.n_scored || 0) / b.n_affairs : null });
  });
  const subs = (D.scheme && D.scheme.subtopics) || {};
  for (const [k, x] of Object.entries(subs)) {
    const code = +k;
    addTopic({ id: x.code, kind: 'sub', scheme: 'aps', code: x.code, idx: code, ch: x.ch, names: { de: x.de, fr: x.de, it: x.de }, aliases: [],
      scored: j => c.ch[j] >= 0, hit: j => { const sb = c.subs[j]; return !!sb && sb[0] === code; }, p: j => c.chp[j], check: j => { const sb = c.subs[j]; return !!sb && sb[0] === code && c.lane[j] === 1; },
      coverage: b => b.n_affairs ? (b.n_scored || 0) / b.n_affairs : null });
  }
  // counts per topic (hits over all rows)
  for (const tp of TOPICS) tp.count = 0;
  for (const tp of TOPICS) if (tp.saved) for (let i = 0; i < D.n; i++) if (tp.hit(i)) tp.count++;
  TOPIC_BY_ID.get('all').count = [...D.c.day].filter(d => d >= D.dmin && d <= D.dmax).length;
  const dig = TOPIC_BY_ID.get('adhoc/digitalisierung');
  const chT = new Map(TOPICS.filter(x => x.kind === 'chapter').map(x => [x.idx, x]));
  const subT = new Map(TOPICS.filter(x => x.kind === 'sub').map(x => [x.idx, x]));
  const beT = TOPIC_BY_ID.get('be-directorates');
  for (let i = 0; i < D.n; i++) {
    if (c.own[i]) { const tn = TOPIC_BY_ID.get(c.own[i][0]); if (tn) tn.count++; }
    if (c.day[i] < D.dmin || c.day[i] > D.dmax) continue; // topic counts cover the main period (as D.tally)
    if (dig && c.df[i]) dig.count++;
    if (beT && c.be[i] != null) beT.count++;
    if (c.ch[i] >= 0) { const tc = chT.get(c.ch[i]); if (tc) tc.count++; const sb = c.subs[i]; if (sb && sb.length) { const ts = subT.get(sb[0]); if (ts) ts.count++; } }
  }
}

// live (Neues Thema) topics share the same interface
export function liveTopic(slug, names, dec) {
  const c = D.c;
  const tp = { id: `adhoc/${slug}`, kind: 'live', scheme: `adhoc/${slug}`, code: `adhoc/${slug}:yes`, names, aliases: Object.values(names), dec,
    scored: i => dec.has(c.id[i]), hit: i => { const d = dec.get(c.id[i]); return !!d && !!d.flag; },
    p: i => { const d = dec.get(c.id[i]); return d ? d.p : NaN; }, check: i => { const d = dec.get(c.id[i]); return !!d && d.p >= 0.3 && d.p < 0.7; },
    coverage: () => null, count: 0 };
  return tp;
}
export function registerTopic(tp) { if (!TOPIC_BY_ID.has(tp.id)) addTopic(tp); else { const i = TOPICS.indexOf(TOPIC_BY_ID.get(tp.id)); TOPICS[i] = tp; TOPIC_BY_ID.set(tp.id, tp); } }

export function findTopic(q) {
  const n = norm(q); if (!n) return null;
  for (const tp of TOPICS) if (tp.aliases.some(a => norm(a) === n) || Object.values(tp.names).some(v => norm(v) === n)) return tp;
  return null;
}

// ---------------------------------------------------------------- decisions (API rows or local)
const DKEY = 'qs.dec.v1';
let DEC = {};
try { DEC = JSON.parse(localStorage.getItem(DKEY) || '{}'); } catch (e) { DEC = {}; }
export const decKey = (tp, id) => `${tp.id}|${id}`;
export const getDec = (tp, id) => DEC[decKey(tp, id)] || null;
export function setDec(tp, id, rec) {
  if (rec) DEC[decKey(tp, id)] = rec; else delete DEC[decKey(tp, id)];
  try { localStorage.setItem(DKEY, JSON.stringify(DEC)); } catch (e) { /* storage off */ }
}
export function allDec() { return DEC; }
// server decisions (who/when) → the same map; the newest row per (topic, affair) wins, a closed newest row = undone
const keyOf = r => r.scheme === 'aps' ? `${r.code}|${r.affair_id}` : `${r.scheme}|${r.affair_id}`;
export function importApiDecisions(rows) {
  const latest = new Map();
  for (const r of rows || []) {
    if (r.provenance !== 'confirmed' && r.status !== 'confirmed' && r.status !== 'rejected') continue;
    if (r.status !== 'confirmed' && r.status !== 'rejected') continue;
    const k = keyOf(r), t0 = r.valid_from || r.confirmed_at || '';
    const o = latest.get(k); if (!o || (o.valid_from || '') <= t0) latest.set(k, r);
  }
  let n = 0;
  for (const [k, r] of latest) {
    const at = r.confirmed_at || r.valid_from || '', cur = DEC[k];
    if (cur && !cur.srv && (cur.at || '') > at) continue; // a newer local decision stays
    if (r.valid_to) {
      // closed: superseded or undone; only drop it when it is the newest row we know
      if (cur && cur.srv && cur.at <= at) { delete DEC[k]; n++; }
      continue;
    }
    const code = r.code && r.scheme === 'be-directorates' ? String(r.code).replace(/^be:/, '') : null;
    DEC[k] = { d: r.status, by: r.confirmed_by || '', at, api: true, srv: true, code };
    n++;
  }
  try { localStorage.setItem(DKEY, JSON.stringify(DEC)); } catch (e) { /* */ }
  return n;
}
let SINCE = null;
export async function syncDecisions() {
  if (!API.live) return 0;
  const all = []; let url = `/changes?kind=decisions&since=${encodeURIComponent(SINCE || '1970-01-01T00:00:00Z')}&limit=5000`, pages = 0, offset = 0, base = url;
  while (url && pages < 30) {
    pages++;
    let j; try { const r = await fetch(API.base + url, { cache: 'no-store' }); if (!r.ok) break; j = await r.json(); } catch (e) { break; }
    const rows = Array.isArray(j) ? j : (j.rows || []);
    const machine = rows.filter(r => r.provenance === 'inferred');
    all.push(...rows.filter(r => r.provenance !== 'inferred'));
    // our API ends a feed with next: null (its `cursor` is always set, and it pages with after=, not cursor=)
    const next = !Array.isArray(j) && ('next' in j ? j.next : (j.next_cursor || j.cursor));
    if (next && rows.length) url = String(next).startsWith('/') ? String(next) : `/changes?kind=decisions&cursor=${encodeURIComponent(next)}&limit=5000`;
    else if (machine.length && pages === 1) {
      // a server without kind=decisions: machine rows share their load time; ask for what came after it
      const t = machine.reduce((a, r) => (r.valid_from > a ? r.valid_from : a), '');
      base = `/changes?since=${encodeURIComponent(t)}&limit=5000`; offset = 0; url = base;
    } else if (rows.length >= 5000) { offset += 5000; url = `${base}&offset=${offset}`; }
    else url = null;
  }
  for (const r of all) { const t = r.valid_to && r.valid_to > (r.valid_from || '') ? r.valid_to : r.valid_from; if (t && (!SINCE || t > SINCE)) SINCE = t; }
  return importApiDecisions(all);
}
