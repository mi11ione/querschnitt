// Anbindung: how Querschnitt lands in OpenParlData — the topics table, the Apache Hop load, the /changes feed, last
// night's run and the compose footprint. Everything comes from app/data/integration.json (dev/make_integration.py) and
// meta.json; /changes is live when the API answers, otherwise the stored sample marked «Beispiel».
import { D, API, SRC } from './data.js';
import { h, t, UI, num, pct } from './util.js';
import { rankList, bindTips } from './viz.js';

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
  // (2) the Hop pipeline
  const right = h('div', { class: 'anb-col' });
  const steps = h('ol', { class: 'hop' });
  I.hop.steps.forEach((st, k) => {
    const sk = I.hop.skips.filter(x => x.after === st.name);
    steps.append(h('li', {}, h('span', { class: 'hs' }, st.name), h('span', { class: 'ht' }, st.type), sk.length ? h('span', { class: 'hk' }, sk.map(x => `↳ ${x.name}`).join(' · ')) : ''));
  });
  right.append(h('h2', {}, L.anbHop), h('p', { class: 'tm mono dim' }, `Apache Hop · ${I.hop.file}`), steps,
    h('pre', { class: 'run' }, I.hop.run || ''), h('p', { class: 'tm mono dim' }, I.hop.readme));
  // (3) /changes
  const ch = h('div', { class: 'anb-sec' }, h('h2', {}, 'GET /changes?after='));
  let feed = null;
  if (API.live) { try { const r = await fetch(`${API.base}/changes?after=0&limit=3`); if (r.ok) feed = await r.json(); } catch (e) { /* stored */ } }
  const rows = feed ? (feed.rows || []).slice(0, 3) : I.changes.rows;
  ch.append(h('p', { class: 'tm mono' }, feed ? h('b', {}, 'live') : h('span', { class: 'dim' }, L.anbSample),
    ` · total ${num(feed ? feed.total : I.changes.total)}`, feed && feed.next ? ` · next ${feed.next}` : feed ? '' : ` · ${I.changes.file}`));
  ch.append(h('div', { class: 'tw' }, h('table', { class: 'anb-t' }, h('thead', {}, h('tr', {}, ['affair_id', 'scheme', 'code', 'p', 'lane', 'provenance', 'valid_from'].map(k => h('th', {}, k)))),
    h('tbody', {}, rows.map(r => h('tr', {}, [r.affair_id, r.scheme || r.scheme_key, r.code, r.p, r.lane, r.provenance, String(r.valid_from || '').replace('T', ' ').slice(0, 16)].map(v => h('td', { class: 'mono' }, v == null ? '–' : String(v)))))))));
  right.append(ch);
  // (4) last night
  const ng = m.nightly;
  // truncated, never rounded up (drain minutes at 0.1, USD at 0.0001); the cut is shown when the endpoint was down
  const tr = (v, d) => Math.floor(v * 10 ** d) / 10 ** d;
  if (ng) right.append(h('div', { class: 'anb-sec' }, h('h2', {}, L.night),
    h('p', { class: 'tm mono' }, `${ng.date} · OPD-Export ${String(ng.opd_export_generated || '').replace('T', ' ').slice(0, 16)} · ${L.anbNew} ${num(ng.new_affairs ?? 0)} · ${L.anbQueue} ${num(ng.pending_after_cut ?? ng.pending ?? 0)} → ${num(ng.pending_after_drain ?? 0)} · ${L.anbDrain} ${ng.drain_minutes != null ? tr(ng.drain_minutes, 1) : '–'} min · USD ${ng.usd != null ? tr(Number(ng.usd), 4).toFixed(4) : '–'}${ng.wall_min ? ` · ${num(Math.floor(ng.wall_min))} min` : ''}`),
    ng.endpoint_cut_first_pass ? h('p', { class: 'tm mono dim', 'data-tip': ng.cut_reason || '' }, L.anbCut) : ''));
  // (5) footprint
  const F = I.footprint;
  if (F) {
    const mx = Math.max(F.full_mib || 0, F.lite_mib || 0, 1);
    right.append(h('div', { class: 'anb-sec' }, h('h2', {}, L.anbFoot),
      rankList([{ label: `full (${Object.keys(F.containers).filter(k => k !== 'nightly-lite').join(' + ')})`, v: F.full_mib / mx, tone: 'ink', value: `≈ ${num(Math.floor(F.full_mib))} MiB` },
        { label: 'lite (nightly-lite)', v: (F.lite_mib || 0) / mx, tone: 'grey', value: `≈ ${num(Math.floor(F.lite_mib || 0))} MiB` }]),
      h('p', { class: 'tm mono' }, `image ${num(F.image_mb)} MB · `, F.run_url ? h('a', { href: F.run_url, target: '_blank', rel: 'noopener' }, `CI run ${F.run_id} ↗`) : '', ` · ${F.file}`)));
  }
  wrap.append(tb, right);
  bindTips(wrap);
}
