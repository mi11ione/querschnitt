// Karte (and the Neues Thema board): topic → map + weekly timeline → ruled list (or Pult) → the selected affair.
import { D, API, apiPost, getDec, setDec, detail, TOPICS, TOPIC_BY_ID, norm, syncDecisions } from './data.js';
import { h, t, UI, num, pct, p3, fmtDate, isoWeek, isoOfDay, dayNum, debounce, toast, download } from './util.js';
import { SwissMap, rampBreaks, rampClass } from './map.js';
import { Timeline } from './timeline.js';
import { VList } from './vlist.js';
import { Picker } from './picker.js';
import { renderCase, bodyName, typeOf, decisionState } from './case.js';
import { rankList, weekly, bindTips, bar } from './viz.js';
import { Matrix } from './matrix.js';

const WHO = 'qs.who', BUDGET = 'qs.budget';
export const HATCH_COV = 0.25, HATCH_TITLE = 0.5;
const ls = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };

export class Board {
  constructor(root, { topic, picker = true, pult = true, order = 'date', head = null, onChange } = {}) {
    this.root = root; this.tp = topic; this.order = order; this.onChange = onChange;
    this.S = { brush: null, body: null, f: { type: '', status: '', party: '', q: '' }, mode: 'list', tab: 'neu', sel: null, pw: null };
    const L = t();
    this.work = h('div', { class: 'work' });
    // map column
    this.mapcol = h('div', { class: 'pane mapcol' });
    if (head) this.mapcol.append(head);
    if (picker) {
      const pr = h('div', { class: 'picker' });
      this.picker = new Picker(pr, { onPick: tp => this.setTopic(tp) });
      this.modeEl = h('span', { class: 'mmode' });
      this.mapcol.append(h('div', { class: 'topicrow' }, pr, this.modeEl));
    }
    this.tsub = h('p', { class: 'tsub' }); this.mapcol.append(this.tsub);
    this.mapEl = h('div', { class: 'map', id: `map-${Math.random().toString(36).slice(2, 7)}` }); this.mapcol.append(this.mapEl);
    this.legend = h('p', { class: 'legend' }); this.mapcol.append(this.legend);
    this.mxEl = h('div', { class: 'matrix', hidden: true }); this.mapEl.after(this.mxEl);
    this.mapMode = 'map';
    this.tlEl = h('div', { class: 'tl' }); this.mapcol.append(this.tlEl);
    // register
    this.reg = h('section', { class: 'register', 'aria-label': 'Liste' });
    this.lhead = h('div', { class: 'lhead' });
    this.tabs = h('div', { class: 'tabs', role: 'tablist' });
    this.pline = h('p', { class: 'pline' });
    this.filters = h('div', { class: 'filters' });
    this.vl = h('div', { class: 'vlist' });
    this.count = h('div', { class: 'count' });
    this.reg.append(this.lhead, this.tabs, this.pline, this.filters, this.vl, this.count);
    this.pultAllowed = pult; this.pultOn = pult;
    // case
    this.case = h('section', { class: 'case', 'aria-label': 'Geschäft', tabindex: '-1' });
    this.case.addEventListener('close', () => this.select(null));
    this.work.append(this.mapcol, this.reg, this.case);
    root.append(this.work);
    this.map = new SwissMap(this.mapEl, { onClick: k => { this.S.body = k && k !== this.S.body ? k : null; this.refresh(); } });
    this.tl = new Timeline(this.tlEl, { onBrush: b => { this.S.brush = b; this.refresh(); } });
    this.matrix = new Matrix(this.mxEl, this);
    this.list = new VList(this.vl, { render: i => this.row(i), onOpen: p => this.openPos(p) });
    this.buildFilters();
    if (this.picker) this.picker.set(topic);
    this.items = [];
  }

  // ------------------------------------------------------------ filters
  buildFilters() {
    const L = t(), c = D.c, F = this.S.f;
    const opts = (vals) => [...vals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 60).map(([v]) => v);
    const types = new Map(), states = new Map(), parties = new Map();
    const scope = this.tp && this.tp.scope;
    for (let i = 0; i < D.n; i++) {
      if (scope && c.body[i] !== scope) continue;
      const ty = typeOf(i); if (ty) types.set(ty, (types.get(ty) || 0) + 1);
      const st = c.state[i]; if (st) states.set(st, (states.get(st) || 0) + 1);
      const pa = c.party[i]; if (pa) parties.set(pa, (parties.get(pa) || 0) + 1);
    }
    const sel = (key, label, vals) => {
      const s = h('select', { 'aria-label': label }, h('option', { value: '' }, L.all), opts(vals).map(v => h('option', { value: v, selected: F[key] === v }, v)));
      s.addEventListener('change', () => { F[key] = s.value; this.refresh(); });
      return h('div', { class: 'fl' }, h('label', { class: 'k' }, label), s);
    };
    this.q = h('input', { type: 'search', placeholder: L.searchPh, value: F.q, 'aria-label': L.search });
    this.q.addEventListener('input', debounce(() => { F.q = this.q.value; this.refresh(); }, 120));
    this.q.addEventListener('keydown', e => { if (e.key === 'Escape') { this.q.blur(); e.stopPropagation(); } if (e.key === 'Enter') { this.q.blur(); this.vl.focus(); } });
    this.filters.replaceChildren(sel('type', L.type, types), sel('status', L.status, states), sel('party', L.party, parties),
      h('div', { class: 'fl' }, h('label', { class: 'k' }, L.search), this.q));
    const tp = this.tp;
    if (tp && tp.kind === 'be') {
      const cnt = new Map(); for (let i = 0; i < D.n; i++) if (c.be[i] != null) cnt.set(c.be[i], (cnt.get(c.be[i]) || 0) + 1);
      const ds = h('select', { 'aria-label': L.dir }, h('option', { value: '' }, L.all),
        tp.options.map(o => h('option', { value: o.code, selected: F.dir === o.code }, `${o.abbr[UI.lang] || o.abbr.de} · ${o.name[UI.lang] || o.name.de} (${num(cnt.get(o.code) || 0)})`)));
      ds.addEventListener('change', () => { F.dir = ds.value; this.refresh(); });
      this.filters.prepend(h('div', { class: 'fl wide' }, h('label', { class: 'k' }, L.dir), ds));
    }
  }
  passMask() {
    const c = D.c, F = this.S.f, n = D.n, m = new Uint8Array(n);
    const qs = F.q ? F.q.split('|').map(norm).filter(Boolean) : null;
    for (let i = 0; i < n; i++) {
      if (F.type && typeOf(i) !== F.type) continue;
      if (F.status && c.state[i] !== F.status) continue;
      if (F.party && c.party[i] !== F.party) continue;
      if (qs) { const hay = norm(`${c.title[i]} ${c.submitter[i]} ${c.number[i] || ''} ${bodyName(c.body[i])}`); if (!qs.some(q => hay.includes(q))) continue; }
      m[i] = 1;
    }
    return m;
  }

