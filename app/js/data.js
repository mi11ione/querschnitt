// Data: static export (app/data/, CONTRACT §3) with a dev fallback (app/data-fixture/), the optional live API, topics,
// per-parliament statistics and the person's decisions.
import { dayNum, mondayOf } from './util.js';

const BASES = ['data/', 'data-fixture/'];
export const SRC = {}; // file -> base it came from

async function getJSON(url) {
  const r = await fetch(url, { cache: 'no-cache' });
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
    detailCache.set(k, getJSON(`${base}detail/${k}.json`).catch(() => ({})));
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
export async function apiPost(path, body) {
  const r = await fetch(`${API.base}${path}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
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
  const w0 = mondayOf(dmin);
  const week = new Int16Array(n);
  for (let i = 0; i < n; i++) week[i] = Math.floor((day[i] - w0) / 7);
  D.c = { id: c.id, body: c.body, date: c.date, title: c.title, lang: c.lang, type_h: c.type_h || [], type: c.type || [], type_h_fr: c.type_h_fr || [],
    be: c.be || [], bi: c.bi || [],
    state: c.state || [], party: c.party || [], submitter: c.submitter || [], number: c.number || [], subs: c.subs || [],
    bodyIdx, bodyKeys, day, week, ch, chp, lane, dp, df, dl, kw, lvl };
  D.w0 = w0; D.nWeeks = Math.floor((dmax - w0) / 7) + 1; D.dmin = dmin; D.dmax = dmax;
  D.rowOf = new Map(); for (let i = 0; i < n; i++) D.rowOf.set(c.id[i], i);
  D.anyCh = ch.some(v => v >= 0);
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
  // scheme swap: Bern's directorates (Grand Council affairs only)
  const be = ((D.scheme && D.scheme.schemes) || []).find(x => x.id === 'be-directorates');
  if (be && c.be.length) {
    const opt = new Map(be.options.map((o, k) => [o.code, { ...o, k }]));
    addTopic({ id: 'be-directorates', kind: 'be', scheme: 'be-directorates', scope: be.body || 'BE', options: be.options, opt,
      names: { de: 'Kanton Bern: Direktionen', fr: 'Canton de Berne : directions', it: 'Canton Berna: direzioni' },
      aliases: ['Bern', 'Berne', 'Direktionen', 'directions', 'BE'], codeOf: i => `be:${c.be[i]}`,
      scored: i => c.be[i] != null, hit: i => c.be[i] != null, p: () => NaN, check: i => c.bi[i] === 1,
      coverage: b => b.n_affairs ? (b.n_scored || 0) / b.n_affairs : null });
  }
  const chs = (D.scheme && D.scheme.chapters) || [];
  chs.forEach((x, i) => {
    const idx = x.i ?? i;
    addTopic({ id: x.code, kind: 'chapter', scheme: 'aps', code: x.code, idx, names: { de: x.de, fr: x.fr || x.de, it: x.it || x.de }, aliases: [x.code.replace('aps:', '')],
      scored: j => c.ch[j] >= 0, hit: j => c.ch[j] === idx, p: j => c.chp[j], check: j => c.lane[j] === 1,
      coverage: b => b.n_affairs ? (b.n_scored || 0) / b.n_affairs : null });
  });
  const subs = (D.scheme && D.scheme.subtopics) || {};
  for (const [k, x] of Object.entries(subs)) {
    const code = +k;
    addTopic({ id: x.code, kind: 'sub', scheme: 'aps', code: x.code, idx: code, ch: x.ch, names: { de: x.de, fr: x.de, it: x.de }, aliases: [],
      scored: j => c.ch[j] >= 0, hit: j => { const sb = c.subs[j]; return !!sb && sb[0] === code; }, p: j => c.chp[j], check: j => c.lane[j] === 1,
      coverage: b => b.n_affairs ? (b.n_scored || 0) / b.n_affairs : null });
  }
  // counts per topic (hits over all rows)
  for (const tp of TOPICS) tp.count = 0;
  const dig = TOPIC_BY_ID.get('adhoc/digitalisierung');
  const chT = new Map(TOPICS.filter(x => x.kind === 'chapter').map(x => [x.idx, x]));
  const subT = new Map(TOPICS.filter(x => x.kind === 'sub').map(x => [x.idx, x]));
  const beT = TOPIC_BY_ID.get('be-directorates');
  for (let i = 0; i < D.n; i++) {
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
export function importApiDecisions(rows) {
  for (const r of rows || []) {
    if (r.status !== 'confirmed' && r.status !== 'rejected') continue;
    const k = `${r.scheme === 'aps' ? r.code : r.scheme}|${r.affair_id}`;
    if (!DEC[k]) DEC[k] = { d: r.status, by: r.confirmed_by || '', at: r.confirmed_at || r.valid_from, api: true };
  }
}
