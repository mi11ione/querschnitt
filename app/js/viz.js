// Small graphics in the register: hairline tracks, black for the shipped / selected value, greys for the rest,
// red only for a please-check tick. Inline SVG or plain boxes; one shared hover/focus tip.
import { h, s, num, pct, p3, t, UI } from './util.js';

// ---------------------------------------------------------------- tip: [data-tip] on hover and focus
let TIP = null;
export function bindTips(root) {
  if (!TIP) { TIP = h('div', { class: 'tip vtip', hidden: true, role: 'tooltip' }); document.body.append(TIP); }
  const show = (el, x, y) => {
    const tx = el.getAttribute('data-tip'); if (!tx) return;
    TIP.textContent = tx; TIP.hidden = false;
    const r = TIP.getBoundingClientRect();
    let left = x + 12, top = y + 14;
    if (left + r.width > innerWidth - 8) left = Math.max(8, x - r.width - 12);
    if (top + r.height > innerHeight - 8) top = Math.max(8, y - r.height - 12);
    TIP.style.left = `${left + scrollX}px`; TIP.style.top = `${top + scrollY}px`;
  };
  root.addEventListener('pointermove', e => { const el = e.target.closest && e.target.closest('[data-tip]'); if (el && root.contains(el)) show(el, e.clientX, e.clientY); else TIP.hidden = true; });
  root.addEventListener('pointerleave', () => { TIP.hidden = true; });
  root.addEventListener('focusin', e => { const el = e.target.closest && e.target.closest('[data-tip]'); if (el) { const r = el.getBoundingClientRect(); show(el, r.left, r.bottom - 10); } });
  root.addEventListener('focusout', () => { TIP.hidden = true; });
}

// grow bars on insertion (≤ 200 ms; the global reduced-motion rule turns transitions off)
export function grow(el) {
  const bars = el.querySelectorAll('.gb');
  for (const b of bars) { b.style.transform = 'scaleX(0)'; }
  requestAnimationFrame(() => requestAnimationFrame(() => { for (const b of bars) b.style.transform = ''; }));
  return el;
}

// one bar: track (hairline) + value box; tone: 'ink' | 'grey' | 'hatch'
export const bar = (v, tone = 'grey', tip = '', thin = false) =>
  h('span', { class: `vb ${thin ? 'thin' : ''}`, 'data-tip': tip || null },
    h('span', { class: `gb ${tone}`, style: `width:${Math.max(0, Math.min(1, v || 0)) * 100}%` }));

// a ranked list: rows {label, v, tone, value, tip, onClick, mark}
export function rankList(rows, { cls = '' } = {}) {
  const el = h('div', { class: `rl ${cls}` });
  for (const r of rows) {
    const tag = r.onClick ? 'button' : 'div';
    el.append(h(tag, { class: 'rr', type: r.onClick ? 'button' : null, onclick: r.onClick || null, 'data-tip': r.tip || null, lang: r.lang || null },
      h('span', { class: `rk ${r.strong ? 'on' : ''}` }, r.label),
      h('span', { class: 'rbar' }, bar(r.v, r.tone || 'grey'), ...(r.sub || []).map(x => bar(x.v, x.tone || 'grey', x.tip || '', true))),
      h('span', { class: 'rv' }, r.value ?? '', r.mark ? h('span', { class: 'rtick', 'aria-label': r.mark }) : '')));
  }
  return grow(el);
}

// weekly small multiples, one row per level; red = undecided please-check rows; click a week → onWeek(w)
export function weekly(rows, { w0, w1, labels, onWeek, weekLabel }) {
  const n = w1 - w0 + 1, W = 400, LH = 30, G = 6, LEFT = 0, H = rows.length * (LH + G);
  let max = 1; for (const r of rows) for (let w = w0; w <= w1; w++) max = Math.max(max, r.hits[w] || 0);
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, class: 'wk', role: 'img' });
  const bw = (W - LEFT) / n;
  rows.forEach((r, l) => {
    const base = l * (LH + G) + LH;
    svg.append(s('line', { x1: LEFT, x2: W, y1: base + .5, y2: base + .5, class: 'base' }));
    for (let w = w0; w <= w1; w++) {
      const v = r.hits[w] || 0, ck = Math.min(v, r.check[w] || 0); if (!v && !ck) continue;
      const x = LEFT + (w - w0) * bw, hh = Math.max(1.5, (v / max) * (LH - 2)), hc = v ? hh * (ck / v) : 0;
      const g = s('g', { class: 'wb', tabindex: '0', 'data-tip': `${weekLabel(w)} · ${labels[l]} ${num(v)}${ck ? ` · ${t().pending} ${num(ck)}` : ''}` });
      g.append(s('rect', { x: x + (bw > 3 ? .5 : 0), y: base - hh, width: Math.max(.8, bw - (bw > 3 ? 1 : 0)), height: hh - hc, class: 'b' }));
      if (hc) g.append(s('rect', { x: x + (bw > 3 ? .5 : 0), y: base - hc, width: Math.max(.8, bw - (bw > 3 ? 1 : 0)), height: hc, class: 'c' }));
      g.addEventListener('click', () => onWeek && onWeek(w));
      g.addEventListener('keydown', e => { if (e.key === 'Enter') onWeek && onWeek(w); });
      svg.append(g);
    }
  });
  const wrap = h('div', { class: 'wkw' });
  rows.forEach((r, l) => wrap.append(h('span', { class: 'wkl', style: `top:${l * (LH + G)}px` }, labels[l])));
  wrap.prepend(svg);
  return wrap;
}

// the hatch pattern for HTML boxes (same as the map's)
export const HATCH_CSS = 'repeating-linear-gradient(45deg,var(--hatch) 0 1px,transparent 1px 4px)';
export { p3, pct, UI };