  // ------------------------------------------------------------ topic
  setTopic(tp) {
    this.tp = tp; this.S.sel = null; this.S.body = tp && tp.scope ? tp.scope : null; this.S.f.dir = '';
    if (this.picker) this.picker.set(tp);
    this.buildFilters(); this.refresh(); this.renderCase();
  }

  // ------------------------------------------------------------ compute + render everything
  refresh() {
    const tp = this.tp, c = D.c, n = D.n, S = this.S, L = t();
    const isBe = tp && tp.kind === 'be';
    if (tp && tp.scope) S.body = tp.scope;
    const mask = this.mask = this.passMask();
    const br = S.brush, inP = i => !br || (c.week[i] >= br[0] && c.week[i] <= br[1]);
    const stats = new Map();
    const counts = [new Int32Array(D.nWeeks), new Int32Array(D.nWeeks), new Int32Array(D.nWeeks)];
    const checks = [new Int32Array(D.nWeeks), new Int32Array(D.nWeeks), new Int32Array(D.nWeeks)];
    const tabsN = { neu: 0, todo: 0, ok: 0, changed: 0, done: 0 };
    const items = [];
    const isAll = tp && tp.kind === 'all';
    this.pultOn = this.pultAllowed && tp && tp.kind !== 'all' && tp.kind !== 'live';
    const lastW = Math.floor((D.dmax - D.w0) / 7);
    // the Pult's week: by default the newest week (up to today) with a hit of this topic
    if (S.pw == null || S.pwFor !== (tp && tp.id)) {
      let w = -1; if (tp) for (let i = 0; i < n; i++) if (c.week[i] <= lastW && c.week[i] > w && tp.scored(i) && tp.hit(i)) w = c.week[i];
      S.pw = w >= 0 ? w : lastW; S.pwFor = tp && tp.id;
    }
    let scoredSel = 0, hitsSel = 0;
    const lv = [{ n: 0, hits: 0 }, { n: 0, hits: 0 }, { n: 0, hits: 0 }, { n: 0, hits: 0 }];
    const stat = k => { let st = stats.get(k); if (!st) stats.set(k, st = { n: 0, hits: 0, check: 0 }); return st; };
    const pult = S.mode === 'pult' && this.pultOn;
    for (let i = 0; tp && i < n; i++) {
      const sc = tp.scored(i); if (!sc) continue;
      const k = c.body[i];
      if (isAll && inP(i)) { stat(k).n++; lv[c.lvl[i]].n++; if (!S.body || k === S.body) scoredSel++; } // denominators ignore the search
      if (!mask[i]) continue;
      if (isBe && S.f.dir && c.be[i] !== S.f.dir) continue;
      const hit = tp.hit(i), chk = tp.check(i);
      const inB = !S.body || k === S.body;
      const dec = getDec(tp, c.id[i]);
      if (hit && inB && c.lvl[i] < 3) counts[c.lvl[i]][c.week[i]]++;
      if (chk && !dec && inB && c.lvl[i] < 3) checks[c.lvl[i]][c.week[i]]++;
      // «neu diese Woche»: every undecided hit begun in the Pult's week (the brush does not apply)
      if (inB && hit && !dec && c.week[i] === S.pw) { tabsN.neu++; if (pult && S.tab === 'neu') items.push(i); }
      if (!inP(i)) continue;
      const st = stat(k);
      if (!isAll) st.n++;
      if (hit) st.hits++; if (chk && !dec) st.check++;
      if (!isAll) lv[c.lvl[i]].n++; if (hit) lv[c.lvl[i]].hits++;
      if (!inB) continue;
      if (!isAll) scoredSel++; if (hit) hitsSel++;
      const todo = chk && !dec; // one definition everywhere: undecided rows in the please_check lane
      if (todo) tabsN.todo++;
      if (dec && dec.d === 'confirmed') tabsN.ok++;
      const changed = dec && dec.d === 'confirmed' && dec.state != null && dec.state !== c.state[i];
      if (changed) tabsN.changed++;
      if (dec) tabsN.done++;
      if (pult) {
        if ((S.tab === 'todo' && todo) || (S.tab === 'ok' && dec && dec.d === 'confirmed') || (S.tab === 'changed' && changed) || (S.tab === 'done' && dec)) items.push(i);
      } else if (hit) items.push(i);
    }
    if (this.order === 'arrival' && tp && tp.dec) {
      const rank = new Map(); let r = 0; for (const id of tp.dec.keys()) rank.set(id, r++);
      items.sort((a, b) => rank.get(c.id[b]) - rank.get(c.id[a]));
    } else if (pult && S.tab === 'neu') {
      items.sort((a, b) => ((tp.check(b) ? 1 : 0) - (tp.check(a) ? 1 : 0)) || (c.day[b] - c.day[a]) || (c.id[b] - c.id[a]));
    } else if (isBe) {
      const k = i => (tp.opt.get(c.be[i]) || { k: 99 }).k;
      items.sort((a, b) => (k(a) - k(b)) || (c.day[b] - c.day[a]) || (c.id[b] - c.id[a]));
    } else items.sort((a, b) => (c.day[b] - c.day[a]) || (c.id[b] - c.id[a]));
    // ramp + coverage
    for (const [k, st] of stats) st.share = st.n ? st.hits / st.n : 0;
    const breaks = rampBreaks([...stats.values()].map(x => x.share));
    this.maxShare = Math.max(0, ...[...stats.values()].map(x => x.share));
    const all = new Map();
    for (const b of D.bodies) {
      const st = stats.get(b.key) || { n: 0, hits: 0, check: 0, share: 0 };
      // coverage: scored in the period / affairs in the period where the export carries monthly counts (n_by_month),
      // else the body's scored share overall
      let cov = null;
      if (b.n_by_month) {
        const a = isoOfDay(br ? D.w0 + br[0] * 7 : D.dmin).slice(0, 7), z = isoOfDay(br ? D.w0 + br[1] * 7 + 6 : D.dmax).slice(0, 7);
        let pop = 0; for (const [m, v] of Object.entries(b.n_by_month)) if (m >= a && m <= z) pop += v;
        cov = pop ? Math.min(1, st.n / pop) : null;
      } else cov = tp && tp.coverage ? tp.coverage(b) : null;
      st.cov = cov;
      st.hatch = !st.n || (cov != null && cov < HATCH_COV) || (b.title_only_share != null && b.title_only_share >= HATCH_TITLE);
      st.cls = st.hatch && !st.hits ? 0 : rampClass(st.share, breaks);
      all.set(b.key, st);
    }
    this.counts = counts; this.checks = checks;
    this.stats = all; this.breaks = breaks; this.lv = lv; this.tabsN = tabsN; this.lastW = lastW;
    this.items = items;
    // identical title + parliament + date in a row → one line with a count; decisions apply to the whole group
    const rows = [], posOf = new Map();
    const byKey = new Map();
    for (const i of items) {
      const key = this.order === 'arrival' ? null : `${c.body[i]}|${c.day[i]}|${c.title[i]}`;
      const at = key != null ? byKey.get(key) : undefined;
      if (at != null) { rows[at].push(i); posOf.set(i, at); continue; }
      rows.push([i]); posOf.set(i, rows.length - 1); if (key != null) byKey.set(key, rows.length - 1);
    }
    this.rows = rows; this.posOf = posOf;
    this.map.update(all, S.body);
    if (this.mapMode === 'matrix') this.matrix.render();
    const selRow = S.sel != null ? D.rowOf.get(S.sel) : null;
    this.tl.set(counts, S.brush, selRow != null ? { w: c.week[selRow], l: Math.min(2, c.lvl[selRow]) } : null, checks);
    // list
    const pos = selRow != null && posOf.has(selRow) ? posOf.get(selRow) : -1;
    this.list.set(rows, pos);
    this.renderHead(scoredSel, hitsSel); this.renderMode();
    if (S.sel == null) this.summary(); // the «Auswahl» panel follows the brush and filters
    this.onChange && this.onChange(this);
  }

