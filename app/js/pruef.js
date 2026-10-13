// Prüfstand: one ruled table per test (human labels first), one coverage–precision chart (black line, red dot at the
// shipped operating point).
import { D, SRC } from './data.js';
import { h, s, t, UI, num, pct, p3 } from './util.js';

export function testCount() {
  const P = D.pruef; if (!P) return 0;
  const rows = Array.isArray(P) ? P : P.rows || [];
  return new Set(rows.map(r => r.test)).size;
}

export function renderPruef(root) {
  const L = t(), P = D.pruef;
  root.replaceChildren();
  const wrap = h('div', { class: 'pr' }); root.append(wrap);
  const left = h('div', { class: 'pane' }), right = h('div', { class: 'pane' });
  wrap.append(left, right);
  if (!P) { left.append(h('p', { class: 'empty' }, '–')); return; }
  const rows = Array.isArray(P) ? P : P.rows || [];
  const fr = UI.lang === 'fr';
  const tests = new Map();
  for (const r of rows) { if (!tests.has(r.test)) tests.set(r.test, []); tests.get(r.test).push(r); }
  const order = [...tests.entries()].sort((a, b) => (a[1][0].gold === 'human' ? 0 : 1) - (b[1][0].gold === 'human' ? 0 : 1));
  let lastGold = null;
  for (const [name, rs] of order) {
    const r0 = rs[0];
    if (r0.gold && r0.gold !== lastGold) { left.append(h('p', { class: 'grp' }, r0.gold === 'human' ? L.human : r0.gold === 'judge' ? L.judge : r0.gold)); lastGold = r0.gold; }
    const file = r0.file ? (/^https?:/.test(r0.file) ? h('a', { href: r0.file, target: '_blank', rel: 'noopener' }, r0.file) : r0.file) : '';
    const sec = h('section', { class: 'test' },
      h('h3', {}, (fr && r0.test_fr) || name),
      h('p', { class: 'tm' }, [r0.split ? `${L.split}: ${r0.split}` : '', r0.file ? `${L.file}: ` : ''].filter(Boolean).join(' · '), file));
    const tb = h('table', {}, h('colgroup', {}, h('col', { class: 'c-d' }), h('col'), h('col'), h('col'), h('col')),
      h('thead', {}, h('tr', {}, h('th', {}, L.design), h('th', { class: 'n' }, 'n'), h('th', {}, L.result), h('th', {}, L.ci), h('th', {}, L.baseline))));
    const body = h('tbody');
    for (const r of rs) {
      const ci = Array.isArray(r.interval) ? `[${r.interval.join(', ')}]` : (r.interval || '–');
      body.append(h('tr', {}, h('td', {}, (fr && r.design_fr) || r.design), h('td', { class: 'n' }, num(r.n)), h('td', { class: 'res' }, String(r.result)),
        h('td', { class: 'res' }, ci), h('td', { class: 'base' }, r.baseline || '–')));
    }
    tb.append(body); sec.append(h('div', { class: 'tw' }, tb)); left.append(sec);
  }
  if (SRC['pruefstand.json'] === 'data-fixture/') left.append(h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `pruefstand.json ${L.fromFixture}`));
  if (P.curve) right.append(chart(P.curve));
}

function chart(cv) {
  const L = t(), fr = UI.lang === 'fr';
  const W = 400, H = 300, ml = 44, mr = 12, mt = 12, mb = 36;
  const pts = cv.points || [];
  const ys = pts.map(p => p[1]);
  const y0 = Math.max(0, Math.floor((Math.min(...ys, cv.op ? cv.op.precision : 1) - .05) * 10) / 10), y1 = 1;
  const X = v => ml + v * (W - ml - mr), Y = v => mt + (1 - (v - y0) / (y1 - y0)) * (H - mt - mb);
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': L.cpTitle });
  for (let v = 0; v <= 1.0001; v += .2) {
    svg.append(s('line', { class: 'gr', x1: X(v), x2: X(v), y1: mt, y2: H - mb }));
    const tx = s('text', { x: X(v), y: H - mb + 16, 'text-anchor': 'middle' }); tx.textContent = `${Math.round(v * 100)}`; svg.append(tx);
  }
  for (let v = y0; v <= 1.0001; v += .1) {
    svg.append(s('line', { class: 'gr', x1: ml, x2: W - mr, y1: Y(v), y2: Y(v) }));
    const tx = s('text', { x: ml - 6, y: Y(v) + 4, 'text-anchor': 'end' }); tx.textContent = v.toFixed(1); svg.append(tx);
  }
  svg.append(s('line', { class: 'ax', x1: ml, x2: W - mr, y1: H - mb, y2: H - mb }), s('line', { class: 'ax', x1: ml, x2: ml, y1: mt, y2: H - mb }));
  const xl = s('text', { x: W - mr, y: H - 4, 'text-anchor': 'end' }); xl.textContent = `${L.cpX} %`; svg.append(xl);
  svg.append(s('path', { class: 'ln', d: pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join('') }));
  if (cv.op) {
    const ox = X(cv.op.coverage), oy = Y(cv.op.precision);
    svg.append(s('circle', { class: 'op', cx: ox, cy: oy, r: 5 }));
    const tx = s('text', { x: ox + 9, y: oy + 18, class: 'opl' }); tx.textContent = `${pct(cv.op.coverage)} · ${p3(cv.op.precision)}`; svg.append(tx);
  }
  return h('div', { class: 'chart' },
    h('h3', {}, L.cpTitle),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 12px' }, `${(fr && cv.test_fr) || cv.test || ''} · n ${num(cv.n)}`),
    svg,
    cv.op ? h('p', { class: 'tm mono', style: 'font-size:12px;margin-top:8px' }, `${(fr ? cv.op.label_fr : cv.op.label_de) || ''}: ${L.cpX} ${pct(cv.op.coverage)}, ${L.cpY} ${p3(cv.op.precision)} (n ${num(cv.op.n)})`) : '',
    cv.file ? h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `${L.file}: ${cv.file}`) : '');
}
