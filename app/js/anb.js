// Anbindung: how Querschnitt lands in OpenParlData — the topics table, last night's run with the measured cost on one
// line, the Apache Hop load (path and command), the /changes feed and the repository links. Everything comes from
// app/data/integration.json (dev/make_integration.py) and meta.json; /changes is live when the API answers, otherwise
// the stored sample marked «Beispiel».
import { D, API, SRC } from './data.js';
import { h, t, UI, num } from './util.js';
import { bindTips } from './viz.js';

// the short cost unit for the night line (the long wording stays in the tooltip)
const PER = { de: n => `pro ${n} Geschäfte`, fr: n => `pour ${n} objets` };

let INT = null;
export async function loadIntegration() {
  if (INT) return INT;
  for (const b of [SRC['meta.json'] || 'data/', 'data/', 'data-fixture/']) {
    try { const r = await fetch(`${b}integration.json`, { cache: 'no-cache' }); if (r.ok) { INT = await r.json(); return INT; } } catch (e) { /* next */ }
  }
  return null;
}

export async function renderAnb(root) {
  const L = t(), I = await loadIntegration(), m = D.meta;
  root.replaceChildren();
  if (!I) { root.append(h('p', { class: 'empty' }, '–')); return; }
  const wrap = h('div', { class: 'anb' }); root.append(wrap);
  // (1) the topics table
  const tb = h('div', { class: 'anb-col' }, h('h2', {}, L.anbTable), h('p', { class: 'tm mono dim' }, `topics · ${I.table.columns.length} ${L.anbCols} · ${I.table.file}`),
    h('p', { class: 'anb-key' }, h('span', { class: 'gk machine' }), L.anbMachine, h('span', { class: 'gk decision' }), L.anbDecision));
  const ul = h('div', { class: 'anb-cols' });
  for (const c of I.table.columns) ul.append(h('div', { class: `ac ${c.group}` }, h('span', { class: 'an' }, c.name), h('span', { class: 'at' }, c.type), h('span', { class: 'ao' }, c.note || '')));
  tb.append(ul);
  // (2) last night on one line: date · new affairs · minutes · measured cost per 1,000 affairs (eval/cost/results.json)
  const right = h('div', { class: 'anb-col' });
  const ng = m.nightly, C = I.cost;
  // truncated, never rounded up (USD at 0.001); the epsilon keeps 0.57 at 0.57
  const tr = (v, d) => Math.floor(v * 10 ** d + 1e-9) / 10 ** d;
  const dmy = iso => String(iso || '').slice(0, 10).split('-').reverse().join('.');
  const cost = C && C.usd_per_1000_affairs != null ? h('span', { 'data-tip': `${L.anbCost(num(1000))} · ${C.file}` },
    `USD ${tr(Number(C.usd_per_1000_affairs), 3).toFixed(3)} ${PER[UI.lang === 'fr' ? 'fr' : 'de'](num(1000))}`) : '';
  const parts = ng ? [dmy(ng.date), `${L.anbNew} ${num(ng.new_affairs ?? 0)}`, ng.wall_min ? `${num(Math.floor(ng.wall_min))} min` : ''].filter(Boolean) : [];
  if (parts.length || cost) right.append(h('div', { class: 'anb-sec anb-first' }, ng ? h('h2', {}, L.night) : '',
    h('p', { class: 'tm mono' }, parts.join(' · '), parts.length && cost ? ' · ' : '', cost)));
  // (3) the Hop load: the pipeline file and the command
  right.append(h('div', { class: 'anb-sec' }, h('h2', {}, L.anbHop), h('p', { class: 'tm mono dim' }, `Apache Hop · ${I.hop.file}`),
    h('pre', { class: 'run' }, I.hop.run || ''), h('p', { class: 'tm mono dim' }, I.hop.readme)));
  // (4) /changes
  const ch = h('div', { class: 'anb-sec' }, h('h2', {}, 'GET /changes?after='));
  let feed = null;
  if (API.live) { try { const r = await fetch(`${API.base}/changes?after=0&limit=3`); if (r.ok) feed = await r.json(); } catch (e) { /* stored */ } }
  const rows = feed ? (feed.rows || []).slice(0, 3) : I.changes.rows;
  ch.append(h('p', { class: 'tm mono' }, feed ? h('b', {}, 'live') : h('span', { class: 'dim' }, L.anbSample),
    ` · total ${num(feed ? feed.total : I.changes.total)}`, feed && feed.next ? ` · next ${feed.next}` : feed ? '' : ` · ${I.changes.file}`));
  ch.append(h('div', { class: 'tw' }, h('table', { class: 'anb-t' }, h('thead', {}, h('tr', {}, ['affair_id', 'scheme', 'code', 'p', 'lane', 'provenance', 'valid_from'].map(k => h('th', {}, k)))),
    h('tbody', {}, rows.map(r => h('tr', {}, [r.affair_id, r.scheme || r.scheme_key, r.code, r.p, r.lane, r.provenance, String(r.valid_from || '').replace('T', ' ').slice(0, 16)].map(v => h('td', { class: 'mono' }, v == null ? '–' : String(v)))))))));
  right.append(ch);
  // (5) the repository: code and site
  const RP = I.repo;
  if (RP) tb.append(h('div', { class: 'anb-sec anb-repo' }, h('h2', {}, L.anbRepo),
    h('div', { class: 'anb-repo-b' }, h('dl', { class: 'tm mono' }, h('dt', {}, L.anbCode), h('dd', {}, h('a', { href: RP.url, target: '_blank', rel: 'noopener' }, RP.url)),
      h('dt', {}, L.anbSite), h('dd', {}, h('a', { href: RP.site, target: '_blank', rel: 'noopener' }, RP.site))))));
  wrap.append(tb, right);
  bindTips(wrap);
}