  renderHead(scoredSel, hitsSel) {
    const L = t(), S = this.S, tp = this.tp;
    const name = tp ? (tp.names[UI.lang] || tp.names.de) : '';
    const bsel = S.body ? D.B.get(S.body) : null;
    const per = S.brush ? `${isoOfDay(D.w0 + S.brush[0] * 7)} – ${isoOfDay(D.w0 + S.brush[1] * 7 + 6)}` : `${isoOfDay(D.dmin)} – ${isoOfDay(D.dmax)}`;
    this.tsub.innerHTML = '';
    const isBe = tp && tp.kind === 'be';
    if (isBe) {
      const o = S.f.dir ? tp.opt.get(S.f.dir) : null;
      this.tsub.append(h('b', {}, num(hitsSel)), ` ${L.affairs} · ${L.dir}: ${o ? `${o.abbr[UI.lang] || o.abbr.de} ${o.name[UI.lang] || o.name.de}` : L.all} · ${per}`);
    } else if (tp && tp.kind === 'all') {
      this.tsub.append(h('b', {}, num(hitsSel)), ` ${L.affairs}${S.f.q || S.f.type || S.f.status || S.f.party ? ` ${L.of} ${num(scoredSel)} · ${pct(scoredSel ? hitsSel / scoredSel : NaN)}` : ''} · ${per}`,
        bsel ? h('span', {}, ' · ', h('b', {}, bodyName(S.body)), ' ', h('button', { class: 'tb', type: 'button', onclick: () => { S.body = null; this.refresh(); } }, `[${L.clear}]`)) : '',
        S.brush ? h('span', {}, ' ', h('button', { class: 'tb', type: 'button', onclick: () => { S.brush = null; this.refresh(); } }, `[${L.reset}]`)) : '');
    } else this.tsub.append(h('b', {}, num(hitsSel)), ` ${L.hits} ${L.of} ${num(scoredSel)} ${L.scored} · ${pct(scoredSel ? hitsSel / scoredSel : NaN)} · ${per}`,
      ' · ', h('span', { class: this.tabsN.todo ? 'sig' : '' }, `${L.pending} ${num(this.tabsN.todo)}`),
      bsel ? h('span', {}, ' · ', h('b', {}, bodyName(S.body)), tp && tp.scope ? '' : h('span', {}, ' ', h('button', { class: 'tb', type: 'button', onclick: () => { S.body = null; this.refresh(); } }, `[${L.clear}]`))) : '',
      S.brush ? h('span', {}, ' ', h('button', { class: 'tb', type: 'button', onclick: () => { S.brush = null; this.refresh(); } }, `[${L.reset}]`)) : '');
    // legend
    const br = this.breaks;
    const ramp = h('span', { class: 'ramp' }, [1, 2, 3, 4, 5].slice(0, Math.max(1, br.length)).map(k => h('span', { class: 'sw', style: `background:var(--r${k})` })));
    this.legend.replaceChildren(
      isBe ? '' : h('span', {}, `${L.ramp} `, ramp, br.length ? ` ${pct(br[0])} … ${pct(this.maxShare)}` : ' –'),
      isBe ? '' : h('span', {}, h('span', { class: 'sw', style: 'background:var(--r0)' }), '0'),
      h('span', { html: `<svg width="14" height="10" viewBox="0 0 14 10" style="vertical-align:-1px;margin-right:4px;border:1px solid var(--ink);box-sizing:content-box"><defs><pattern id="lg-h" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" style="stroke:var(--hatch);stroke-width:1.2"/></pattern></defs><rect width="14" height="10" fill="url(#lg-h)"/></svg>${L.hatch}` }),
      h('span', {}, h('span', { class: 'tk' }), L.tick));
    // list header: mode toggle, Pult tabs, Pult line
    const N = this.tabsN;
    this.lhead.hidden = !this.pultOn;
    if (this.pultOn) {
      const mk = (m, lab) => h('button', { class: 'tb', type: 'button', 'aria-pressed': String(S.mode === m), onclick: () => this.setMode(m) }, lab);
      this.lhead.replaceChildren(mk('list', `${L.list}`), mk('pult', `${L.pult}`), h('span', { class: 'sp' }, '[l]'));
      this.tabs.hidden = S.mode !== 'pult'; this.pline.hidden = S.mode !== 'pult';
      if (S.mode === 'pult') {
        const tab = (k) => h('button', { class: `tab ${(k === 'todo' || k === 'neu') && N[k] ? 'need' : ''}`, role: 'tab', type: 'button', 'aria-selected': String(S.tab === k), onclick: () => { S.tab = k; S.sel = null; this.refresh(); this.renderCase(); } },
          h('span', { class: 't' }, L.tabs[k]), h('span', { class: 'c' }, num(N[k])));
        this.tabs.replaceChildren(tab('neu'), tab('todo'), tab('ok'), tab('changed'), tab('done'));
        const [y, wk] = isoWeek(D.w0 + S.pw * 7);
        const budget = +(ls(BUDGET) || 25);
        const bi = h('input', { type: 'text', inputmode: 'numeric', value: budget, 'aria-label': L.budget });
        bi.addEventListener('change', () => { const v = parseInt(bi.value, 10); if (v > 0) ls(BUDGET, String(v)); this.refresh(); });
        const wb = (d, lab) => h('button', { class: 'tb', type: 'button', disabled: (d < 0 ? S.pw <= 0 : S.pw >= this.lastW) || null, onclick: () => this.stepWeek(d) }, lab);
        this.pline.replaceChildren(wb(-1, '[‹]'), ' ', h('b', {}, `${L.week} ${wk} ${y}`), ` (${isoOfDay(D.w0 + S.pw * 7).slice(5).split('-').reverse().join('.')}.–${isoOfDay(D.w0 + S.pw * 7 + 6).slice(5).split('-').reverse().join('.')}.) `, wb(1, '[›]'),
          ` · ${L.newW} ${num(N.neu)} · `, h('span', { class: N.todo ? 'sig' : '' }, `${L.pending} ${num(N.todo)}`), ` · ${L.budget} `, bi, L.perWeek);
      }
    } else { this.lhead.hidden = true; this.tabs.hidden = true; this.pline.hidden = true; }
    this.count.replaceChildren(h('span', {}, `${num(this.items.length)} ${L.affairs}${this.rows.length !== this.items.length ? ` · ${num(this.rows.length)} ${L.lines}` : ''}`),
      h('span', { class: 'sp' }, h('button', { class: 'tb', type: 'button', onclick: () => this.exportCsv() }, `[e] ${L.export}`)));
  }

