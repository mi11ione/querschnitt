// Anbindung: how Querschnitt lands in OpenParlData — last night's run and the measured cost (top right, in the first
// screen), the topics table, the Apache Hop load, the /changes feed, the compose footprint, and the repository with its
// QR code. Everything comes from app/data/integration.json (dev/make_integration.py) and meta.json; /changes is live when
// the API answers, otherwise the stored sample marked «Beispiel».
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
  // (2) last night, then the measured cost per 1,000 affairs (eval/cost/results.json via integration.json)
  const right = h('div', { class: 'anb-col' });
  const ng = m.nightly, C = I.cost;
  // truncated, never rounded up (drain minutes at 0.1, USD at 0.0001 / 0.001); the epsilon keeps 0.57 at 0.57
  const tr = (v, d) => Math.floor(v * 10 ** d + 1e-9) / 10 ** d;
  const cost = C && C.usd_per_1000_affairs != null ? h('p', { class: 'tm mono anb-cost' }, h('b', {}, `USD ${tr(Number(C.usd_per_1000_affairs), 3).toFixed(3)}`),
    ` ${L.anbCost(num(1000))}`, h('span', { class: 'dim' }, ` · ${C.file}`)) : '';
  // the night's own record; a hand-written `note` (runs/nightly/last.json) replaces the queue figures it corrects. The
  // outage sentence only when the record names an outage (`cut_reason`); an even-day cut is the scheduled test cut
  const note = ng && ng.note ? (typeof ng.note === 'string' ? ng.note : ng.note[UI.lang] || ng.note.de) : '';
  const qline = r => `${L.anbQueue} ${num(r.pending_after_cut ?? r.pending ?? 0)} → ${num(r.pending_after_drain ?? 0)} · ${L.anbDrain} ${r.drain_minutes != null ? tr(r.drain_minutes, 1) : '–'} min · USD ${r.usd != null ? tr(Number(r.usd), 4).toFixed(4) : '–'}`;
  const dmy = iso => String(iso || '').slice(0, 10).split('-').reverse().join('.');
  // the last real outage (meta.nightly_outage, from eval/nightly/<date>.json), always on its own line
  const O = m.nightly_outage;
  const outage = O ? [h('p', { class: 'tm mono anb-out' }, `${L.anbOutage(dmy(O.date))} ${qline(O)}`),
    h('p', { class: 'tm mono dim', 'data-tip': O.cut_reason || '' }, L.anbCut)] : [];
  if (ng) right.append(h('div', { class: 'anb-sec anb-first' }, h('h2', {}, L.night),
    h('p', { class: 'tm mono' }, `${ng.date} · OPD-Export ${String(ng.opd_export_generated || '').replace('T', ' ').slice(0, 16)} · ${L.anbNew} ${num(ng.new_affairs ?? 0)}${note ? '' : ` · ${qline(ng)}`}${ng.wall_min ? ` · ${num(Math.floor(ng.wall_min))} min` : ''}`),
    note ? h('p', { class: 'tm mono dim' }, note) : '',
    ng.endpoint_cut_first_pass ? h('p', { class: 'tm mono dim', 'data-tip': ng.cut_reason || '' }, ng.cut_reason ? L.anbCut : L.anbSched) : '',
    ...(O && O.date !== ng.date ? outage : []), cost));
  else if (cost) right.append(h('div', { class: 'anb-sec anb-first' }, cost));
  // (3) the Hop pipeline
  const steps = h('ol', { class: 'hop' });
  I.hop.steps.forEach((st, k) => {
    const sk = I.hop.skips.filter(x => x.after === st.name);
    steps.append(h('li', {}, h('span', { class: 'hs' }, st.name), h('span', { class: 'ht' }, st.type), sk.length ? h('span', { class: 'hk' }, sk.map(x => `↳ ${x.name}`).join(' · ')) : ''));
  });
  right.append(h('div', { class: 'anb-sec' }, h('h2', {}, L.anbHop), h('p', { class: 'tm mono dim' }, `Apache Hop · ${I.hop.file}`), steps,
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
  // (5) footprint
  const F = I.footprint;
  if (F) {
    const mx = Math.max(F.full_mib || 0, F.lite_mib || 0, 1);
    right.append(h('div', { class: 'anb-sec' }, h('h2', {}, L.anbFoot),
      rankList([{ label: `full (${Object.keys(F.containers).filter(k => k !== 'nightly-lite').join(' + ')})`, v: F.full_mib / mx, tone: 'ink', value: `≈ ${num(Math.floor(F.full_mib))} MiB` },
        { label: 'lite (nightly-lite)', v: (F.lite_mib || 0) / mx, tone: 'grey', value: `≈ ${num(Math.floor(F.lite_mib || 0))} MiB` }]),
      h('p', { class: 'tm mono' }, `image ${num(F.image_mb)} MB · `, F.run_url ? h('a', { href: F.run_url, target: '_blank', rel: 'noopener' }, `CI run ${F.run_id} ↗`) : '', ` · ${F.file}`)));
  }
  // (6) the repository: URL, site, QR code (app/img/qr-repo.svg, written at build time by dev/qr.py;
  // 37 modules with the quiet zone at 148 px = 4 px a module)
  const RP = I.repo;
  if (RP) tb.append(h('div', { class: 'anb-sec anb-repo' }, h('h2', {}, L.anbRepo),
    h('div', { class: 'anb-repo-b' }, RP.qr ? h('img', { class: 'qr', src: RP.qr, width: 148, height: 148, alt: `${L.anbQr} ${RP.url}` }) : '',
      h('dl', { class: 'tm mono' }, h('dt', {}, L.anbCode), h('dd', {}, h('a', { href: RP.url, target: '_blank', rel: 'noopener' }, RP.url)),
        h('dt', {}, L.anbSite), h('dd', {}, h('a', { href: RP.site, target: '_blank', rel: 'noopener' }, RP.site))))));
  wrap.append(tb, right);
  bindTips(wrap);
}
