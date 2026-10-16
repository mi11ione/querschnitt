// Überblick: a statistical-atlas page. One line of large numbers; one small Switzerland per topic (cantons on one
// shared grey ramp = the topic's share of the canton's scored affairs, the Federal Assembly as a thin band; communes
// omitted at this size); «Neueste Woche» (the newest week with complete data) beside it. Click a map → the Karte on that topic.
import { D, TOPIC_BY_ID, newestFullWeek, parlCount } from './data.js';
import { h, s, t, UI, num, pct, p3, fmtDate, isoWeek, isoOfDay } from './util.js';
import { rampBreaks, rampClass } from './map.js';
import { bindTips, rankList } from './viz.js';
import { bodyName } from './case.js';

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
    const none = TOPIC_BY_ID.get('aps:none');
    return [dig, ...ch, none, ...saved].filter(Boolean);
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
    // share of scored APS rows that go to a person (lane please check), main period: D.tally, the fact line's numbers
    const nS = D.tally.aps, nC = D.tally.check;
    // big numbers; the lane leads with what needs no check, the rest is a person's weekly load (red tick: «wartet auf eine Person»)
    const weeks = Math.floor((D.dmax - D.dmin) / 7) + 1;
    const nP = nS - nC;
    // the same load per parliament: please-check rows per week / parliaments with affairs in the period
    const parl = new Set(); for (let i = 0; i < D.n; i++) if (c.day[i] >= D.dmin && c.day[i] <= D.dmax) parl.add(c.body[i]);
    const perParl = parl.size ? nC / weeks / parl.size : NaN;
    const fmt1 = x => Number.isNaN(x) ? '–' : (Math.floor(x * 10) / 10).toLocaleString(UI.lang === 'fr' ? 'fr-CH' : 'de-CH', { maximumFractionDigits: 1 });
    const bigShare = h('span', { class: 'bn', 'data-tip': `${num(nP)} ${L.of} ${num(nS)}` }, h('b', {}, pct(nS ? nP / nS : NaN, 0).replace(/\s/g, '\u2009')),
      h('span', {}, `${L.bigPass} · ${L.bigPassOf}`), h('span', { class: 'bn-sub', 'data-tip': `${num(nC)} ${L.of} ${num(nS)}` }, h('i', { class: 'rtick' }),
        ` ${pct(nS ? nC / nS : NaN, 0)} ${L.bigShare} · ${L.bigPerWeek(num(Math.round(nC / weeks)))} · `,
        h('span', { 'data-tip': L.bigPerParlTip(num(nC), num(weeks), num(parl.size)) }, L.bigPerParl(fmt1(perParl)))));
    const big = h('div', { class: 'big' },
      bigN(num(nS), L.bigScored), bigN(num(parlCount()[0]), L.parls(parlCount()[1])), bigN(num(weeks), L.bigWeeks),
      bigShare);
    const lede = h('p', { class: 'lede' }, L.lede(num(parlCount()[0]), parlCount()[1]));
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
        tp.saved ? h('span', { class: 'sv' }, h('span', { class: 'nw' }, `${L.narrow} ·`), ' ', pr ? [h('span', { class: 'nw' }, `${L.prec} ${pr.v}`), ' ',
          h('span', { class: 'nw' }, `(${pr.gold === 'judge' ? L.judgeLc : L.humanLc})`)] : h('span', { class: 'nw' }, L.notMeasured)) : '');
      (tp.saved ? sgrid : grid).append(cell);
    });
    const golds = new Set(tps.filter(x => x.saved).map(x => this.prec(x)).filter(Boolean).map(x => x.gold));
    const savedSec = sgrid.childNodes.length ? h('section', { class: 'atl-sv' },
      h('h3', { class: 'atl-h3' }, golds.size === 1 && golds.has('judge') ? L.savedAtlJ : L.savedTopics), sgrid) : '';
    const legend = h('p', { class: 'atl-leg' }, L.atlasLeg, ' ',
      ...[[1, '< 2.5'], [2, '2.5'], [3, '5'], [4, '10'], [5, '≥ 20']].map(([k, lab]) => h('span', { class: 'lk' }, h('span', { class: 'sw1', style: `background:var(--r${k})` }), lab)), h('span', {}, '%'),
      h('span', { class: 'lk' }, h('span', { class: 'sw1 hz' }), L.notScored));
    root.replaceChildren(h('div', { class: 'atl' }, lede, big, h('div', { class: 'atl-body' }, h('div', { class: 'atl-main' }, legend, grid, savedSec), this.week()), defs));
  }
  // «Neueste Woche»: new affairs of the newest week by level, then up to 5 notable ones (one chapter on ≥ 2 levels, then highest p)
  week() {
    const L = t(), c = D.c;
    const w = newestFullWeek(); // the newest week with complete data, as the «Neueste Woche» view (data.js)
    const lv = [0, 0, 0], rows = [];
    for (let i = 0; i < D.n; i++) if (c.week[i] === w && c.day[i] <= D.dmax) { if (c.lvl[i] < 3) lv[c.lvl[i]]++; rows.push(i); }
    const [y, k] = isoWeek(D.w0 + w * 7), mx = Math.max(1, ...lv);
    const box = h('aside', { class: 'atl-week' }, h('h2', {}, L.thisWeek),
      h('p', { class: 'tm mono dim' }, `${L.week} ${k} ${y} · ${isoOfDay(D.w0 + w * 7).slice(5).split('-').reverse().join('.')}.–${isoOfDay(Math.min(D.dmax, D.w0 + w * 7 + 6)).slice(5).split('-').reverse().join('.')}. · ${num(rows.length)} ${L.affairs}`),
      rankList([L.federal, L.cantonal, L.communal].map((lab, l) => ({ label: lab, v: lv[l] / mx, tone: 'ink', value: num(lv[l]) }))));
    // notable: a chapter present on ≥ 2 levels this week → its best affair per level; then the highest-p hits
    const P = i => Math.max(Number.isNaN(c.chp[i]) ? 0 : c.chp[i], c.df[i] ? c.dp[i] : 0);
    const byCh = new Map();
    for (const i of rows) { if (c.ch[i] < 0 || c.ch[i] === 24 || c.lvl[i] > 2) continue; if (!byCh.has(c.ch[i])) byCh.set(c.ch[i], [null, null, null]); const a = byCh.get(c.ch[i]); const l = c.lvl[i]; if (a[l] == null || P(i) > P(a[l])) a[l] = i; }
    const pick = [], seen = new Set();
    const cross = [...byCh.entries()].map(([ch, a]) => [ch, a.filter(x => x != null)]).filter(([, a]) => a.length >= 2).sort((a, b) => b[1].length - a[1].length);
    if (cross.length) { const [ch, a] = cross[0]; const nm = D.scheme.chapters[ch]; a.forEach(i => { pick.push([i, `${UI.lang === 'fr' ? nm.fr || nm.de : nm.de} · ${L.acrossLv(a.length)}`]); seen.add(i); }); }
    for (const i of [...rows].sort((a, b) => P(b) - P(a) || c.day[b] - c.day[a])) { if (pick.length >= 5) break; if (seen.has(i) || !(c.df[i] || c.ch[i] >= 0)) continue; pick.push([i, c.df[i] ? (TOPIC_BY_ID.get('adhoc/digitalisierung').names[UI.lang]) : (UI.lang === 'fr' ? D.scheme.chapters[c.ch[i]].fr : D.scheme.chapters[c.ch[i]].de)]); seen.add(i); }
    box.append(h('h3', { class: 'atl-h3' }, L.notable));
    for (const [i, why] of pick) box.append(h('button', { class: 'nt-a', type: 'button', lang: c.lang[i], onclick: () => this.openAffair(i) },
      h('span', { class: 't' }, c.title[i]), h('span', { class: 'm' }, `${fmtDate(c.date[i])} · ${bodyName(c.body[i])} · ${why}`)));
    return box;
  }
}
const bigN = (v, k, red) => h('span', { class: 'bn' }, h('b', { class: red ? 'sig' : '' }, v), h('span', {}, k));
