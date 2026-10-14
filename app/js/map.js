// Switzerland for one topic: cantons as outlines (cantonal parliaments), communal parliaments as squares at their
// commune's centroid, the Federal Assembly as a band above, Liechtenstein's Landtag apart in the corner. Geometry is
// pre-projected at build time (dev/make_geo.py); nothing is projected at runtime.
import { D } from './data.js';
import { s, h, num, pct, t, UI } from './util.js';

const SMALL = new Set(['BS', 'AI', 'AR', 'NW', 'OW', 'ZG', 'GE', 'BL', 'SH', 'UR', 'GL', 'NE', 'JU', 'SO']);
const BAND_Y = -72, BAND_H = 34;

export class SwissMap {
  constructor(root, { onClick, onHover } = {}) {
    this.root = root; this.onClick = onClick; this.onHover = onHover; this.sel = null; this.stats = new Map();
    const g = D.geo, [, , W, H] = g.viewBox;
    this.W = W; this.H = H;
    const svg = this.svg = s('svg', { viewBox: `0 ${BAND_Y - 4} ${W} ${H - BAND_Y + 8}`, role: 'img', 'aria-label': 'Karte' });
    const defs = s('defs');
    const pat = s('pattern', { id: `hatch-${root.id || 'm'}`, patternUnits: 'userSpaceOnUse', width: 6, height: 6, patternTransform: 'rotate(45)' });
    pat.append(s('line', { x1: 0, y1: 0, x2: 0, y2: 6, style: 'stroke:var(--hatch);stroke-width:1.1' }));
    defs.append(pat); svg.append(defs);
    this.hatchUrl = `url(#hatch-${root.id || 'm'})`;
    this.gC = s('g'); this.gL = s('g'); this.gH = s('g', { class: 'hat' }); this.gM = s('g'); this.gT = s('g'); this.gX = s('g');
    svg.append(this.gC, this.gL, this.gH, this.gM, this.gX, this.gT);
    this.el = new Map(); this.hat = new Map(); this.lbl = new Map();
    for (const [ab, d] of Object.entries(g.cantons)) {
      const p = s('path', { d, class: 'ct', 'data-k': ab });
      this.gC.append(p); this.el.set(ab, p);
      const hp = s('path', { d, fill: this.hatchUrl, stroke: 'none' }); hp.style.display = 'none'; this.gH.append(hp); this.hat.set(ab, hp);
    }
    this.gL.append(s('path', { d: g.lakes, class: 'lake' }));
    // canton labels
    for (const [ab, [x, y]] of Object.entries(g.canton_centroids)) {
      if (SMALL.has(ab)) continue;
      const tx = s('text', { x, y, 'text-anchor': 'middle', 'dominant-baseline': 'central' }); tx.textContent = ab;
      this.gX.append(tx); this.lbl.set(ab, tx);
    }
    // federal band
    const band = s('rect', { x: 0, y: BAND_Y, width: W, height: BAND_H, class: 'band', 'data-k': 'CHE' });
    const bh = s('rect', { x: 0, y: BAND_Y, width: W, height: BAND_H, fill: this.hatchUrl }); bh.style.display = 'none';
    this.gC.append(band); this.gH.append(bh); this.el.set('CHE', band); this.hat.set('CHE', bh);
    this.bandL = s('text', { x: 10, y: BAND_Y + BAND_H / 2, 'dominant-baseline': 'central' });
    this.bandR = s('text', { x: W - 10, y: BAND_Y + BAND_H / 2, 'dominant-baseline': 'central', 'text-anchor': 'end' });
    this.gX.append(this.bandL, this.bandR);
    // communes + Liechtenstein
    this.sq = [];
    for (const b of D.bodies) {
      if (b.level === 'communal') {
        const c = g.communes[b.key]; if (!c) continue;
        const r = s('rect', { class: 'cm', 'data-k': b.key }); const hr = s('rect', { fill: this.hatchUrl }); hr.style.display = 'none';
        this.gM.append(r); this.gH.append(hr); this.el.set(b.key, r); this.hat.set(b.key, hr);
        this.sq.push({ k: b.key, x0: c[0], y0: c[1], x: c[0], y: c[1], r, hr });
      }
    }
    if (D.B.has('LIE')) {
      const r = s('rect', { class: 'cm', 'data-k': 'LIE' }); const hr = s('rect', { fill: this.hatchUrl }); hr.style.display = 'none';
      this.gM.append(r); this.gH.append(hr); this.el.set('LIE', r); this.hat.set('LIE', hr);
      this.lie = { k: 'LIE', r, hr, x: W - 24, y: H - 30 };
      this.lieL = s('text', { 'text-anchor': 'end', 'dominant-baseline': 'central' }); this.lieL.textContent = 'FL'; this.gX.append(this.lieL);
    }
    root.append(svg);
    this.tip = h('div', { class: 'tip', hidden: true }); root.append(this.tip);
    svg.addEventListener('pointermove', e => this.move(e));
    svg.addEventListener('pointerleave', () => { this.tip.hidden = true; this.onHover && this.onHover(null); });
    svg.addEventListener('click', e => { const k = e.target.getAttribute && e.target.getAttribute('data-k'); this.onClick && this.onClick(k || null); });
    this.ro = new ResizeObserver(() => this.layout()); this.ro.observe(root);
  }
  unit() { const w = this.svg.clientWidth || this.root.clientWidth || 600; return this.W / w; }
  layout() {
    const k = this.unit(); if (!isFinite(k) || k <= 0) return;
    this.k = k;
    const px = this.W / k, fs = 12 * k, side = Math.max(5, Math.min(9, px / 70)) * k;
    for (const tx of this.svg.querySelectorAll('text')) tx.setAttribute('font-size', fs);
    // nudge overlapping squares apart (a few relaxation passes)
    const S = this.sq; for (const q of S) { q.x = q.x0; q.y = q.y0; }
    const min = side + 1.5 * k;
    for (let it = 0; it < 40; it++) {
      let moved = false;
      for (let a = 0; a < S.length; a++) for (let b = a + 1; b < S.length; b++) {
        const A = S[a], B = S[b], dx = B.x - A.x, dy = B.y - A.y;
        if (Math.abs(dx) < min && Math.abs(dy) < min) {
          const ox = min - Math.abs(dx), oy = min - Math.abs(dy);
          if (ox < oy) { const m = (ox / 2) * (dx >= 0 ? 1 : -1) || ox / 2; A.x -= m; B.x += m; } else { const m = (oy / 2) * (dy >= 0 ? 1 : -1) || oy / 2; A.y -= m; B.y += m; }
          moved = true;
        }
      }
      if (!moved) break;
    }
    for (const q of S) for (const r of [q.r, q.hr]) { r.setAttribute('x', q.x - side / 2); r.setAttribute('y', q.y - side / 2); r.setAttribute('width', side); r.setAttribute('height', side); }
    if (this.lie) {
      const L = this.lie, sd = side * 1.4;
      for (const r of [L.r, L.hr]) { r.setAttribute('x', L.x - sd / 2); r.setAttribute('y', L.y - sd / 2); r.setAttribute('width', sd); r.setAttribute('height', sd); }
      this.lieL.setAttribute('x', L.x - sd / 2 - 6 * k); this.lieL.setAttribute('y', L.y);
    }
    this.drawTicks();
  }
  // stats: Map key -> {n, hits, check, share, cls, hatch}
  update(stats, sel) {
    this.stats = stats; this.sel = sel;
    for (const [k, el] of this.el) {
      const st = stats.get(k);
      el.style.fill = `var(--r${st ? st.cls : 0})`;
      el.classList.toggle('on', k === sel);
      const hp = this.hat.get(k); if (hp) hp.style.display = st && st.hatch ? '' : 'none';
      const lb = this.lbl.get(k); if (lb) { lb.classList.toggle('lbl-dark', !!st && st.cls >= 4); lb.classList.toggle('on', k === sel); }
    }
    const fe = stats.get('CHE'), b = D.B.get('CHE');
    this.bandL.textContent = t().federal; // short: the full name sits in the filter line when selected
    this.bandR.textContent = fe && fe.n ? `${num(fe.hits)} · ${pct(fe.share)}` : '–';
    for (const tx of [this.bandL, this.bandR]) tx.classList.toggle('lbl-dark', !!fe && fe.cls >= 4);
    this.drawTicks();
    if (this.k == null) this.layout();
  }
  drawTicks() {
    this.gT.replaceChildren();
    const k = this.k || this.unit(), w = 2.5 * k, hh = 8 * k;
    const at = (x, y) => this.gT.append(s('rect', { class: 'tick', x, y, width: w, height: hh }));
    for (const [key, st] of this.stats) {
      if (!st.check) continue;
      if (key === 'CHE') { at(this.W - 4 * k, BAND_Y + 2 * k); continue; }
      if (key === 'LIE' && this.lie) { at(this.lie.x + 10 * k, this.lie.y - 11 * k); continue; }
      const q = this.sq.find(x => x.k === key);
      if (q) { at(q.x + 6 * k, q.y - 10 * k); continue; }
      const c = D.geo.canton_centroids[key];
      if (c) at(c[0] + (SMALL.has(key) ? 0 : 12 * k), c[1] - 12 * k);
    }
  }
  move(e) {
    const k = e.target.getAttribute && e.target.getAttribute('data-k');
    if (!k) { this.tip.hidden = true; this.onHover && this.onHover(null); return; }
    const b = D.B.get(k), st = this.stats.get(k) || {}, L = t();
    const nm = b ? `${UI.lang === 'fr' ? b.name_fr : b.name_de}${b.level !== 'federal' ? ' ' + (UI.lang === 'fr' ? b.place_fr : b.place_de) : ''}` : k;
    const lines = [];
    lines.push(st.n ? `${num(st.hits)} ${L.of} ${num(st.n)} · ${pct(st.share)}` : L.notScored);
    if (b) lines.push(`${L.coverage} ${pct(st.cov)}${b.covered_from ? ` · ${L.covered} ${b.covered_from}` : ''}`);
    if (b && b.title_only_share != null) lines.push(`${L.titleOnly} ${pct(b.title_only_share)}`);
    if (st.check) lines.push(`<span class="sig">${L.pending} ${num(st.check)}</span>`);
    this.tip.innerHTML = `<b>${nm.replace(/</g, '&lt;')}</b>${lines.join('<br>')}`;
    this.tip.hidden = false;
    const r = this.root.getBoundingClientRect();
    let x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    const tw = this.tip.offsetWidth, th = this.tip.offsetHeight;
    if (x + tw > r.width) x = Math.max(0, e.clientX - r.left - tw - 10);
    if (y + th > r.height + 40) y = e.clientY - r.top - th - 10;
    this.tip.style.left = `${x}px`; this.tip.style.top = `${y}px`;
    this.onHover && this.onHover(k);
  }
}

// ramp classes from the distribution of non-zero shares (quintiles); returns breaks (lower bounds of classes 1..5)
export function rampBreaks(shares) {
  const v = shares.filter(x => x > 0).sort((a, b) => a - b);
  if (!v.length) return [];
  const q = f => v[Math.min(v.length - 1, Math.floor(f * v.length))];
  const br = [v[0], q(0.2), q(0.4), q(0.6), q(0.8)];
  for (let i = 1; i < br.length; i++) if (br[i] <= br[i - 1]) br[i] = br[i - 1] + 1e-9;
  return br;
}
export function rampClass(share, br) {
  if (!(share > 0) || !br.length) return 0;
  let c = 1; for (let i = 1; i < br.length; i++) if (share >= br[i]) c = i + 1;
  return c;
}
