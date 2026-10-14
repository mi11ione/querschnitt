// Querschnitt: APS chapters (rows) × parliaments (columns: Bund, cantons by language region, communes aggregated, FL).
// Cell = share of the parliament's scored affairs in that chapter in the period; grey ramp; hatched where fewer than
// 25 % of the parliament's affairs in the period are scored. Click a cell → that chapter, that parliament, on the map.
import { D, TOPIC_BY_ID } from './data.js';
import { h, s, t, UI, num, pct, isoOfDay } from './util.js';
import { rampBreaks, rampClass } from './map.js';
import { bindTips } from './viz.js';

const DE = 'ZH BE LU UR SZ OW NW GL ZG SO BS BL SH AR AI SG GR AG TG'.split(' ');
const FR = 'FR VD VS NE GE JU'.split(' ');
const IT = ['TI'];

export class Matrix {
  constructor(root, board) {
    this.root = root; this.board = board;
    this.ro = new ResizeObserver(() => { if (!root.hidden) this.render(); }); this.ro.observe(root);
    bindTips(root);
  }
  columns(narrow) {
    const L = t();
    if (narrow) return [
      { key: 'CHE', label: 'CH', bodies: ['CHE'], g: 0 }, { key: 'de', label: 'de', bodies: DE, g: 1 }, { key: 'fr', label: 'fr', bodies: FR, g: 2 },
      { key: 'it', label: 'it', bodies: IT, g: 3 }, { key: 'GEM', label: L.gemAgg.slice(0, 3), bodies: null, g: 4 }, { key: 'LIE', label: 'FL', bodies: ['LIE'], g: 5 }];
    return [{ key: 'CHE', label: 'CH', bodies: ['CHE'], g: 0 }, ...DE.map(k => ({ key: k, label: k, bodies: [k], g: 1 })), ...FR.map(k => ({ key: k, label: k, bodies: [k], g: 2 })),
      ...IT.map(k => ({ key: k, label: k, bodies: [k], g: 3 })), { key: 'GEM', label: L.gemAgg.slice(0, 3), bodies: null, g: 4 }, { key: 'LIE', label: 'FL', bodies: ['LIE'], g: 5 }];
  }
  render() {
    const B = this.board, S = B.S, c = D.c, L = t(), root = this.root;
    const W = root.clientWidth || 520, narrow = W < 460;
    const cols = this.columns(narrow), ci = new Map();
    cols.forEach((col, k) => { if (col.bodies) col.bodies.forEach(b => ci.set(b, k)); });
    const colOf = i => { const b = c.body[i]; if (ci.has(b)) return ci.get(b); return c.lvl[i] === 2 ? cols.findIndex(x => x.key === 'GEM') : -1; };
    const chs = D.scheme.chapters, K = chs.length, nC = cols.length;
    const cnt = Array.from({ length: K }, () => new Int32Array(nC)), tot = new Int32Array(nC), rowTot = new Int32Array(K);
    const mask = B.mask, br = S.brush;
    for (let i = 0; i < D.n; i++) {
      const ch = c.ch[i]; if (ch < 0 || (mask && !mask[i]) || c.day[i] < D.dmin) continue;
      if (br && (c.week[i] < br[0] || c.week[i] > br[1])) continue;
      const k = colOf(i); if (k < 0) continue;
      cnt[ch][k]++; tot[k]++; rowTot[ch]++;
    }
    // coverage per column: scored / affairs in the period (n_by_month)
    const a = isoOfDay(br ? D.w0 + br[0] * 7 : D.dmin).slice(0, 7), z = isoOfDay(br ? D.w0 + br[1] * 7 + 6 : D.dmax).slice(0, 7);
    const pop = new Float64Array(nC);
    for (const b of D.bodies) {
      let k = ci.has(b.key) ? ci.get(b.key) : (b.level === 'communal' ? cols.findIndex(x => x.key === 'GEM') : -1);
      if (k < 0 || !b.n_by_month) continue;
      for (const [m, v] of Object.entries(b.n_by_month)) if (m >= a && m <= z) pop[k] += v;
    }
    const cov = [...tot].map((x, k) => pop[k] ? x / pop[k] : null);
    const shares = []; for (let r = 0; r < K; r++) for (let k = 0; k < nC; k++) if (tot[k]) shares.push(cnt[r][k] / tot[k]);
    const brk = rampBreaks(shares);
    const order = [...Array(K).keys()].sort((x, y) => rowTot[y] - rowTot[x]);
    const LW = narrow ? 120 : Math.min(170, Math.round(W * 0.32)), HH = 30, cw = (W - LW) / nC, rh = 16;
    const H = HH + K * rh + 4;
    const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, class: 'mx', role: 'img', 'aria-label': L.matrix });
    const cur = B.tp && B.tp.kind === 'chapter' ? B.tp.idx : null;
    // column heads (click = that parliament on the map)
    cols.forEach((col, k) => {
      const x = LW + k * cw + cw / 2;
      const tx = s('text', { x, y: HH - 6, 'text-anchor': 'middle', class: `ch ${S.body && col.bodies && col.bodies.length === 1 && col.bodies[0] === S.body ? 'on' : ''}`, tabindex: '0',
        'data-tip': `${col.bodies && col.bodies.length === 1 ? (D.B.get(col.bodies[0]) ? `${D.B.get(col.bodies[0]).name_de}` : col.key) : col.label} · ${num(tot[k])} ${L.scored} · ${L.coverage} ${pct(cov[k])}` });
      tx.textContent = col.label;
      if (cw < 22) tx.setAttribute('transform', `rotate(-90 ${x} ${HH - 8})`), tx.setAttribute('text-anchor', 'start'), tx.setAttribute('x', x + 4), tx.setAttribute('y', HH - 8);
      const go = () => { if (col.bodies && col.bodies.length === 1) { B.S.body = col.bodies[0]; B.setMapMode('map'); B.refresh(); } };
      tx.addEventListener('click', go); tx.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
      svg.append(tx);
    });
    // region hairlines
    for (let k = 1; k < nC; k++) if (cols[k].g !== cols[k - 1].g) svg.append(s('line', { x1: LW + k * cw, x2: LW + k * cw, y1: HH - 4, y2: H, class: 'reg' }));
    order.forEach((r, ri) => {
      const y = HH + ri * rh, nm = UI.lang === 'fr' ? chs[r].fr || chs[r].de : chs[r].de;
      const lab = s('text', { x: 0, y: y + rh - 4, class: `rl ${r === cur ? 'on' : ''}`, tabindex: '0', 'data-tip': `${nm} · ${num(rowTot[r])}` });
      lab.textContent = nm.length > (LW / 7) ? nm.slice(0, Math.floor(LW / 7) - 1) + '…' : nm;
      const goR = () => { const tp = TOPIC_BY_ID.get(chs[r].code); if (tp) { B.setTopic(tp); B.setMapMode('map'); } };
      lab.addEventListener('click', goR); lab.addEventListener('keydown', e => { if (e.key === 'Enter') goR(); });
      svg.append(lab);
      if (r === cur) svg.append(s('rect', { x: LW - 1, y, width: W - LW + 1, height: rh, class: 'cur' }));
      cols.forEach((col, k) => {
        const v = tot[k] ? cnt[r][k] / tot[k] : 0, hatch = cov[k] != null && cov[k] < 0.25;
        const g = s('rect', { x: LW + k * cw + .5, y: y + .5, width: Math.max(1, cw - 1), height: rh - 1, class: 'cell', style: `fill:var(--r${tot[k] ? rampClass(v, brk) : 0})`,
          'data-tip': `${nm} · ${col.bodies && col.bodies.length === 1 ? col.key : col.label}: ${num(cnt[r][k])} ${L.of} ${num(tot[k])} · ${pct(v)}${cov[k] != null ? ` · ${L.coverage} ${pct(cov[k])}` : ''}` });
        g.addEventListener('click', () => { const tp = TOPIC_BY_ID.get(chs[r].code); if (!tp) return; B.setTopic(tp); if (col.bodies && col.bodies.length === 1) B.S.body = col.bodies[0]; B.setMapMode('map'); B.refresh(); });
        svg.append(g);
        if (hatch || !tot[k]) svg.append(s('rect', { x: LW + k * cw + .5, y: y + .5, width: Math.max(1, cw - 1), height: rh - 1, fill: 'url(#mx-h)', class: 'hz' }));
      });
    });
    const defs = s('defs'); defs.innerHTML = '<pattern id="mx-h" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" style="stroke:var(--hatch);stroke-width:1"/></pattern>';
    svg.prepend(defs);
    root.replaceChildren(h('p', { class: 'mxh' }, L.matrixHint, ` · ${pct(brk[0] || 0)} … ${pct(Math.max(0, ...shares))}`), svg);
  }
}
