// Shell: one bar (wordmark, three views with counts, DE/FR, build), one mono fact line, the view, provenance footer.
import { D, SRC, API, load, probeApi, TOPIC_BY_ID, findTopic, syncDecisions } from './data.js';
import { $, h, t, UI, num, pct } from './util.js';
import { Board } from './board.js';
import { Neu, loadSaved } from './neu.js';
import { renderPruef, testCount } from './pruef.js';
import { Atlas } from './atlas.js';
import { renderAnb } from './anb.js';

const VIEWS = ['ueber', 'karte', 'neu', 'pruef', 'anb'];
let view = 'ueber', karte = null, neu = null, atlas = null;

function setLang(l) {
  UI.lang = l; document.documentElement.lang = l;
  try { localStorage.setItem('qs.lang', l); } catch (e) { /* */ }
  renderShell();
  if (karte) karte.relang();
  if (neu) neu.relang();
  if (view === 'pruef') renderPruef($('#v-pruef'));
  if (view === 'ueber') atlas.render();
  if (view === 'anb') renderAnb($('#v-anb'));
}

function renderShell() {
  const L = t(), m = D.meta;
  // bar
  const counts = { anb: '', ueber: num(atlas ? atlas.topics().length : 0), karte: num(D.n), neu: num([...TOPIC_BY_ID.values()].filter(x => x.kind === 'live').length || 0), pruef: num(testCount()) };
  for (const v of VIEWS) {
    const b = $(`#t-${v}`); b.replaceChildren(L[v], h('span', { class: 'c' }, counts[v]));
    b.setAttribute('aria-selected', String(v === view));
  }
  for (const l of ['de', 'fr']) $(`#l-${l}`).setAttribute('aria-pressed', String(UI.lang === l));
  $('#mode').textContent = API.live ? L.live : L.static;
  $('#fixture').hidden = SRC['meta.json'] !== 'data-fixture/';
  $('#fixture').textContent = L.fixture;
  $('#build').replaceChildren();
  // fact line: affairs, parliaments, scored share, build, last night's new rows, pending rows
  // «letzte Nacht: 412 neu · 8 min»; nothing when the night added no rows
  const ng = m.nightly || null, nRows = ng ? (ng.new_rows ?? null) : (API.metrics && (API.metrics.rows_last_night ?? API.metrics.new_rows));
  const night = nRows ? [`${num(nRows)} ${L.newW}${ng && ng.wall_min != null ? ` · ${Math.floor(ng.wall_min)} min` : ''}`, `${L.night}:`, true] : null;
  const items = [
    [num(m.affairs ?? D.n), L.affairs],
    [num(m.parliaments ?? D.bodies.length), L.parls],
    [num(m.please_check ?? 0), L.pendingAll],
    [pct(m.scored_share), `${L.scored} (APS)`],
    m.dig_scored != null ? [num(m.dig_scored), `${L.scored} (${(TOPIC_BY_ID.get('adhoc/digitalisierung') || { names: { de: 'Digitalisierung', fr: 'numérique' } }).names[UI.lang]})`] : null,
    night,
  ].filter(Boolean);
  $('#facts').replaceChildren(...items.map(([v, k, pre]) => h('span', {}, pre ? `${k} ` : '', h('b', {}, v), pre ? '' : ` ${k}`)));
  fitFacts();
  // footer: provenance + keys
  const gen = (m.generated_at || '').replace('T', ' ').slice(0, 16);
  $('#prov').textContent = [`${L.prov1}, Export ${gen} UTC`, `${L.engine} ${m.model || ''}, Build ${m.build_short || String(m.build || '').slice(-8)}`, `Querschnitt ${m.version || ''}`, L.geo].join(' · ');
  $('#keys').replaceChildren(...L.keys.map(([k, v]) => h('span', {}, h('kbd', {}, k), ` ${v}`)));
}

// the fact line stays one line: drop items from the end until it fits
function fitFacts() {
  const el = $('#facts'); if (!el) return;
  for (const x of el.children) x.hidden = false;
  const kids = [...el.children];
  const wraps = () => el.scrollWidth > el.clientWidth + 1;
  for (let k = kids.length - 1; k > 0 && wraps(); k--) kids[k].hidden = true;
}
addEventListener('resize', () => fitFacts());

function show(v) {
  view = v;
  document.body.classList.toggle('v-ueber', v === 'ueber');
  for (const x of VIEWS) { $(`#v-${x}`).hidden = x !== v; $(`#t-${x}`).setAttribute('aria-selected', String(x === v)); }
  if (v === 'pruef') renderPruef($('#v-pruef'));
  if (v === 'ueber') atlas.render();
  if (v === 'anb') renderAnb($('#v-anb'));
  if (v === 'neu' && !neu) neu = new Neu($('#v-neu'));
  if (v === 'neu' && neu) neu.board.refresh();
  writeHash();
}
const board = () => (view === 'karte' ? karte : view === 'neu' && neu ? neu.board : null);

// ---------------------------------------------------------------- hash state
function writeHash() {
  let s = `#${view}`;
  if (view === 'karte' && karte) {
    const S = karte.S, p = new URLSearchParams();
    if (karte.tp) p.set('t', karte.tp.id);
    if (S.sel != null) p.set('a', S.sel);
    if (S.body) p.set('p', S.body);
    if (S.brush) p.set('w', S.brush.join('-'));
    if (S.mode === 'pult') { p.set('m', 'pult'); p.set('tab', S.tab); if (S.pw != null) p.set('pw', S.pw); }
    if (S.f.q) p.set('q', S.f.q);
    if (karte.mapMode === 'matrix') p.set('v', 'matrix');
    s += `?${p}`;
  }
  history.replaceState(null, '', s);
}
function readHash() {
  const [v, q] = location.hash.slice(1).split('?');
  const p = new URLSearchParams(q || '');
  return { view: VIEWS.includes(v) ? v : 'ueber', p };
}