  setMapMode(m) {
    this.mapMode = m;
    this.mapEl.hidden = m === 'matrix'; this.legend.hidden = m === 'matrix'; this.mxEl.hidden = m !== 'matrix';
    if (m === 'matrix') this.matrix.render();
    this.renderMode();
    this.onChange && this.onChange(this);
  }
  renderMode() {
    if (!this.modeEl) return;
    const L = t(), mk = (m, lab) => h('button', { class: 'tb mono', type: 'button', 'aria-pressed': String(this.mapMode === m), onclick: () => this.setMapMode(m) }, lab);
    this.modeEl.replaceChildren(mk('map', L.mapMode), ' ', mk('matrix', L.matrix), h('span', { class: 'dim' }, ' [x]'));
  }
  relang() { this.buildFilters(); if (this.picker) this.picker.set(this.tp); this.refresh(); this.renderCase(); }

  setMode(m) { this.S.mode = m; this.S.sel = null; this.refresh(); this.renderCase(); }
  stepWeek(d) { const S = this.S; S.pw = Math.max(0, Math.min(this.lastW, S.pw + d)); S.pwFor = this.tp && this.tp.id; S.sel = null; this.refresh(); this.renderCase(); }

  row(g) {
    const i = g[0], c = D.c, tp = this.tp, L = t();
    const dec = tp ? getDec(tp, c.id[i]) : null, chk = tp && tp.check(i);
    const sub = c.submitter[i] ? `${c.submitter[i]}${c.party[i] ? ` (${c.party[i]})` : ''}` : '';
    const meta = [fmtDate(c.date[i]), bodyName(c.body[i], false), typeOf(i), sub, c.state[i]].filter(Boolean).join(' · ');
    const p = tp ? tp.p(i) : NaN;
    const mark = dec ? (dec.d === 'confirmed' ? '✓' : '–') : chk ? '!' : '';
    return h('div', { class: dec ? 'dec' : '' },
      h('div', { class: 'tc' }, h('div', { class: 't', lang: c.lang[i] }, c.title[i]), h('div', { class: 'm' }, g.length > 1 ? h('b', { class: 'grpn' }, `×${g.length} `) : '', meta)),
      h('div', { class: 'p' }, tp && tp.kind === 'be' ? beAbbr(tp, c.be[i]) : Number.isNaN(p) ? '' : [p3(p), h('span', { class: 'pc' }, h('span', { style: `width:${Math.round(Math.max(0, Math.min(1, p)) * 40)}px` }))]),
      h('div', { class: `x ${dec ? 'd' : ''}`, 'aria-label': chk && !dec ? L.lanes.please_check : null }, dec ? `[${mark}]` : chk ? h('span', { class: 'rtick' }) : ''));
  }

