// Überblick: a statistical-atlas page. One small Switzerland per topic (cantons on one shared grey ramp = the topic's
// share of the canton's scored affairs, the Federal Assembly as a thin band; communes omitted at this size); the saved
// narrow topics in their own row. Click a map → the Karte on that topic.
import { D, TOPIC_BY_ID } from './data.js';
import { h, s, t, UI, num, pct } from './util.js';
import { rampBreaks, rampClass } from './map.js';
import { bindTips } from './viz.js';

const BAND = 26;

export class Atlas {
  constructor(root, { openTopic, openAffair }) {
    this.root = root; this.openTopic = openTopic; this.openAffair = openAffair;
    bindTips(root);
  }
  // Digitalisierung and the APS chapters first; the saved narrow topics after them, in their own quiet row
  topics() {
    const dig = TOPIC_BY_ID.get('adhoc/digitalisierung');
    const saved = [...TOPIC_BY_ID.values()].filter(x => x.saved).sort((a, b) => b.count - a.count);
    const ch = [...TOPIC_BY_ID.values()].filter(x => x.kind === 'chapter' && x.code !== 'aps:none').sort((a, b) => b.count - a.count);
    return [dig, ...ch, ...saved].filter(Boolean);
  }
  // a saved topic's measured precision of flags: the leading figure of its Prüfstand row (pruefstand.json rows[].topic),
  // exactly as written there; null when the topic has no row (then «nicht gemessen», never a number)
  prec(tp) {
    const r = ((D.pruef && (D.pruef.rows || D.pruef)) || []).find(x => x.topic === tp.id);
    if (!r) return null;
    const v = /^\s*(\d+[.,]\d+)/.exec(String((UI.lang === 'fr' && r.result_fr) || r.result || ''));
    return v ? { v: v[1], gold: r.gold } : null;
  }
  render() {
    const L = t(), c = D.c, root = this.root;
    const tps = this.topics();
    // per topic × canton (and federal): scored, hits
    const keys = Object.keys(D.geo.cantons), ki = new Map(keys.map((k, j) => [k, j])); ki.set('CHE', keys.length);
    const nK = keys.length + 1;
    const stat = tps.map(() => ({ n: new Int32Array(nK), hit: new Int32Array(nK) }));
    for (let i = 0; i < D.n; i++) {
      if (c.day[i] < D.dmin || c.day[i] > D.dmax) continue; // the main period only (as D.tally)
      const k = ki.get(c.body[i]);
      if (k == null) continue;
      tps.forEach((tp, j) => { if (tp.scored(i)) { stat[j].n[k]++; if (tp.hit(i)) stat[j].hit[k]++; } });
    }
    // one fixed, doubling ramp for every small map, so the maps compare at a glance
    const brk = [0.000001, 0.025, 0.05, 0.1, 0.2];
    // shared defs: every canton path once, used by every small map
    const [, , W, H] = D.geo.viewBox;
    const defs = s('svg', { width: 0, height: 0, class: 'atl-defs', 'aria-hidden': 'true' });
    const dg = s('defs');
    for (const [k, d] of Object.entries(D.geo.cantons)) dg.append(s('path', { id: `cp-${k}`, d }));
    dg.innerHTML += '<pattern id="atl-h" patternUnits="userSpaceOnUse" width="10" height="10" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="10" style="stroke:var(--hatch);stroke-width:2"/></pattern>';
    defs.append(dg);
    const grid = h('div', { class: 'atl-grid' }), sgrid = h('div', { class: 'atl-grid atl-saved' });
    tps.forEach((tp, j) => {
      const st = stat[j], name = tp.names[UI.lang] || tp.names.de;
      const svg = s('svg', { viewBox: `0 ${-BAND - 14} ${W} ${H + BAND + 14}`, class: 'atl-map', role: 'img', 'aria-label': name });
      const fk = ki.get('CHE'), fs = st.n[fk] ? st.hit[fk] / st.n[fk] : 0;
      svg.append(s('rect', { x: 0, y: -BAND - 6, width: W, height: BAND, class: 'atl-band', style: `fill:var(--r${st.n[fk] ? rampClass(fs, brk) : 0})`,
        'data-tip': `${L.federal} · ${pct(fs)} (${num(st.hit[fk])} ${L.of} ${num(st.n[fk])})` }));
      for (const k of keys) {
        const j2 = ki.get(k), v = st.n[j2] ? st.hit[j2] / st.n[j2] : 0;
        const u = s('use', { href: `#cp-${k}`, class: 'atl-ct', style: `fill:var(--r${st.n[j2] ? rampClass(v, brk) : 0})`,
          'data-tip': `${k} · ${pct(v)} (${num(st.hit[j2])} ${L.of} ${num(st.n[j2])})` });
        svg.append(u);
        if (!st.n[j2]) svg.append(s('use', { href: `#cp-${k}`, fill: 'url(#atl-h)', class: 'atl-hz' }));
      }
      // a saved topic says it is narrow and how often its flags were right (Prüfstand), under its map
      const pr = tp.saved ? this.prec(tp) : null;
      const cell = h('button', { class: `atl-cell ${j === 0 ? 'first' : ''}`, type: 'button', onclick: () => this.openTopic(tp), 'aria-label': name },
        svg, h('span', { class: 'atl-n' }, h('span', { class: 'nm' }, name), h('span', { class: 'ct' }, num(tp.count))),
        tp.saved ? h('span', { class: 'sv' }, h('span', { class: 'nw' }, `${L.narrow} ·`), ' ', pr ? h('span', { class: 'nw' }, `${L.prec} ${pr.v}`) : h('span', { class: 'nw' }, L.notMeasured)) : '');
      (tp.saved ? sgrid : grid).append(cell);
    });
    const golds = new Set(tps.filter(x => x.saved).map(x => this.prec(x)).filter(Boolean).map(x => x.gold));
    const savedSec = sgrid.childNodes.length ? h('section', { class: 'atl-sv' },
      h('h3', { class: 'atl-h3' }, golds.size === 1 && golds.has('judge') ? L.savedAtlJ : L.savedTopics), sgrid) : '';
    const legend = h('p', { class: 'atl-leg' }, L.atlasLeg, ' ',
      ...[[1, '< 2.5'], [2, '2.5'], [3, '5'], [4, '10'], [5, '≥ 20']].map(([k, lab]) => h('span', { class: 'lk' }, h('span', { class: 'sw1', style: `background:var(--r${k})` }), lab)), h('span', {}, '%'),
      h('span', { class: 'lk' }, h('span', { class: 'sw1 hz' }), L.notScored));
    root.replaceChildren(h('div', { class: 'atl' }, h('div', { class: 'atl-body one' }, h('div', { class: 'atl-main' }, legend, grid, savedSec)), defs));
  }
}
