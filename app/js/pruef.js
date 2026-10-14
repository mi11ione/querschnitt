// Prüfstand: one ruled table per test (human labels first), one coverage–precision chart (black line, red dot at the
// shipped operating point).
import { D, SRC } from './data.js';
import { h, s, t, UI, num, pct, p3 } from './util.js';
import { bindTips } from './viz.js';

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
      h('p', { class: 'tm' }, [r0.split ? `${L.split}: ${(fr && r0.split_fr) || r0.split}` : '', r0.file ? `${L.file}: ` : ''].filter(Boolean).join(' · '), file));
    const tb = h('table', {}, h('colgroup', {}, h('col', { class: 'c-d' }), h('col'), h('col'), h('col'), h('col')),
      h('thead', {}, h('tr', {}, h('th', {}, L.design), h('th', { class: 'n' }, 'n'), h('th', {}, L.result), h('th', {}, L.ci), h('th', {}, L.baseline))));
    const body = h('tbody');
    for (const r of rs) {
      const ci = Array.isArray(r.interval) ? `[${r.interval.map(v => typeof v === 'number' ? v.toFixed(3) : v).join(', ')}]` : (r.interval || '–');  // bounds are stored at 3 decimals (truncated / outward)
      const ship = r === order[0][1][0]; // the production row leads the first human-label table
      body.append(h('tr', { class: ship ? 'ship' : '' }, h('td', {}, (fr && r.design_fr) || r.design), h('td', { class: 'n' }, num(r.n)), h('td', { class: 'res' }, String((fr && r.result_fr) || r.result)),
        h('td', { class: 'res' }, ci), h('td', { class: 'base' }, (fr && r.baseline_fr) || r.baseline || '–')));
    }
    tb.append(body); sec.append(h('div', { class: 'tw' }, tb)); left.append(sec);
  }
  if (SRC['pruefstand.json'] === 'data-fixture/') left.append(h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `pruefstand.json ${L.fromFixture}`));
  if (P.curve) {
    // held out first: the S25 curve (black, red dot at the shipped lane); the design-set curve stays as a grey reference
    const hc = D.conf && D.conf.curve, cv = hc ? { ...hc, ref: P.curve.points, refLabel: [P.curve.test, P.curve.test_fr] } : { ...P.curve };
    right.append(chart(cv));
  }
  if (D.conf) right.append(D.conf.lanes_tau ? lanesTau(D.conf.lanes_tau) : lanesBar(D.conf), confusion(D.conf));
  bindTips(right);
}

function chart(cv) {
  const L = t(), fr = UI.lang === 'fr';
  const W = 400, H = 300, ml = 44, mr = 12, mt = 12, mb = 36;
  const pts = cv.points || [];
  const ys = pts.concat(cv.ref || []).map(p => p[1]);
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
  if (cv.ref) svg.append(s('path', { class: 'ln ref', d: cv.ref.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join('') }));
  svg.append(s('path', { class: 'ln', d: pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join('') }));
  if (cv.op2) {
    const ox = X(cv.op2.coverage), oy = Y(cv.op2.precision);
    svg.append(s('circle', { class: 'op2', cx: ox, cy: oy, r: 4, tabindex: '0', 'data-tip': `${cv.op2.label_de && UI.lang === 'fr' ? cv.op2.label_fr : cv.op2.label_de}: ${pct(cv.op2.coverage)} · ${p3(cv.op2.precision)}` }));
  }
  if (cv.op) {
    const ox = X(cv.op.coverage), oy = Y(cv.op.precision);
    svg.append(s('circle', { class: 'op', cx: ox, cy: oy, r: 5 }));
    const tx = s('text', { x: ox + 8, y: oy - 9, class: 'opl' }); tx.textContent = `${pct(cv.op.coverage)} · ${p3(cv.op.precision)}`; svg.append(tx);
  }
  return h('div', { class: 'chart' },
    h('h3', {}, L.cpTitle),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 12px' }, `${(fr && cv.test_fr) || cv.test || ''} · n ${num(cv.n)}`),
    svg,
    cv.op ? h('p', { class: 'tm mono', style: 'font-size:12px;margin-top:8px' }, `${(fr ? cv.op.label_fr : cv.op.label_de) || ''}: ${L.cpX} ${pct(cv.op.coverage)}, ${L.cpY} ${p3(cv.op.precision)} (n ${num(cv.op.n)})`) : '',
    cv.ref ? h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `${L.refCurve}: ${(fr && cv.refLabel[1]) || cv.refLabel[0]}`) : '',
    cv.file ? h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `${L.file}: ${cv.file}`) : '');
}