  // ------------------------------------------------------------ selection + case
  openPos(p) { const g = this.rows[p]; if (!g) return; const i = g[0]; this.select(D.c.id[i]); if (matchMedia('(max-width:899px)').matches) this.case.scrollIntoView({ block: 'start' }); }
  select(id, { focus = false } = {}) {
    this.S.sel = id;
    const row = id != null ? D.rowOf.get(id) : null;
    const pos = row != null && this.posOf.has(row) ? this.posOf.get(row) : -1;
    this.list.select(pos);
    this.work.classList.toggle('case-open', id != null);
    const c = D.c;
    this.tl.set(this.tl.counts, this.S.brush, row != null ? { w: c.week[row], l: Math.min(2, c.lvl[row]) } : null);
    this.renderCase();
    this.onChange && this.onChange(this);
    if (focus) this.case.focus();
  }
  step(d) {
    if (!this.rows.length) return;
    const row = this.S.sel != null ? D.rowOf.get(this.S.sel) : null;
    let pos = row != null && this.posOf.has(row) ? this.posOf.get(row) : -1;
    pos = Math.max(0, Math.min(this.rows.length - 1, pos + d));
    this.select(D.c.id[this.rows[pos][0]]);
  }
  renderCase() {
    const id = this.S.sel, root = this.case;
    root.dataset.id = id == null ? '' : String(id);
    if (id == null) { this.summary(); return; }
    const i = D.rowOf.get(id);
    if (i == null) { root.replaceChildren(h('p', { class: 'empty' }, `#${id}`)); return; }
    this.pend = null; this.corr = null;
    renderCase(root, i, this.tp, { onOpen: j => this.select(D.c.id[j]), decideBar: this.decideBar(i), group: this.groupOf(i) });
  }
  decideBar(i) {
    const L = t(), id = D.c.id[i], tp = this.tp;
    if (!tp || tp.kind === 'all') return null;
    const b = (k, key, lab) => h('button', { class: 'box', type: 'button', onclick: () => this.decide(k) }, h('span', { class: 'k' }, `[${key}] `), lab);
    const who = h('input', { type: 'text', value: ls(WHO) || '', 'aria-label': L.who, placeholder: L.whoAsk });
    who.addEventListener('change', () => ls(WHO, who.value.trim()));
    who.addEventListener('keydown', e => { if (e.key === 'Enter') { ls(WHO, who.value.trim()); who.blur(); } });
    this.who = who;
    this.st = h('div', { class: 'st', 'aria-live': 'polite' });
    const bar = h('div', { class: 'decide' }, h('div', { class: 'btns' }, b('confirmed', '1', L.accept), b('rejected', '2', L.reject), b('skip', '0', L.skip)),
      h('div', { class: 'who' }, L.who, who), this.st);
    this.stateLine(i);
    return bar;
  }
  // the one mono state line under the buttons: decision, pending overwrite, correction choices
  stateLine(i, extra) {
    const L = t(), tp = this.tp, st = this.st; if (!st || !tp) return;
    const id = D.c.id[i], dec = getDec(tp, id), grp = this.groupOf(i);
    st.replaceChildren();
    if (extra) { st.append(extra); return; }
    if (dec) {
      st.innerHTML = decisionState(tp, id);
      st.append(' · ', h('button', { class: 'tb', type: 'button', onclick: () => this.undo() }, `[u] ${L.undo}`));
    } else if (grp.length > 1) st.textContent = `[1] [2] ${L.sameDec(grp.length)}`;
    if (tp.kind === 'chapter' && !tp.hit(i)) st.append(h('span', { class: 'dim' }, `${st.textContent ? ' · ' : ''}${L.notSuggested}`));
  }
  groupOf(row) { return this.posOf && this.posOf.has(row) ? this.rows[this.posOf.get(row)] : [row]; }
  who_() {
    const L = t(), by = (this.who && this.who.value.trim()) || ls(WHO) || '';
    if (!by) { const w = this.case.querySelector('.who'); if (w) { w.classList.add('ask'); w.querySelector('input').focus(); } toast(L.whoAsk); }
    else ls(WHO, by);
    return by;
  }
  async post(aid, code, scheme, action, by) {
    if (!API.live) return {};
    try {
      const r = await apiPost(`/affairs/${aid}/topics/${encodeURIComponent(code)}/${action}`, { by, scheme });
      return { api: true, row: r && (r.valid_from || r.confirmed_at) ? { valid_from: r.valid_from, confirmed_at: r.confirmed_at } : null };
    } catch (e) { return { err: String(e.message || e) }; }
  }
  async decide(kind) {
    const id = this.S.sel, tp = this.tp, L = t(), c = D.c;
    if (id == null || !tp || tp.kind === 'all') return;
    if (this.corr) { this.corr = null; }
    if (kind === 'skip') { this.pend = null; this.step(1); return; }
    if (kind === 'undo') return this.undo();
    const row = D.rowOf.get(id), group = this.groupOf(row), pos = this.posOf.get(row);
    if (tp.kind === 'chapter' && !tp.hit(row)) { this.stateLine(row, h('span', { class: 'sig' }, L.notSuggested)); return; }
    // never overwrite a decision silently: the same key twice confirms
    const cur = getDec(tp, id);
    if (cur && cur.d !== kind && !(this.pend && this.pend.id === id && this.pend.kind === kind)) {
      this.pend = { id, kind };
      this.stateLine(row, h('span', { class: 'sig' }, L.overwrite(L.decided[cur.d] || cur.d, cur.by || '–', fmtWhen(cur.at), kind === 'confirmed' ? '1' : '2')));
      return;
    }
    this.pend = null;
    const by = this.who_(); if (!by) return;
    const at = new Date().toISOString();
    for (const j of group) { // one key decides every affair of a group of identical affairs
      const aid = c.id[j], code = tp.codeOf ? tp.codeOf(j) : tp.code;
      const rec = { d: kind, by, at, state: c.state[j], n: group.length, ...(await this.post(aid, code, tp.scheme, kind === 'confirmed' ? 'confirm' : 'reject', by)) };
      setDec(tp, aid, rec);
    }
    this.last = { id, tp };
    await syncDecisions();
    // a rejection in a scheme with alternatives offers the corrected code on number keys
    if (kind === 'rejected' && (tp.kind === 'chapter' || tp.kind === 'be')) { this.refresh(); this.select(id); await this.offerCorrection(row); return; }
    this.refresh();
    const stillThere = this.posOf.has(row);
    const next = this.rows[stillThere ? pos + 1 : pos];
    this.select(next ? c.id[next[0]] : id);
  }
  async offerCorrection(row) {
    const L = t(), tp = this.tp, c = D.c, id = c.id[row];
    let alts = [];
    if (tp.kind === 'be') alts = tp.options.filter(o => o.code !== c.be[row]).map(o => ({ code: `be:${o.code}`, scheme: 'be-directorates', key: o.code, label: `${o.abbr[UI.lang] || o.abbr.de} ${o.name[UI.lang] || o.name.de}` }));
    else {
      const d = await detail(id), ranks = (d && d.aps && d.aps.rank) || [];
      alts = ranks.filter(r => r !== tp.idx && D.scheme.chapters[r]).map(r => { const ch = D.scheme.chapters[r]; return { code: ch.code, scheme: 'aps', label: UI.lang === 'fr' ? ch.fr || ch.de : ch.de }; });
    }
    if (!alts.length) { this.step(1); return; }
    this.corr = { id, row, alts: alts.slice(0, 9) };
    this.stateLine(row, h('span', {}, h('b', {}, `${L.correct}: `), ...this.corr.alts.flatMap((a, k) => [h('button', { class: 'tb', type: 'button', onclick: () => this.pickCorrection(k + 1) }, `[${k + 1}] ${a.label}`), ' · ']), h('span', { class: 'dim' }, `[0] ${L.noCorrection}`)));
  }
  async pickCorrection(k) {
    const cr = this.corr; if (!cr) return;
    this.corr = null;
    const c = D.c, L = t(), tp = this.tp, row = cr.row, pos = this.posOf.get(row);
    if (!k) { this.refresh(); const next = this.rows[this.posOf.has(row) ? pos + 1 : pos]; this.select(next ? c.id[next[0]] : cr.id); return; }
    const a = cr.alts[k - 1]; if (!a) return;
    const by = this.who_(); if (!by) return;
    const at = new Date().toISOString();
    for (const j of this.groupOf(row)) {
      const aid = c.id[j], res = await this.post(aid, a.code, a.scheme, 'confirm', by);
      if (tp.kind === 'be') setDec(tp, aid, { d: 'confirmed', by, at, state: c.state[j], code: a.key, corr: true, ...res });
      else {
        const cur = getDec(tp, aid); if (cur) setDec(tp, aid, { ...cur, corr: a.code });
        const t2 = TOPIC_BY_ID.get(a.code); if (t2) setDec(t2, aid, { d: 'confirmed', by, at, state: c.state[j], corr: true, ...res });
      }
    }
    await syncDecisions();
    toast(`${L.corrected} → ${a.label}`);
    this.refresh();
    const next = this.rows[this.posOf.has(row) ? pos + 1 : pos];
    this.select(next ? c.id[next[0]] : cr.id);
  }
  // u: undo the selected row's decision; with an undecided row selected, the last decision of this session
  async undo() {
    const L = t(), c = D.c;
    let tp = this.tp, id = this.S.sel;
    if (id == null || !getDec(tp, id)) { if (!this.last) return; ({ id, tp } = this.last); }
    const row = D.rowOf.get(id); if (row == null) return;
    const dec = getDec(tp, id); if (!dec) return;
    const by = this.who_() || dec.by;
    let note = '';
    for (const j of this.groupOf(row)) {
      const aid = c.id[j], code = tp.kind === 'be' ? `be:${(getDec(tp, aid) || {}).code || c.be[j]}` : (tp.codeOf ? tp.codeOf(j) : tp.code);
      if (API.live) {
        const r = await this.post(aid, code, tp.scheme, 'undo', by);
        if (r.err) note = L.undoLocal;
      }
      setDec(tp, aid, null);
    }
    this.last = null;
    await syncDecisions();
    this.refresh(); this.select(id);
    if (note) this.stateLine(row, h('span', { class: 'sig' }, note));
  }