// ---------------------------------------------------------------- keyboard
function keys(e) {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const tg = e.target, typing = tg && (tg.tagName === 'INPUT' || tg.tagName === 'TEXTAREA' || tg.tagName === 'SELECT');
  if (typing) { if (e.key === 'Escape') tg.blur(); return; }
  const b = board(), k = e.key;
  if (k === 'd' || k === 'f') { setLang(k === 'd' ? 'de' : 'fr'); e.preventDefault(); return; }
  if (k === 'm') { show('karte'); return; }
  if (k === 'a') { show('ueber'); return; }
  if (k === 'i') { show('anb'); return; }
  if (k === 'n') { show('neu'); return; }
  if (k === 'b') { show('pruef'); return; }
  if (!b) return;
  if (b.corr && /^[0-9]$/.test(k)) { b.pickCorrection(+k); e.preventDefault(); return; }
  if (k === 'j' || k === 'ArrowDown') { b.step(1); e.preventDefault(); }
  else if (k === 'k' || k === 'ArrowUp') { b.step(-1); e.preventDefault(); }
  else if (k === '1') b.decide('confirmed');
  else if (k === '2') b.decide('rejected');
  else if (k === '0') b.decide('skip');
  else if (k === 'u') b.decide('undo');
  else if (k === 'l' && b.pultOn) b.setMode(b.S.mode === 'pult' ? 'list' : 'pult');
  else if (k === '/') { b.q.focus(); e.preventDefault(); }
  else if (k === 't' && b.picker) { b.picker.focus(); e.preventDefault(); }
  else if (k === 'e') b.exportCsv();
  else if (k === 'x' && b.modeEl) b.setMapMode(b.mapMode === 'matrix' ? 'map' : 'matrix');
  else if (k === 'Enter' && b.S.sel == null) b.step(1);
  else if ((k === '[' || k === ']') && b.S.mode === 'pult') b.stepWeek(k === '[' ? -1 : 1);
  else if (k === 'Escape') { // never resets the period
    if (b.corr || b.pend) { b.corr = null; b.pend = null; const r = D.rowOf.get(b.S.sel); if (r != null) b.stateLine(r); }
    else if (b.S.sel != null) b.select(null);
    else if (b.S.body && !(b.tp && b.tp.scope)) { b.S.body = null; b.refresh(); }
  }
}

// ---------------------------------------------------------------- boot
async function boot() {
  try { const l = localStorage.getItem('qs.lang'); if (l === 'fr' || l === 'de') UI.lang = l; } catch (e) { /* */ }
  const qlang = new URLSearchParams(location.search).get('lang'); if (qlang === 'fr' || qlang === 'de') UI.lang = qlang;
  document.documentElement.lang = UI.lang;
  const [, ok] = await Promise.all([load(), probeApi()]);
  if (API.live) {
    await syncDecisions();
    setInterval(async () => { if (await syncDecisions() && karte) { karte.refresh(); } }, 60000);
  }
  loadSaved();
  const { view: v0, p } = readHash();
  const tp = (p.get('t') && TOPIC_BY_ID.get(p.get('t'))) || findTopic('Digitalisierung') || [...TOPIC_BY_ID.values()][0];
  karte = new Board($('#v-karte'), { topic: tp, onChange: () => writeHash() });
  atlas = new Atlas($('#v-ueber'), {
    openTopic: x => { karte.S.brush = null; karte.S.mode = 'list'; show('karte'); karte.setTopic(x); },
    openAffair: i => { const c = D.c; const x = c.df[i] ? TOPIC_BY_ID.get('adhoc/digitalisierung') : (c.ch[i] >= 0 ? TOPIC_BY_ID.get(D.scheme.chapters[c.ch[i]].code) : karte.tp); karte.S.brush = null; show('karte'); karte.setTopic(x); karte.select(c.id[i]); } });
  if (p.get('p')) karte.S.body = p.get('p');
  if (p.get('w')) { const [a, b] = p.get('w').split('-').map(Number); if (b >= a) karte.S.brush = [a, b]; }
  else if (tp.scoredDays) karte.S.brush = [Math.floor((tp.scoredDays[0] - D.w0) / 7), Math.floor((tp.scoredDays[1] - D.w0) / 7)];
  if (p.get('m') === 'pult') { karte.S.mode = 'pult'; karte.S.tab = p.get('tab') || 'neu'; if (p.get('pw')) { karte.S.pw = +p.get('pw'); karte.S.pwFor = karte.tp.id; } }
  if (p.get('q')) { karte.S.f.q = p.get('q'); karte.q.value = p.get('q'); }
  karte.refresh();
  if (p.get('v') === 'matrix') karte.setMapMode('matrix');
  if (p.get('a')) karte.select(+p.get('a')); else karte.renderCase();
  for (const x of VIEWS) $(`#t-${x}`).addEventListener('click', () => show(x));
  $('#l-de').addEventListener('click', () => setLang('de'));
  $('#l-fr').addEventListener('click', () => setLang('fr'));
  document.addEventListener('keydown', keys);
  renderShell();
  show(v0);
  document.body.classList.remove('loading');
  window.__qs = { D, karte, API }; // for the headless checks in dev/
}
boot().catch(e => {
  console.error(e);
  const el = document.getElementById('facts');
  if (el) { el.innerHTML = ''; el.append(Object.assign(document.createElement('span'), { className: 'sig', textContent: String(e.message || e) })); }
});