// the two lanes of the shipped design as one split bar: width = share of affairs, dark part = precision in that lane
function lanesBar(cf) {
  const L = t(), l = cf.lanes, n = l.agree_n + l.disagree_n, a = l.agree_n / n;
  const seg = (w, k, nn, cls, lab) => h('span', { class: `lseg ${cls}`, style: `width:${w * 100}%`, tabindex: '0', 'data-tip': `${lab} · ${pct(nn / n)} (n ${num(nn)}) · ${L.cpY} ${p3(k / nn)}` },
    h('span', { class: 'lok', style: `width:${(k / nn) * 100}%` }));
  return h('div', { class: 'lanes' }, h('h3', {}, L.lanesT),
    h('div', { class: 'lbar' }, seg(a, l.agree_k, l.agree_n, 'ag', L.agree), seg(1 - a, l.disagree_k, l.disagree_n, 'dis', L.disagree)),
    h('div', { class: 'llab' }, h('span', { style: `width:${a * 100}%` }, `${L.agree} ${pct(a)} · ${p3(l.agree_k / l.agree_n)}`),
      h('span', { style: `width:${(1 - a) * 100}%` }, h('span', { class: 'rtick' }), ` ${L.disagree} · ${p3(l.disagree_k / l.disagree_n)}`)),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:6px 0 0' }, `${L.cpY}: ${L.dark}; n ${num(n)} · ${cf.design}`));
}

// confusion: rows = APS editors' chapter, columns = Querschnitt's; cell grey = share of the row; diagonal outlined
function confusion(cf) {
  const L = t(), m = cf.m, K = m.length, chs = D.scheme.chapters;
  const nm = k => chs[k] ? (UI.lang === 'fr' ? chs[k].fr || chs[k].de : chs[k].de) : String(k);
  const rows = [...Array(K).keys()].filter(r => m[r].some(v => v) || m.some(row => row[r]));
  const n = rows.length, cs = 12, LW = 0, W = n * cs, H = n * cs;
  const svg = s('svg', { viewBox: `-1 -1 ${W + 2} ${H + 2}`, class: 'cf', role: 'img', 'aria-label': L.confusion });
  rows.forEach((r, ri) => {
    const tot = m[r].reduce((a, b) => a + b, 0);
    rows.forEach((c, cj) => {
      const v = m[r][c]; const sh = tot ? v / tot : 0;
      const cls = v ? Math.min(5, 1 + Math.floor(sh * 5)) : 0;
      svg.append(s('rect', { x: cj * cs, y: ri * cs, width: cs - 1, height: cs - 1, style: `fill:var(--r${cls})`, class: r === c ? 'dia' : 'off',
        'data-tip': `${L.gold}: ${nm(r)} → ${L.pred}: ${nm(c)} · ${num(v)} ${L.of} ${num(tot)}${tot ? ` (${pct(sh)})` : ''}` }));
    });
  });
  return h('div', { class: 'cfw' }, h('h3', {}, (UI.lang === 'fr' ? cf.title_fr : cf.title_de) || L.confusion),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 8px' }, `${L.rowsGold} · ${L.colsPred} · n ${num(cf.n)} · top-1 ${p3(cf.correct / cf.n)}`), svg);
}

// the two lanes of the shipped rule as one split bar: width = share of affairs, dark part = precision in that lane
function lanesTau(lt) {
  const L = t(), a = lt.pass_.coverage;
  const seg = (w, x, cls, lab) => h('span', { class: `lseg ${cls}`, style: `width:${w * 100}%`, tabindex: '0', 'data-tip': `${lab} · ${pct(w)} (n ${num(x.n)}) · ${L.cpY} ${p3(x.precision)} [${x.ci.join(', ')}]` },
    h('span', { class: 'lok', style: `width:${x.precision * 100}%` }));
  return h('div', { class: 'lanes' }, h('h3', {}, L.lanesT),
    h('div', { class: 'lbar' }, seg(a, lt.pass_, 'ag', L.shipped), seg(1 - a, lt.check, 'dis', L.laneCheck)),
    h('div', { class: 'llab' }, h('span', { style: `width:${a * 100}%` }, `${L.shipped} · ${pct(a)} · ${p3(lt.pass_.precision)}`),
      h('span', { style: `width:${(1 - a) * 100}%` }, h('span', { class: 'rtick' }), ` ${L.laneCheck} · ${p3(lt.check.precision)}`)),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:6px 0 0' }, `${L.cpY}: ${L.dark}; n ${num(lt.pass_.n + lt.check.n)} · D4 · ${lt.file}`));
}