  // Überblick (nothing selected): weeks by level with the please-check share in red, the parliaments as a ranked bar
  // list (hatched where coverage is low), a few notable affairs. Every element filters or opens.
  summary() {
    const L = t(), tp = this.tp, root = this.case, S = this.S, c = D.c;
    const name = tp ? (tp.names[UI.lang] || tp.names.de) : '';
    const sc = h('div', { class: 'scroll' });
    root.replaceChildren(sc);
    const per = S.brush ? `${isoOfDay(D.w0 + S.brush[0] * 7)} – ${isoOfDay(D.w0 + S.brush[1] * 7 + 6)}` : `${isoOfDay(D.dmin)} – ${isoOfDay(D.dmax)}`;
    sc.append(h('div', { class: 'sl' }, L.overview, h('span', { class: 'sp' }, `${name} · ${per}`)));
    if (tp && tp.kind === 'be') { this.beSummary(sc); bindTips(sc); return; }
    if (!this.items.length) { sc.append(h('p', { class: 'empty' }, L.none)); return; }
    const wl = w => { const [y, k] = isoWeek(D.w0 + w * 7); return `${L.week} ${k} ${y}`; };
    // (b) parliaments
    const top = [...this.stats].filter(([, x]) => x.hits).sort((a, b) => (b[1].hits - a[1].hits) || (b[1].share - a[1].share)).slice(0, 10);
    const mx = Math.max(...top.map(([, x]) => x.share), 1e-9);
    sc.append(h('div', { class: 'ov' }, h('div', { class: 'dgh' }, h('span', {}, L.topParl), h('span', { class: 'dim' }, L.share)),
      rankList(top.map(([k, x]) => ({ label: shortName(k), v: x.share / mx, tone: x.hatch ? 'hatch' : (k === S.body ? 'ink' : 'grey'), strong: k === S.body,
        value: `${num(x.hits)} · ${pct(x.share)}`, mark: x.check ? L.pending : null,
        tip: `${bodyName(k)} · ${num(x.hits)} ${L.of} ${num(x.n)} · ${pct(x.share)} · ${L.coverage} ${pct(x.cov)}${x.check ? ` · ${L.pending} ${num(x.check)}` : ''}`,
        onClick: () => { S.body = S.body === k ? null : k; this.refresh(); } })))));
    // (c) notable: the newest week with hits on two or more levels (best p per level), then the newest confident hits
    const pick = [], seen = new Set(), P = i => (tp ? tp.p(i) : NaN);
    const byW = new Map();
    for (const i of this.items) { if (c.lvl[i] > 2) continue; const w = c.week[i]; if (!byW.has(w)) byW.set(w, [null, null, null]); const a = byW.get(w); const l = c.lvl[i]; if (a[l] == null || (P(i) || 0) > (P(a[l]) || 0)) a[l] = i; }
    for (const w of [...byW.keys()].sort((a, b) => b - a)) { const a = byW.get(w).filter(x => x != null); if (a.length >= 2) { a.forEach(i => { pick.push([i, `${L.acrossLv(a.length)} · ${wl(w)}`]); seen.add(i); }); break; } }
    for (const i of this.items) { if (pick.length >= 5) break; if (seen.has(i)) continue; if (Number.isNaN(P(i)) || P(i) >= 0.99) { pick.push([i, `${L.newest}${Number.isNaN(P(i)) ? '' : ` · p ${p3(P(i))}`}`]); seen.add(i); } }
    const nl = h('div', { class: 'ov' }, h('div', { class: 'dgh' }, h('span', {}, L.notable)));
    for (const [i, why] of pick) nl.append(h('button', { class: 'nt-a', type: 'button', lang: c.lang[i], onclick: () => this.select(c.id[i]) },
      h('span', { class: 't' }, c.title[i]), h('span', { class: 'm' }, `${fmtDate(c.date[i])} · ${bodyName(c.body[i])} · ${why}`)));
    sc.append(nl);
    bindTips(sc);
  }

