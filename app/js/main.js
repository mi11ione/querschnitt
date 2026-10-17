// Shell: one bar (wordmark, the views, export date or «live», DE/FR), one mono fact line, the view, provenance footer.
import { D, SRC, API, load, probeApi, TOPIC_BY_ID, findTopic, syncDecisions, parlCount } from './data.js';
import { $, h, t, UI, num } from './util.js';
import { Board } from './board.js';
import { Neu, loadSaved } from './neu.js';
import { renderPruef } from './pruef.js';
import { Atlas } from './atlas.js';
import { renderAnb } from './anb.js';
import { Woche } from './woche.js';

const VIEWS = ['woche', 'ueber', 'karte', 'neu', 'pruef', 'anb'];
let view = 'woche', karte = null, neu = null, atlas = null, woche = null;
// every view but Neueste Woche waits for the full data (D.full) and the boards built on it
let READY_DONE = false, readyOk;
const READY = new Promise(r => { readyOk = r; });

function setLang(l) {
  UI.lang = l; document.documentElement.lang = l;
  try { localStorage.setItem('qs.lang', l); } catch (e) { /* */ }
  renderShell();
  if (karte) karte.relang();
  if (neu) neu.relang();
  if (view === 'pruef') renderPruef($('#v-pruef'));
  if (view === 'ueber') atlas.render();
  if (view === 'woche') woche.render();
  if (view === 'anb') renderAnb($('#v-anb'));
}

function renderShell() {
  const L = t(), m = D.meta;
  // bar
  // tab names only: counts beside them («Überblick 29», «Prüfstand 21») read as unexplained codes to a newcomer
  for (const v of VIEWS) {
    const b = $(`#t-${v}`); b.replaceChildren(L[v]);
    b.setAttribute('aria-selected', String(v === view));
  }
  for (const l of ['de', 'fr']) $(`#l-${l}`).setAttribute('aria-pressed', String(UI.lang === l));
  // static build: the export's date in words, what «static» means only on hover; live: «live»
  const exp = (m.generated_at || '').slice(0, 10);
  $('#mode').textContent = API.live ? L.live : L.snap(exp ? `${exp.slice(8, 10)}.${exp.slice(5, 7)}.${exp.slice(0, 4)}` : '–');
  if (API.live) $('#mode').removeAttribute('title'); else $('#mode').title = L.snapTip;
  $('#fixture').hidden = SRC['meta.json'] !== 'data-fixture/';
  $('#fixture').textContent = L.fixture;
  $('#build').replaceChildren();
  // fact line: affairs, parliaments, the affairs waiting for a person (APS lane); the same counts as D.tally everywhere
  const T = D.tally;
  const items = [
    [num(T.affairs), L.affairs],
    [num(parlCount()[0]), L.parls(parlCount()[1])],
    [num(T.check), L.pendingAll],
  ].filter(Boolean);
  $('#facts').replaceChildren(...items.map(([v, k, pre]) => h('span', {}, pre ? `${k} ` : '', h('b', {}, v), pre ? '' : ` ${k}`)));
  fitFacts();
  // footer: provenance + keys
  const gen = (m.generated_at || '').replace('T', ' ').slice(0, 16);
  $('#prov').textContent = [`${L.prov1}, Export ${gen} UTC`, `${L.engine} ${m.model || ''}, Build ${m.build_short || String(m.build || '').slice(-8)}`, L.geo].join(' · ');
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
  if (!READY_DONE && v !== 'woche') { READY.then(() => show(v)); return; }
  view = v;
  document.body.classList.toggle('v-ueber', v === 'woche');
  $('#keys').hidden = !(v === 'karte' || v === 'neu');   // the keys act on the list and the Pult only
  for (const x of VIEWS) { $(`#v-${x}`).hidden = x !== v; $(`#t-${x}`).setAttribute('aria-selected', String(x === v)); }
  if (v === 'pruef') renderPruef($('#v-pruef'));
  if (v === 'ueber') atlas.render();
  if (v === 'woche') woche.render();
  if (v === 'anb') renderAnb($('#v-anb'));
  if (v === 'neu' && !neu) neu = new Neu($('#v-neu'));
  if (v === 'neu' && neu) { neu.board.refresh(); neu.shown(); }
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
  if (view === 'woche' && woche && woche.hashQ()) s += `?${woche.hashQ()}`;
  if (view === 'neu' && neu && neu.limit) s += `?limit=${neu.limit}`; // a capped live run keeps its cap in the link
  history.replaceState(null, '', s);
}
function readHash() {
  const [v, q] = location.hash.slice(1).split('?');
  const p = new URLSearchParams(q || '');
  return { view: VIEWS.includes(v) ? v : 'woche', p };
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
  if (k === 'w') { show('woche'); return; }
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
  const { view: v0, p } = readHash();
  // Neueste Woche can render from the first-screen slice; its links carry the affair id, the topic id and the week's
  // Monday (day number), so they still hold once the full data has replaced the slice
  const wk = day => Math.floor((day - D.w0) / 7);
  const toWeek = (x, w) => { karte.S.mode = 'list'; show('karte'); karte.setTopic(x); karte.S.brush = [w, w]; karte.refresh(); };
  woche = new Woche($('#v-woche'), {
    openTopic: (id, day) => READY.then(() => toWeek(TOPIC_BY_ID.get(id), wk(day))),
    openAffair: (aid, id, day) => READY.then(() => { toWeek(TOPIC_BY_ID.get(id), wk(day)); karte.select(aid); }) });
  if (v0 === 'woche') woche.setDate(p.get('d'));
  for (const x of VIEWS) $(`#t-${x}`).addEventListener('click', () => show(x));
  $('#l-de').addEventListener('click', () => setLang('de'));
  $('#l-fr').addEventListener('click', () => setLang('fr'));
  document.addEventListener('keydown', keys);
  // a link pasted into the address bar (make demo prints one per pitch beat) changes only the hash: open it as a fresh load;
  // the app itself writes the hash with replaceState, which fires no hashchange
  addEventListener('hashchange', () => location.reload());
  const early = D.partial && v0 === 'woche';
  if (early) { renderShell(); show('woche'); document.body.classList.remove('loading'); }
  const w0h = D.w0;
  await D.full;
  woche.rebase(w0h);
  loadSaved();
  // an affair link without a topic (#karte?a=96375) opens on the affair's own topic, as from the Überblick: Digitalisierung
  // when it is flagged, else its APS chapter
  const ownTopic = () => {
    const r = p.get('a') ? D.rowOf.get(+p.get('a')) : null; if (r == null) return null;
    return D.c.df[r] ? TOPIC_BY_ID.get('adhoc/digitalisierung') : D.c.ch[r] >= 0 && D.scheme.chapters[D.c.ch[r]] ? TOPIC_BY_ID.get(D.scheme.chapters[D.c.ch[r]].code) : null;
  };
  const tp = (p.get('t') && TOPIC_BY_ID.get(p.get('t'))) || ownTopic() || findTopic('Digitalisierung') || [...TOPIC_BY_ID.values()][0];
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
  READY_DONE = true; readyOk();
  renderShell();
  if (!early || view !== 'woche') show(early ? view : v0);
  document.body.classList.remove('loading');
  window.__qs = { D, karte, API }; // for the headless checks in dev/
}
boot().catch(e => {
  console.error(e);
  const el = document.getElementById('facts');
  if (el) { el.innerHTML = ''; el.append(Object.assign(document.createElement('span'), { className: 'sig', textContent: String(e.message || e) })); }
});
