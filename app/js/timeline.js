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
    const [o, z] = this.dom || [0, D.nWeeks - 1];
    return Math.max(o, Math.min(z, o + Math.floor(x / this.bw)));
  }
  down(e) { if (e.button) return; this.prev = this.brush; this.drag = { a: this.wAt(e), moved: false }; this.svg.setPointerCapture(e.pointerId); }
  move(e) {
    const w = this.wAt(e);
    if (this.drag) { if (w !== this.drag.a) this.drag.moved = true; this.brush = [Math.min(this.drag.a, w), Math.max(this.drag.a, w)]; this.draw(); }
    this.hover = w; this.head();
  }
  up(e) {
    if (!this.drag) return;
    const d = this.drag; this.drag = null;
    if (!d.moved) this.brush = this.prev && this.prev[0] === d.a && this.prev[1] === d.a ? null : [d.a, d.a]; // click = that week; again = all
    this.draw(); this.onBrush && this.onBrush(this.brush);
  }
  set(counts, brush, mark, checks, dom, scored) {
    this.counts = counts; this.brush = brush; this.mark = mark; if (checks !== undefined) this.checks = checks;
    if (dom !== undefined) this.dom = dom; if (scored !== undefined) this.scored = scored; this.draw();
  }
  weekLabel(w) { const d = D.w0 + w * 7, [y, k] = isoWeek(d); return `${t().week} ${k} ${y}`; }
  head() {
    const L = t(), w = this.hover;
    if (w != null) {
      const c = this.counts;
      const k = this.checks ? this.checks[0][w] + this.checks[1][w] + this.checks[2][w] : 0;
      this.hd.innerHTML = `<b>${this.weekLabel(w)}</b><span>${L.federal} ${num(c[0][w] || 0)}</span><span>${L.cantonal} ${num(c[1][w] || 0)}</span><span>${L.communal} ${num(c[2][w] || 0)}</span>${k ? `<span class="sig">${L.pending} ${num(k)}</span>` : ''}`;
    } else if (this.brush) {
      const [a, b] = this.brush;
      this.hd.innerHTML = `<b>${isoOfDay(D.w0 + a * 7)} – ${isoOfDay(D.w0 + b * 7 + 6)}</b><span>${this.weekLabel(a)} – ${this.weekLabel(b)}</span>`;
    } else {
      const [o, z] = this.dom || [0, D.nWeeks - 1];
      this.hd.innerHTML = `<span>${L.period}: <b>${isoOfDay(Math.max(D.w0 + o * 7, D.dminAll))} – ${isoOfDay(Math.min(D.dmax, D.w0 + z * 7 + 6))}</b></span>`;
    }
  }
  draw() {
    const W = this.root.clientWidth; if (!W) return;
    LEFT = W < 420 ? 0 : 92;
    const [o, z] = this.dom || [0, D.nWeeks - 1];
    const nW = z - o + 1, bw = this.bw = Math.max(1, (W - LEFT) / nW), L = t();
    const Hh = 3 * ROW + 2 * GAP + AXIS;
    const svg = this.svg; svg.setAttribute('viewBox', `0 0 ${W} ${Hh}`); svg.setAttribute('height', Hh);
    svg.replaceChildren();
    // weeks outside a saved topic's scored period are hatched
    if (this.scored) {
      const df = s('defs'); df.innerHTML = '<pattern id="tl-h" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" style="stroke:var(--hatch);stroke-width:1"/></pattern>'; svg.append(df);
      const [sa, sb] = this.scored;
      for (const [a, b] of [[o, sa - 1], [sb + 1, z]]) if (b >= a) svg.append(s('rect', { class: 'unsc', fill: 'url(#tl-h)', x: LEFT + (a - o) * bw, y: 0, width: (b - a + 1) * bw, height: 3 * ROW + 2 * GAP }));
    }
    if (this.brush) {
      const [a, b] = this.brush;
      svg.append(s('rect', { class: 'brush', x: LEFT + (a - o) * bw, y: 0, width: (b - a + 1) * bw, height: 3 * ROW + 2 * GAP }));
      for (const x of [LEFT + (a - o) * bw, LEFT + (b + 1 - o) * bw]) svg.append(s('line', { class: 'edge', x1: x, x2: x, y1: 0, y2: 3 * ROW + 2 * GAP }));
    }
    let max = 1; for (const r of this.counts) for (let w = o; w <= z; w++) if (r[w] > max) max = r[w];
    const names = [L.federal, L.cantonal, L.communal];
    for (let l = 0; l < 3; l++) {
      const y0 = l * (ROW + GAP), base = y0 + ROW;
      const lab = s('text', { x: 0, y: LEFT ? base - 4 : y0 + 10 }); lab.textContent = names[l]; svg.append(lab);
      svg.append(s('line', { class: 'base', x1: LEFT, x2: W, y1: base + .5, y2: base + .5 }));
      const row = this.counts[l] || [];
      let d = '';
      for (let w = o; w <= z; w++) {
        const v = row[w]; if (!v) continue;
        const hh = Math.max(1.5, (v / max) * (ROW - 4));
        d += `M${(LEFT + (w - o) * bw + (bw > 3 ? .5 : 0)).toFixed(1)} ${base}h${Math.max(.8, bw - (bw > 3 ? 1 : 0)).toFixed(1)}v${-hh.toFixed(1)}h${-Math.max(.8, bw - (bw > 3 ? 1 : 0)).toFixed(1)}z`;
      }
      svg.append(s('path', { class: 'bar0', d }));
      // the undecided please-check rows of each week as a red base segment
      const ck = this.checks && this.checks[l];
      if (ck) {
        let dc = '';
        for (let w = o; w <= z; w++) {
          const v = row[w], k = Math.min(ck[w] || 0, v || 0); if (!k) continue;
          const hh = Math.max(1.5, (v / max) * (ROW - 4)) * (k / v), bwi = Math.max(.8, bw - (bw > 3 ? 1 : 0));
          dc += `M${(LEFT + (w - o) * bw + (bw > 3 ? .5 : 0)).toFixed(1)} ${base}h${bwi.toFixed(1)}v${-Math.max(1, hh).toFixed(1)}h${-bwi.toFixed(1)}z`;
        }
        if (dc) svg.append(s('path', { class: 'mark', d: dc }));
      }
    }
    if (this.mark) {
      const x = LEFT + (this.mark.w - o + .5) * bw;
      svg.append(s('line', { class: 'selw', x1: x, x2: x, y1: 0, y2: 3 * ROW + 2 * GAP }));
      const y = this.mark.l * (ROW + GAP) + ROW;
      svg.append(s('rect', { class: 'selm', x: x - 3, y: y + 2, width: 6, height: 4 }));
    }
    // month ticks
    const yA = 3 * ROW + 2 * GAP + 14, M = MONTHS[UI.lang];
    let lastX = -99;
    for (let d = D.w0 + o * 7; d <= Math.min(D.dmax, D.w0 + z * 7 + 6) + 7; d++) {
      const dt = new Date(d * 864e5);
      if (dt.getUTCDate() !== 1) continue;
      const x = LEFT + ((d - D.w0) / 7 - o) * bw;
      if (x - lastX < 34) continue; lastX = x;
      svg.append(s('line', { class: 'base', x1: x, x2: x, y1: 3 * ROW + 2 * GAP, y2: 3 * ROW + 2 * GAP + 4 }));
      const tx = s('text', { x: x + 2, y: yA }); tx.textContent = dt.getUTCMonth() === 0 ? String(dt.getUTCFullYear()) : M[dt.getUTCMonth()]; svg.append(tx);
    }
    this.head();
  }
}