  beSummary(sc) {
    const L = t(), tp = this.tp, c = D.c, cnt = new Map(), chk = new Map();
    for (const i of this.items) { const k = c.be[i]; cnt.set(k, (cnt.get(k) || 0) + 1); if (tp.check(i) && !getDec(tp, c.id[i])) chk.set(k, (chk.get(k) || 0) + 1); }
    const mx = Math.max(1, ...cnt.values());
    sc.append(h('div', { class: 'ov' }, h('div', { class: 'dgh' }, h('span', {}, L.beGroup)),
      rankList(tp.options.map(o => ({ label: `${o.abbr[UI.lang] || o.abbr.de} · ${o.name[UI.lang] || o.name.de}`, v: (cnt.get(o.code) || 0) / mx,
        tone: this.S.f.dir === o.code ? 'ink' : 'grey', strong: this.S.f.dir === o.code, value: num(cnt.get(o.code) || 0), mark: chk.get(o.code) ? L.pending : null,
        tip: `${o.name[UI.lang] || o.name.de} · ${num(cnt.get(o.code) || 0)}${chk.get(o.code) ? ` · ${L.pending} ${num(chk.get(o.code))}` : ''}`,
        onClick: () => { this.S.f.dir = this.S.f.dir === o.code ? '' : o.code; this.buildFilters(); this.refresh(); } })))));
  }

