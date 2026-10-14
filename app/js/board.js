// Karte (and the Neues Thema board): topic → map + weekly timeline → ruled list (or Pult) → the selected affair.
import { D, API, apiPost, getDec, setDec, detail, TOPICS, norm } from './data.js';
import { h, t, UI, num, pct, p3, fmtDate, isoWeek, isoOfDay, dayNum, debounce, toast, download } from './util.js';
import { SwissMap, rampBreaks, rampClass } from './map.js';
import { Timeline } from './timeline.js';
import { VList } from './vlist.js';
import { Picker } from './picker.js';
import { renderCase, bodyName, typeOf, decisionState } from './case.js';

const WHO = 'qs.who', BUDGET = 'qs.budget';
export const HATCH_COV = 0.25, HATCH_TITLE = 0.5;
const ls = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };

export class Board {
  constructor(root, { topic, picker = true, pult = true, order = 'date', head = null, onChange } = {}) {
    this.root = root; this.tp = topic; this.order = order; this.onChange = onChange;
    this.S = { brush: null, body: null, f: { type: '', status: '', party: '', q: '' }, mode: 'list', tab: 'todo', sel: null };
    const L = t();
    this.work = h('div', { class: 'work' });
    // map column
    this.mapcol = h('div', { class: 'pane mapcol' });
    if (head) this.mapcol.append(head);
    if (picker) {
      const pr = h('div', { class: 'picker' });
      this.picker = new Picker(pr, { onPick: tp => this.setTopic(tp) });
      this.mapcol.append(h('div', { class: 'topicrow' }, pr));
    }
    this.tsub = h('p', { class: 'tsub' }); this.mapcol.append(this.tsub);
    this.mapEl = h('div', { class: 'map', id: `map-${Math.random().toString(36).slice(2, 7)}` }); this.mapcol.append(this.mapEl);
    this.legend = h('p', { class: 'legend' }); this.mapcol.append(this.legend);
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
    this.pultOn = pult;
    // case
    this.case = h('section', { class: 'case', 'aria-label': 'Geschäft', tabindex: '-1' });
    this.case.addEventListener('close', () => this.select(null));
    this.work.append(this.mapcol, this.reg, this.case);
    root.append(this.work);
    this.map = new SwissMap(this.mapEl, { onClick: k => { this.S.body = k && k !== this.S.body ? k : null; this.refresh(); } });
    this.tl = new Timeline(this.tlEl, { onBrush: b => { this.S.brush = b; this.refresh(); } });
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
    for (let i = 0; i < D.n; i++) {
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
    const mask = this.passMask();
    const br = S.brush, inP = i => !br || (c.week[i] >= br[0] && c.week[i] <= br[1]);
    const stats = new Map();
    const counts = [new Int32Array(D.nWeeks), new Int32Array(D.nWeeks), new Int32Array(D.nWeeks)];
    const tabsN = { todo: 0, ok: 0, changed: 0, done: 0 };
    const items = [];
    const gen = (D.meta.generated_at || '').slice(0, 10);
    const lastW = gen ? Math.floor((dayNum(gen) - D.w0) / 7) : c.week.reduce((a, b) => Math.max(a, b), 0);
    let newW = 0, scoredSel = 0, hitsSel = 0;
    const lv = [{ n: 0, hits: 0 }, { n: 0, hits: 0 }, { n: 0, hits: 0 }, { n: 0, hits: 0 }];
    for (let i = 0; i < n; i++) {
      if (!mask[i] || !tp) continue;
      const sc = tp.scored(i); if (!sc) continue;
      if (isBe && S.f.dir && c.be[i] !== S.f.dir) continue;
      const hit = tp.hit(i), chk = tp.check(i), k = c.body[i];
      if (hit && (!S.body || k === S.body) && c.lvl[i] < 3) counts[c.lvl[i]][c.week[i]]++;
      if (!inP(i)) continue;
      const dec = getDec(tp, c.id[i]);
      let st = stats.get(k); if (!st) stats.set(k, st = { n: 0, hits: 0, check: 0 });
      st.n++; if (hit) st.hits++; if (chk && !dec) st.check++;
      lv[c.lvl[i]].n++; if (hit) lv[c.lvl[i]].hits++;
      if (S.body && k !== S.body) continue;
      scoredSel++; if (hit) hitsSel++;
      if (hit && c.week[i] === lastW) newW++;
      const todo = chk && !dec; // one definition everywhere: undecided rows in the please_check lane
      if (todo) tabsN.todo++;
      if (dec && dec.d === 'confirmed') tabsN.ok++;
      const changed = dec && dec.d === 'confirmed' && dec.state != null && dec.state !== c.state[i];
      if (changed) tabsN.changed++;
      if (dec) tabsN.done++;
      if (S.mode === 'pult' && this.pultOn) {
        if ((S.tab === 'todo' && todo) || (S.tab === 'ok' && dec && dec.d === 'confirmed') || (S.tab === 'changed' && changed) || (S.tab === 'done' && dec)) items.push(i);
      } else if (hit) items.push(i);
    }
    if (this.order === 'arrival' && tp && tp.dec) {
      const rank = new Map(); let r = 0; for (const id of tp.dec.keys()) rank.set(id, r++);
      items.sort((a, b) => rank.get(c.id[b]) - rank.get(c.id[a]));
    } else if (S.mode === 'pult' && this.pultOn && S.tab === 'todo') {
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
    this.stats = all; this.breaks = breaks; this.lv = lv; this.tabsN = tabsN; this.newW = newW; this.lastW = lastW;
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
    const selRow = S.sel != null ? D.rowOf.get(S.sel) : null;
    this.tl.set(counts, S.brush, selRow != null ? { w: c.week[selRow], l: Math.min(2, c.lvl[selRow]) } : null);
    // list
    const pos = selRow != null && posOf.has(selRow) ? posOf.get(selRow) : -1;
    this.list.set(rows, pos);
    this.renderHead(scoredSel, hitsSel);
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
    if (this.pultOn) {
      const mk = (m, lab) => h('button', { class: 'tb', type: 'button', 'aria-pressed': String(S.mode === m), onclick: () => this.setMode(m) }, lab);
      this.lhead.replaceChildren(mk('list', `${L.list}`), mk('pult', `${L.pult}`), h('span', { class: 'sp' }, '[l]'));
      this.tabs.hidden = S.mode !== 'pult'; this.pline.hidden = S.mode !== 'pult';
      if (S.mode === 'pult') {
        const tab = (k) => h('button', { class: `tab ${k === 'todo' && N.todo ? 'need' : ''}`, role: 'tab', type: 'button', 'aria-selected': String(S.tab === k), onclick: () => { S.tab = k; S.sel = null; this.refresh(); this.renderCase(); } },
          h('span', { class: 't' }, L.tabs[k]), h('span', { class: 'c' }, num(N[k])));
        this.tabs.replaceChildren(tab('todo'), tab('ok'), tab('changed'), tab('done'));
        const [y, wk] = isoWeek(D.w0 + this.lastW * 7);
        const budget = +(ls(BUDGET) || 25);
        const bi = h('input', { type: 'text', inputmode: 'numeric', value: budget, 'aria-label': L.budget });
        bi.addEventListener('change', () => { const v = parseInt(bi.value, 10); if (v > 0) ls(BUDGET, String(v)); this.refresh(); });
        this.pline.replaceChildren(h('b', {}, `${L.week} ${wk} ${y}`), ` · ${L.newW} ${num(this.newW)} · `,
          h('span', { class: N.todo ? 'sig' : '' }, `${L.pending} ${num(N.todo)}`), ` · ${L.budget} `, bi, L.perWeek);
      }
    } else { this.lhead.hidden = true; this.tabs.hidden = true; this.pline.hidden = true; }
    this.count.replaceChildren(h('span', {}, `${num(this.items.length)} ${L.affairs}${this.rows.length !== this.items.length ? ` · ${num(this.rows.length)} ${L.lines}` : ''}`),
      h('span', { class: 'sp' }, h('button', { class: 'tb', type: 'button', onclick: () => this.exportCsv() }, `[e] ${L.export}`)));
  }

  relang() { this.buildFilters(); if (this.picker) this.picker.set(this.tp); this.refresh(); this.renderCase(); }

  setMode(m) { this.S.mode = m; this.S.sel = null; this.refresh(); this.renderCase(); }

  row(g) {
    const i = g[0], c = D.c, tp = this.tp, L = t();
    const dec = tp ? getDec(tp, c.id[i]) : null, chk = tp && tp.check(i);
    const sub = c.submitter[i] ? `${c.submitter[i]}${c.party[i] ? ` (${c.party[i]})` : ''}` : '';
    const meta = [fmtDate(c.date[i]), bodyName(c.body[i], false), typeOf(i), sub, c.state[i]].filter(Boolean).join(' · ');
    const p = tp ? tp.p(i) : NaN;
    const mark = dec ? (dec.d === 'confirmed' ? '✓' : '–') : chk ? '!' : '';
    return h('div', { class: dec ? 'dec' : '' },
      h('div', { class: 'tc' }, h('div', { class: 't', lang: c.lang[i] }, c.title[i]), h('div', { class: 'm' }, g.length > 1 ? h('b', { class: 'grpn' }, `×${g.length} `) : '', meta)),
      h('div', { class: 'p' }, tp && tp.kind === 'be' ? beAbbr(tp, c.be[i]) : p3(p)),
      h('div', { class: `x ${dec ? 'd' : ''}`, title: chk ? L.lanes.please_check : '' }, mark ? `[${mark}]` : ''));
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
    renderCase(root, i, this.tp, { onOpen: j => this.select(D.c.id[j]), decideBar: this.decideBar(i), group: this.groupOf(i) });
  }
  decideBar(i) {
    const L = t(), id = D.c.id[i], tp = this.tp;
    const b = (k, key, lab) => h('button', { class: 'box', type: 'button', onclick: () => this.decide(k) }, h('span', { class: 'k' }, `[${key}] `), lab);
    const who = h('input', { type: 'text', value: ls(WHO) || '', 'aria-label': L.who, placeholder: L.whoAsk });
    who.addEventListener('change', () => ls(WHO, who.value.trim()));
    who.addEventListener('keydown', e => { if (e.key === 'Enter') { ls(WHO, who.value.trim()); who.blur(); } });
    this.who = who;
    const st = h('div', { class: 'st', html: tp ? decisionState(tp, id) : '' });
    const grp = this.groupOf(i);
    if (grp.length > 1 && !getDec(tp, id)) st.textContent = `[1] [2] ${L.sameDec(grp.length)}`;
    const bar = h('div', { class: 'decide' }, h('div', { class: 'btns' }, b('confirmed', '1', L.accept), b('rejected', '2', L.reject), b('skip', '0', L.skip),
),
      h('div', { class: 'who' }, L.who, who), st);
    if (getDec(tp, id)) st.append(' · ', h('button', { class: 'tb', type: 'button', onclick: () => this.decide('undo') }, `[u] ${L.undo}`));
    return bar;
  }
  groupOf(row) { return this.posOf && this.posOf.has(row) ? this.rows[this.posOf.get(row)] : [row]; }
  async decide(kind) {
    const id = this.S.sel, tp = this.tp, L = t(), c = D.c;
    if (id == null || !tp) return;
    if (kind === 'skip') { this.step(1); return; }
    const row = D.rowOf.get(id), group = this.groupOf(row), pos = this.posOf.get(row);
    if (kind === 'undo') { for (const j of group) setDec(tp, c.id[j], null); this.refresh(); this.renderCase(); return; }
    const by = (this.who && this.who.value.trim()) || ls(WHO) || '';
    if (!by) { const w = this.case.querySelector('.who'); if (w) { w.classList.add('ask'); w.querySelector('input').focus(); } toast(L.whoAsk); return; }
    ls(WHO, by);
    const at = new Date().toISOString();
    for (const j of group) { // one key decides every affair of a group of identical affairs
      const aid = c.id[j], rec = { d: kind, by, at, state: c.state[j], n: group.length };
      if (API.live) {
        try {
          const r = await apiPost(`/affairs/${aid}/topics/${encodeURIComponent(tp.codeOf ? tp.codeOf(j) : tp.code)}/${kind === 'confirmed' ? 'confirm' : 'reject'}`, { by, scheme: tp.scheme });
          rec.api = true; rec.row = r && (r.valid_from || r.confirmed_at) ? { valid_from: r.valid_from, confirmed_at: r.confirmed_at } : null;
        } catch (e) { rec.err = String(e.message || e); }
      }
      setDec(tp, aid, rec);
    }
    this.refresh();
    const stillThere = this.posOf.has(row);
    const next = this.rows[stillThere ? pos + 1 : pos];
    this.select(next ? c.id[next[0]] : id);
  }

  summary() {
    const L = t(), tp = this.tp, root = this.case;
    const name = tp ? (tp.names[UI.lang] || tp.names.de) : '';
    const sc = h('div', { class: 'scroll' });
    root.replaceChildren(sc);
    const per = this.S.brush ? `${isoOfDay(D.w0 + this.S.brush[0] * 7)} – ${isoOfDay(D.w0 + this.S.brush[1] * 7 + 6)}` : `${isoOfDay(D.dmin)} – ${isoOfDay(D.dmax)}`;
    sc.append(h('div', { class: 'sl' }, L.summary, h('span', { class: 'sp' }, `${name} · ${per}`)));
    if (tp && tp.kind === 'be') { this.beSummary(sc); return; }
    const lvN = [L.federal, L.cantonal, L.communal, 'FL'];
    const tb = h('table', {}, h('thead', {}, h('tr', {}, h('th', {}, L.perLevel), h('th', { class: 'n' }, L.hits), h('th', { class: 'n' }, L.scored), h('th', { class: 'n' }, L.share))));
    const body = h('tbody');
    this.lv.forEach((x, k) => { if (x.n) body.append(h('tr', {}, h('td', {}, lvN[k]), h('td', { class: 'n' }, num(x.hits)), h('td', { class: 'n' }, num(x.n)), h('td', { class: 'n' }, pct(x.n ? x.hits / x.n : NaN)))); });
    tb.append(body);
    sc.append(h('div', { class: 'tw' }, tb));
    const top = [...this.stats].filter(([, s]) => s.hits).sort((a, b) => b[1].hits - a[1].hits).slice(0, 15);
    if (!top.length) { sc.append(h('p', { class: 'empty' }, L.none)); return; }
    const t2 = h('table', {}, h('thead', {}, h('tr', {}, h('th', {}, L.selParl), h('th', { class: 'n cov' }, L.covered), h('th', { class: 'n' }, L.hits), h('th', { class: 'n' }, L.share), h('th', { class: 'n' }, L.pending))));
    const b2 = h('tbody');
    for (const [k, s] of top) {
      const b = D.B.get(k);
      b2.append(h('tr', { class: 'clk', onclick: () => { this.S.body = k; this.refresh(); } },
        h('td', {}, bodyName(k)), h('td', { class: 'n dim cov' }, b && b.covered_from ? String(b.covered_from) : '–'),
        h('td', { class: 'n' }, num(s.hits)), h('td', { class: 'n' }, pct(s.share)), h('td', { class: `n ${s.check ? 'sig' : 'dim'}` }, s.check ? num(s.check) : '–')));
    }
    t2.append(b2);
    sc.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.topParl), h('div', { class: 'tw' }, t2)));
  }

  beSummary(sc) {
    const L = t(), tp = this.tp, c = D.c, cnt = new Map(), chk = new Map();
    for (const i of this.items) { const k = c.be[i]; cnt.set(k, (cnt.get(k) || 0) + 1); if (tp.check(i) && !getDec(tp, c.id[i])) chk.set(k, (chk.get(k) || 0) + 1); }
    const tb = h('table', {}, h('thead', {}, h('tr', {}, h('th', {}, L.dir), h('th', { class: 'n' }, L.affairs), h('th', { class: 'n' }, L.pending))));
    const body = h('tbody');
    for (const o of tp.options) {
      const n = cnt.get(o.code) || 0;
      body.append(h('tr', { class: 'clk', onclick: () => { this.S.f.dir = this.S.f.dir === o.code ? '' : o.code; this.buildFilters(); this.refresh(); this.renderCase(); } },
        h('td', {}, h('span', { class: 'mono' }, `${o.abbr[UI.lang] || o.abbr.de} `), o.name[UI.lang] || o.name.de),
        h('td', { class: 'n' }, n ? num(n) : '–'), h('td', { class: `n ${chk.get(o.code) ? 'sig' : 'dim'}` }, chk.get(o.code) ? num(chk.get(o.code)) : '–')));
    }
    tb.append(body);
    sc.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.beGroup), h('div', { class: 'tw' }, tb)));
  }

  // ------------------------------------------------------------ export: CSV in the DVS list's columns + method line
  async exportCsv() {
    const L = t(), tp = this.tp, c = D.c, items = this.items;
    if (!tp) return;
    const det = new Map(); await Promise.all([...new Set(items.map(i => Math.floor(c.id[i] / 1000)))].map(async k => {
      const any = items.find(i => Math.floor(c.id[i] / 1000) === k); await detail(c.id[any]);
    }));
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
        c.submitter[i], c.party[i], d.url || '', tp.kind === 'be' ? beFull(tp, c.be[i]) : tname, p3(tp.p(i)), tp.check(i) ? 'please_check' : 'readings_agree',
        dec ? dec.d : 'suggested', dec ? dec.by : '', dec ? dec.at : '', c.id[i], (d.build || D.meta.build || '').slice(-8)].map(q).join(','));
    }
    // method line: affairs found, scored share per parliament, machine suggestions
    const per = this.S.brush ? `${isoOfDay(D.w0 + this.S.brush[0] * 7)} – ${isoOfDay(D.w0 + this.S.brush[1] * 7 + 6)}` : `${isoOfDay(D.dmin)} – ${isoOfDay(D.dmax)}`;
    const bodies = [...new Set(items.map(i => c.body[i]))];
    const cov = bodies.map(k => { const s = this.stats.get(k), b = D.B.get(k); return `${k} ${pct(s && s.cov)}${b && b.covered_from ? (fr ? ' dès ' : ' ab ') + b.covered_from : ''}`; }).join('; ');
    lines.push('');
    lines.push(q(`# ${L.method(items.length, tp.names[UI.lang] || tp.names.de, per, cov || '–', (D.meta.build_short || D.meta.build || '').slice(-8))}`));
    const slug = (tp.names.de || 'thema').toLowerCase().replace(/[^a-z0-9]+/g, '-');
    download(`querschnitt-${slug}-${new Date().toISOString().slice(0, 10)}.csv`, lines.join('\n'));
    toast(`${num(items.length)} → CSV`);
  }
}

export const beAbbr = (tp, code) => { const o = tp.opt.get(code); return o ? (o.abbr[UI.lang] || o.abbr.de) : (code || '–'); };
export const beFull = (tp, code, l = UI.lang) => { const o = tp.opt.get(code); return o ? `${o.abbr[l] || o.abbr.de} ${o.name[l] || o.name.de}` : (code || ''); };
