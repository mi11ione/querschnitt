// Weekly timeline, one row per level (federal, cantonal, communal); drag to set the period, click to clear it.
import { D } from './data.js';
import { s, h, t, num, isoWeek, isoOfDay, MONTHS, UI } from './util.js';

let LEFT = 92; const ROW = 34, GAP = 6, AXIS = 20;

export class Timeline {
  constructor(root, { onBrush } = {}) {
    this.root = root; this.onBrush = onBrush; this.brush = null; this.counts = [[], [], []]; this.mark = null;
    this.hd = h('div', { class: 'hd' }); root.append(this.hd);
    this.svg = s('svg', { role: 'img', 'aria-label': 'Timeline' }); root.append(this.svg);
    this.svg.addEventListener('pointerdown', e => this.down(e));
    this.svg.addEventListener('pointermove', e => this.move(e));
    this.svg.addEventListener('pointerup', e => this.up(e));
    this.svg.addEventListener('pointerleave', () => { if (!this.drag) { this.hover = null; this.head(); } });
    this.ro = new ResizeObserver(() => this.draw()); this.ro.observe(root);
  }
  wAt(e) {
    const r = this.svg.getBoundingClientRect(), x = e.clientX - r.left - LEFT;
    return Math.max(0, Math.min(D.nWeeks - 1, Math.floor(x / this.bw)));
  }
  down(e) { if (e.button) return; this.drag = { a: this.wAt(e), moved: false }; this.svg.setPointerCapture(e.pointerId); }
  move(e) {
    const w = this.wAt(e);
    if (this.drag) { if (w !== this.drag.a) this.drag.moved = true; this.brush = [Math.min(this.drag.a, w), Math.max(this.drag.a, w)]; this.draw(); }
    this.hover = w; this.head();
  }
  up(e) {
    if (!this.drag) return;
    const d = this.drag; this.drag = null;
    if (!d.moved) this.brush = null;
    this.draw(); this.onBrush && this.onBrush(this.brush);
  }
  set(counts, brush, mark) { this.counts = counts; this.brush = brush; this.mark = mark; this.draw(); }
  weekLabel(w) { const d = D.w0 + w * 7, [y, k] = isoWeek(d); return `${t().week} ${k} ${y}`; }
  head() {
    const L = t(), w = this.hover;
    if (w != null) {
      const c = this.counts;
      this.hd.innerHTML = `<b>${this.weekLabel(w)}</b><span>${L.federal} ${num(c[0][w] || 0)}</span><span>${L.cantonal} ${num(c[1][w] || 0)}</span><span>${L.communal} ${num(c[2][w] || 0)}</span>`;
    } else if (this.brush) {
      const [a, b] = this.brush;
      this.hd.innerHTML = `<b>${isoOfDay(D.w0 + a * 7)} – ${isoOfDay(D.w0 + b * 7 + 6)}</b><span>${this.weekLabel(a)} – ${this.weekLabel(b)}</span>`;
    } else {
      this.hd.innerHTML = `<span>${L.period}: <b>${isoOfDay(D.dmin)} – ${isoOfDay(D.dmax)}</b></span>`;
    }
  }
  draw() {
    const W = this.root.clientWidth; if (!W) return;
    LEFT = W < 420 ? 0 : 92;
    const nW = D.nWeeks, bw = this.bw = Math.max(1, (W - LEFT) / nW), L = t();
    const Hh = 3 * ROW + 2 * GAP + AXIS;
    const svg = this.svg; svg.setAttribute('viewBox', `0 0 ${W} ${Hh}`); svg.setAttribute('height', Hh);
    svg.replaceChildren();
    if (this.brush) {
      const [a, b] = this.brush;
      svg.append(s('rect', { class: 'brush', x: LEFT + a * bw, y: 0, width: (b - a + 1) * bw, height: 3 * ROW + 2 * GAP }));
      for (const x of [LEFT + a * bw, LEFT + (b + 1) * bw]) svg.append(s('line', { class: 'edge', x1: x, x2: x, y1: 0, y2: 3 * ROW + 2 * GAP }));
    }
    let max = 1; for (const r of this.counts) for (const v of r) if (v > max) max = v;
    const names = [L.federal, L.cantonal, L.communal];
    for (let l = 0; l < 3; l++) {
      const y0 = l * (ROW + GAP), base = y0 + ROW;
      const lab = s('text', { x: 0, y: LEFT ? base - 4 : y0 + 10 }); lab.textContent = names[l]; svg.append(lab);
      svg.append(s('line', { class: 'base', x1: LEFT, x2: W, y1: base + .5, y2: base + .5 }));
      const row = this.counts[l] || [];
      let d = '';
      for (let w = 0; w < nW; w++) {
        const v = row[w]; if (!v) continue;
        const hh = Math.max(1.5, (v / max) * (ROW - 4));
        d += `M${(LEFT + w * bw + (bw > 3 ? .5 : 0)).toFixed(1)} ${base}h${Math.max(.8, bw - (bw > 3 ? 1 : 0)).toFixed(1)}v${-hh.toFixed(1)}h${-Math.max(.8, bw - (bw > 3 ? 1 : 0)).toFixed(1)}z`;
      }
      svg.append(s('path', { class: 'bar0', d }));
    }
    if (this.mark) {
      const x = LEFT + (this.mark.w + .5) * bw;
      svg.append(s('line', { class: 'selw', x1: x, x2: x, y1: 0, y2: 3 * ROW + 2 * GAP }));
      const y = this.mark.l * (ROW + GAP) + ROW;
      svg.append(s('rect', { class: 'mark', x: x - 3, y: y + 2, width: 6, height: 4 }));
    }
    // month ticks
    const yA = 3 * ROW + 2 * GAP + 14, M = MONTHS[UI.lang];
    let lastX = -99;
    for (let d = D.w0; d <= D.dmax + 7; d++) {
      const dt = new Date(d * 864e5);
      if (dt.getUTCDate() !== 1) continue;
      const x = LEFT + ((d - D.w0) / 7) * bw;
      if (x - lastX < 34) continue; lastX = x;
      svg.append(s('line', { class: 'base', x1: x, x2: x, y1: 3 * ROW + 2 * GAP, y2: 3 * ROW + 2 * GAP + 4 }));
      const tx = s('text', { x: x + 2, y: yA }); tx.textContent = dt.getUTCMonth() === 0 ? String(dt.getUTCFullYear()) : M[dt.getUTCMonth()]; svg.append(tx);
    }
    this.head();
  }
}