  // ------------------------------------------------------------ export: CSV in the DVS list's columns + method line
  async exportCsv() {
    const L = t(), tp = this.tp, c = D.c, items = this.items;
    if (!tp) return;
    const det = new Map(), chunks = [...new Set(items.map(i => Math.floor(c.id[i] / 1000)))];
    for (let a = 0; a < chunks.length; a += 6) // a few chunk files at a time
      await Promise.all(chunks.slice(a, a + 6).map(k => detail(c.id[items.find(i => Math.floor(c.id[i] / 1000) === k)])));
    for (const i of items) det.set(i, await detail(c.id[i]));
    const fr = UI.lang === 'fr';
    const LV = fr ? ['Confédération', 'Canton', 'Commune', 'Liechtenstein'] : ['Bund', 'Kanton', 'Gemeinde', 'Liechtenstein'];
    const head = fr ? ['Date', 'Niveau', 'Canton', 'Parlement', 'Numéro', 'Titre', 'Langue', 'Type', 'Statut', 'Auteur·e', 'Parti', 'Lien',
      'Thème', 'p', 'Voie', 'Décision', 'Décidé par', 'Décidé le', 'ID OPD', 'Build']
      : ['Datum', 'Ebene', 'Kanton', 'Parlament', 'Geschäftsnummer', 'Titel', 'Sprache', 'Typ', 'Status', 'Urheber/in', 'Partei', 'Link',
      'Thema', 'p', 'Spur', 'Entscheid', 'Entschieden von', 'Entschieden am', 'OPD-ID', 'Build'];
    const tname = tp.kind === 'be' ? null : (tp.names[UI.lang] || tp.names.de);
    const q = v => { const s = String(v ?? ''); return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const lines = [head.join(',')];
    for (const i of items) {
      const d = det.get(i) || {}, b = D.B.get(c.body[i]) || {}, dec = getDec(tp, c.id[i]);
      lines.push([c.date[i], LV[c.lvl[i]], b.canton || '', bodyName(c.body[i]), d.number || c.number[i] || '', c.title[i], c.lang[i], typeOf(i), c.state[i],
        c.submitter[i], c.party[i], d.url || '', tp.kind === 'be' ? beFull(tp, c.be[i]) : tname, p3(tp.p(i)), L.lanes[tp.check(i) ? 'please_check' : 'readings_agree'],
        dec ? (L.decided[dec.d] || dec.d) + (dec.code ? ` ${dec.code}` : '') : L.suggested, dec ? dec.by : '', dec ? dec.at : '', c.id[i], (d.build || D.meta.build || '').slice(-8)].map(q).join(','));
    }
    // method line: affairs found, scored share per parliament, machine suggestions
    const per = this.S.brush ? `${isoOfDay(D.w0 + this.S.brush[0] * 7)} – ${isoOfDay(D.w0 + this.S.brush[1] * 7 + 6)}` : `${isoOfDay(D.dmin)} – ${isoOfDay(D.dmax)}`;
    const bodies = [...new Set(items.map(i => c.body[i]))];
    const cov = bodies.map(k => { const s = this.stats.get(k); return `${bodyName(k)} ${pct(s && s.cov)}`; }).join('; ');
    lines.push('');
    lines.push(q(`# ${L.method(items.length, tp.names[UI.lang] || tp.names.de, per, cov || '–', (D.meta.build_short || D.meta.build || '').slice(-8))}`));
    const slug = (tp.names.de || 'thema').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    download(`querschnitt-${slug}-${new Date().toISOString().slice(0, 10)}.csv`, lines.join('\n'));
    toast(`${num(items.length)} → CSV`);
  }
}

export const beAbbr = (tp, code) => { const o = tp.opt.get(code); return o ? (o.abbr[UI.lang] || o.abbr.de) : (code || '–'); };
export const beFull = (tp, code, l = UI.lang) => { const o = tp.opt.get(code); return o ? `${o.abbr[l] || o.abbr.de} ${o.name[l] || o.name.de}` : (code || ''); };

const fmtWhen = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString(UI.lang === 'fr' ? 'fr-CH' : 'de-CH', { dateStyle: 'short', timeStyle: 'short' }); };

// compact parliament label for ranked lists: the Federal Assembly by name, cantons as "BE Bern", communes by place
const shortName = k => { const b = D.B.get(k); if (!b) return k; if (b.level === 'federal') return bodyName(k);
  if (b.key === 'LIE') return 'Landtag FL'; const pl = UI.lang === 'fr' ? b.place_fr || b.place_de : b.place_de; return b.level === 'cantonal' ? `${b.key} ${pl}` : pl; };
