// Diese Woche: what Swiss parliaments did in one week, for a reader who has 30 seconds. One plain sentence (affairs,
// parliaments, the three biggest topics), the week by level and language, then the 6 topics with the most affairs
// (APS chapters, Digitalisierung, saved ad-hoc topics): count by level as hairline bars and up to 3 example affairs from
// different parliaments and languages, each with the quoted sentence that supports the topic and a red tick when a
// person should check. Default week = the newest week with complete data (data.js newestFullWeek: ≥ 50 % of the median of
// the 8 weeks before, so an export-lagged week is not the opener); ‹ › step weeks, later lagged weeks say so quietly.
// Examples come from the pass lane; a please-check row only fills a slot that pass-lane rows cannot.
// Detail files are per 1000 ids: only the buckets that hold this week's candidates are fetched.
import { D, TOPIC_BY_ID, detail, norm, lastCompleteWeek, newestFullWeek, priorMedian, weekCounts } from './data.js';
import { h, t, UI, num, isoWeek, isoOfDay, dayNum, fmtDate } from './util.js';
import { bodyName } from './case.js';
import { bindTips } from './viz.js';

const NTOP = 6, NEX = 3, QMAX = 160;
const LV = ['federal', 'cantonal', 'communal', 'other'];
const ABBR = /\b(art|artt|cpv|al|cfr|cf|lett|let|cap|ecc|ca|bzw|vgl|etc|nr|no|n|abs|ziff|inkl|resp|seg|ss|sig|sigg|dott|avv|prof|dr|st|ev|lit|chap|ch|p|pp|s|vol|mio|mia|fr|chf|sen|on|dipl|ing|lic|phil|jur|med)\.$/i;

// the quote as one clean line: whitespace collapsed, PDF line-break hyphens joined, the most prose-like sentence of it,
// cut at a word boundary. Returns [text, quality]; letterheads, addresses and form fields («Data: … Numero: …») score low.
function cleanQuote(q) {
  let s = String(q || '').replace(/\s+/g, ' ').trim();
  s = s.replace(/(\p{Ll})- (\p{Ll}+)/gu, (m, a, b) => /^(und|oder|bzw|et|ou|e|o|sowie)$/.test(b) ? m : a + b);
  s = s.replace(/^\[(.*)\]$/, '$1');
  const prose = p => {
    const ws = p.split(' '), n = ws.length, low = ws.filter(x => /^\p{Ll}/u.test(x)).length / n;
    return low * 2 - Math.min(3, (p.match(/:/g) || []).length) * 0.5 - ((p.match(/\d/g) || []).length / p.length) * 6
      - (/^[^\p{Lu}«"„(]/u.test(p) ? 1.2 : 0) - (/^[^(]*\)/.test(p) ? 1 : 0) - (p.length < 40 ? 1 : 0) - (/@|www\.|https?:|\.(docx?|pdf)\b/i.test(p) ? 2 : 0)
      - Math.min(2, (p.match(/\b\p{Lu}{5,}\b/gu) || []).length * 0.5); // «RICEVUTA IL», «EINGANG»
  };
  // sentences; a run of form fields keeps only what follows its last label
  const raw = s.split(/(?<=[.!?])\s+(?=[«"„(\p{Lu}\d])/u), parts0 = [];
  for (const p of raw) { // «art. 111 LGC», «Abs. 2», «RS 171.10)»: no sentence end
    const prev = parts0[parts0.length - 1];
    if (prev && (ABBR.test(prev) || /\d\.$/.test(prev) || /^\d/.test(p) || /^[^(]*\)/.test(p))) parts0[parts0.length - 1] = `${prev} ${p}`; else parts0.push(p);
  }
  const parts = parts0.map(p => {
    if ((p.match(/:/g) || []).length < 2) return p;
    const tail = p.slice(p.lastIndexOf(':') + 1).replace(/^[\s\d./-]+/, '').trim();
    return tail.length >= 40 ? tail : p;
  }).map(p => p.replace(/^\d+\s*\/\s*\d{2,4}\s+(?=\p{Lu})/u, '')); // «71 /2026 Sottoscrizione …»
  let best = parts[0], bs = -Infinity;
  for (const p of parts) { const v = prose(p); if (v > bs + 0.05) { bs = v; best = p; } }
  s = /^[^\p{Lu}«"„(]/u.test(best) ? `… ${best}` : best; // a quote that starts mid-sentence says so
  if (s.length > QMAX) {
    let cut = s.slice(0, QMAX);
    const sp = cut.lastIndexOf(' ');
    if (sp > QMAX * 0.6) cut = cut.slice(0, sp);
    s = cut.replace(/[\s,;:.(«"–-]+$/u, '') + ' …';
  }
  return [s, bs];
}

export class Woche {
  constructor(root, { openTopic, openAffair }) {
    this.root = root; this.openTopic = openTopic; this.openAffair = openAffair;
    this.w = null; this.tok = 0; this.loaded = new Set();
    bindTips(root);
    document.addEventListener('keydown', e => {
      if (root.hidden || e.metaKey || e.ctrlKey || e.altKey) return;
      const tg = e.target; if (tg && /^(INPUT|TEXTAREA|SELECT)$/.test(tg.tagName)) return;
      if (e.key === '[' || e.key === 'ArrowLeft') { this.step(-1); e.preventDefault(); }
      else if (e.key === ']' || e.key === 'ArrowRight') { this.step(1); e.preventDefault(); }
    });
  }
  // newest week whose Sunday is on or before the export date; the default is the newest of those with complete data
  lastFull() { return lastCompleteWeek(); }
  home() { return newestFullWeek(); }
  setDate(iso) { // #woche?d=2026-10-05
    if (!iso || !/^\d{4}-\d\d-\d\d$/.test(iso)) return;
    const w = Math.floor((dayNum(iso) - D.w0) / 7);
    if (w >= D.mainW && w <= this.lastFull()) this.w = w;
  }
  hashQ() { return this.w != null && this.w !== this.home() ? `d=${isoOfDay(D.w0 + this.w * 7)}` : ''; }
  step(d) {
    const w = (this.w ?? this.home()) + d;
    if (w < D.mainW || w > this.lastFull()) return;
    this.w = w; this.render();
    const q = this.hashQ(); history.replaceState(null, '', `#woche${q ? `?${q}` : ''}`);
  }
  topics() {
    const dig = TOPIC_BY_ID.get('adhoc/digitalisierung');
    const rest = [...TOPIC_BY_ID.values()].filter(x => x.saved || (x.kind === 'chapter' && x.code !== 'aps:none'));
    return [dig, ...rest].filter(Boolean);
  }
  // the topic's own evidence: APS chapter → detail.aps, Digitalisierung → detail.dig, saved topic → detail.adhoc[slug]
  quote(tp, d) {
    if (!d) return null;
    const ev = tp.kind === 'chapter' ? d.aps && d.aps.evidence
      : tp.id === 'adhoc/digitalisierung' ? d.dig && d.dig.evidence
        : d.adhoc && d.adhoc[tp.id.replace(/^adhoc\//, '')] && d.adhoc[tp.id.replace(/^adhoc\//, '')].evidence;
    return ev && typeof ev.quote === 'string' && ev.quote.trim().length >= 12 ? ev : null;
  }

  render() {
    const L = t(), c = D.c, root = this.root, tok = ++this.tok;
    if (this.w == null) this.w = this.home();
    const w = this.w, d0 = D.w0 + w * 7, d1 = d0 + 6;
    // the week's affairs
    const rows = [], lv = [0, 0, 0, 0], lg = new Map(), bodies = new Set();
    for (let i = 0; i < D.n; i++) {
      if (c.week[i] !== w || c.day[i] > D.dmax || c.day[i] < D.dmin) continue;
      rows.push(i); lv[c.lvl[i]]++; bodies.add(c.body[i]);
      const l = c.lang[i] || '?'; lg.set(l, (lg.get(l) || 0) + 1);
    }
    // topics by count this week
    const tps = this.topics().map(tp => {
      const hits = rows.filter(i => tp.hit(i)), l4 = [0, 0, 0, 0];
      for (const i of hits) l4[c.lvl[i]]++;
      return { tp, hits, l4 };
    }).filter(x => x.hits.length).sort((a, b) => b.hits.length - a.hits.length);
    const top = tps.slice(0, NTOP), more = tps.slice(NTOP);
    const name = tp => tp.names[UI.lang] || tp.names.de;
    const [, k] = isoWeek(d0);

    // head: week stepper, the sentence, the week by level and language
    const first = w <= D.mainW, last = w >= this.lastFull(), home = this.home(), lag = w > home;
    const nav = h('p', { class: 'wo-nav' },
      h('button', { class: 'tb', type: 'button', disabled: first || null, 'aria-label': L.wkPrev, 'data-tip': first ? null : `${L.wkPrev} [‹]`, onclick: () => this.step(-1) }, '‹'),
      h('span', {}, h('b', {}, `${L.week} ${k}`), ` · ${span(d0, d1)}${w === home ? ` · ${L.wkNewest}` : ''}`),
      h('button', { class: 'tb', type: 'button', disabled: last || null, 'aria-label': L.wkNext, 'data-tip': last ? null : `${L.wkNext} [›]`, onclick: () => this.step(1) }, '›'));
    const head = h('h2', { class: 'wo-h' }, rows.length ? L.wkLine(k, num(rows.length), num(bodies.size), bodies.size, top.slice(0, 3).map(x => name(x.tp))) : L.wkNone(k));
    // a week after the newest complete one: the export has not caught up yet (quiet, not red)
    const md = lag ? priorMedian(w) : null;
    const lagNote = lag ? h('p', { class: 'wo-lag', 'data-tip': L.wkLagTip(num(weekCounts()[w]), md == null ? '–' : num(Math.round(md))) }, L.wkLag) : '';
    const mxL = Math.max(1, ...lv);
    const langs = ['de', 'fr', 'it', 'rm'].filter(l => lg.get(l)).map(l => `${num(lg.get(l))} ${L.wkIn[l]}`);
    const sub = h('div', { class: 'wo-sub' },
      levelBars(lv, mxL, L, 'wo-lv wide'),
      h('p', { class: 'wo-lg' }, langs.join(' · ')),
      h('p', { class: 'wo-key' }, h('span', { class: 'rtick' }), ` ${L.wkCheck}`));
    // topic rows; examples fill in once their detail buckets are in
    const mx = Math.max(1, ...top.flatMap(x => x.l4));
    const list = h('ol', { class: 'wo-list' });
    const slots = top.map(x => {
      const ex = h('div', { class: 'wo-ex' }, h('p', { class: 'wo-wait' }, '…'));
      list.append(h('li', { class: 'wo-row' },
        h('div', { class: 'wo-tp' },
          h('button', { class: 'wo-name', type: 'button', 'data-tip': L.wkMap, onclick: () => this.openTopic(x.tp, w) }, name(x.tp)),
          h('p', { class: 'wo-n' }, h('b', {}, num(x.hits.length)), ` ${x.hits.length === 1 ? L.affair1 : L.affairs}`, x.tp.saved ? ` · ${L.savedMark}` : ''),
          levelBars(x.l4, mx, L, 'wo-lv')),
        ex));
      return ex;
    });
    const tail = more.length ? h('p', { class: 'wo-more' }, `${L.wkMore}: `, ...more.slice(0, 12).flatMap((x, j) => [j ? ' · ' : '',
      h('button', { class: 'tb', type: 'button', onclick: () => this.openTopic(x.tp, w) }, name(x.tp)), ` ${num(x.hits.length)}`])) : '';
    const note = h('p', { class: 'wo-note' }, L.wkNote);
    root.replaceChildren(h('div', { class: 'wo' }, nav, head, lagNote, sub, rows.length ? list : '', tail, note));
    if (!top.length) { window.__wocheReady = Promise.resolve(); return; }
    window.__wocheReady = this.fill(top, slots, tok, w);
  }

  // load the buckets that hold the candidates (largest first; a thin bucket only when a topic still lacks examples)
  async fill(top, slots, tok, w) {
    const c = D.c, L = t();
    const bk = id => Math.floor(id / 1000);
    const cand = new Map(); // bucket -> ids
    for (const x of top) for (const i of x.hits) { const b = bk(c.id[i]); if (!cand.has(b)) cand.set(b, new Set()); cand.get(b).add(c.id[i]); }
    const total = [...cand.values()].reduce((a, s) => a + s.size, 0);
    const order = [...cand.entries()].sort((a, b) => b[1].size - a[1].size);
    const want = order.filter(([b, s], j) => j === 0 || s.size >= Math.max(3, total * 0.1)).map(([b]) => b);
    const load = async bs => { await Promise.all(bs.map(b => detail([...cand.get(b)][0]))); bs.forEach(b => this.loaded.add(b)); };
    await load(want.filter(b => !this.loaded.has(b)));
    let picks = await this.pick(top);
    for (let round = 0; round < 3; round++) {
      const short = top.filter((x, j) => picks[j].length < Math.min(2, x.hits.length));
      if (!short.length) break;
      const need = new Map();
      for (const x of short) for (const i of x.hits) { const b = bk(c.id[i]); if (!this.loaded.has(b)) need.set(b, (need.get(b) || 0) + 1); }
      const nx = [...need.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2).map(([b]) => b);
      if (!nx.length) break;
      await load(nx);
      picks = await this.pick(top);
    }
    if (tok !== this.tok) return;
    top.forEach((x, j) => {
      const ex = slots[j];
      if (!picks[j].length) { ex.replaceChildren(h('p', { class: 'wo-wait' }, L.wkNoQuote)); return; }
      ex.replaceChildren(...picks[j].map(p => this.example(p, x.tp, w)));
    });
  }

  // up to 3 examples per topic: quoted rows only, each from another parliament, preferably another language and level
  async pick(top) {
    const c = D.c, used = new Set(), out = [];
    for (const x of top) {
      const cands = [];
      for (const i of x.hits) {
        if (!this.loaded.has(Math.floor(c.id[i] / 1000))) continue;
        const d = await detail(c.id[i]); const ev = this.quote(x.tp, d);
        if (!ev) continue;
        const [q, qual] = cleanQuote(ev.quote), nt = norm(bare(c.title[i]));
        const onTitle = ev.field === 'title' || norm(q.replace(/^… /, '')).startsWith(nt.slice(0, 40)), weak = onTitle || qual < 0.6;
        const p = x.tp.p(i);
        // a clean title beats a weak fragment (letterhead, form fields, mid-sentence start)
        const score = (onTitle ? 0 : weak ? -1 : 1) + qual + (Number.isNaN(p) ? 0 : p * 0.5);
        cands.push({ i, d, q, onTitle, weak, score, lang: langOf(i, d), chk: !!x.tp.check(i) });
      }
      cands.sort((a, b) => b.score - a.score || c.day[b.i] - c.day[a.i]);
      // diversity first among good quoted sentences, then titles and fragments as evidence: new language and level, new language, new parliament;
      // all of that in the pass lane first: a please-check row (the model was unsure) only fills a slot no pass-lane row can
      const sel = [], bodies = new Set(), langs = new Set(), lvls = new Set(), titles = new Set();
      const ok = (o, tier) => !used.has(o.i) && !bodies.has(c.body[o.i]) && !titles.has(norm(c.title[o.i]))
        && (tier % 3 === 2 || !langs.has(o.lang)) && (tier % 3 !== 0 || !lvls.has(c.lvl[o.i])) && (tier >= 3 || !o.weak);
      for (const pool of [cands.filter(o => !o.chk), cands.filter(o => o.chk)]) {
        for (let tier = 0; tier < 6 && sel.length < NEX; tier++) {
          for (const o of pool) {
            if (sel.length >= NEX) break;
            if (!ok(o, tier)) continue;
            sel.push(o); used.add(o.i); bodies.add(c.body[o.i]); langs.add(o.lang); lvls.add(c.lvl[o.i]); titles.add(norm(c.title[o.i]));
          }
        }
      }
      out.push(sel);
    }
    return out;
  }

  example({ i, d, q, onTitle, lang }, tp, w) {
    const c = D.c, L = t();
    // the title in the interface language where the parliament publishes that version, else the original with its language
    const alt = d && d.title_alt && d.alt_lang === UI.lang && d.alt_lang !== lang;
    const tl = alt ? d.title_alt : bare(c.title[i]), tlLang = alt ? d.alt_lang : lang;
    const check = tp.check(i);
    const meta = h('span', { class: 'm' },
      tlLang && tlLang !== UI.lang ? h('span', { class: 'lg' }, tlLang) : '',
      `${bodyName(c.body[i]).trim()} · ${fmtDate(c.date[i])}`,
      check ? h('span', { class: 'rtick', role: 'img', 'aria-label': L.wkCheck, 'data-tip': L.wkCheck }) : '');
    // the topic rests on the title alone: the title is marked, no second copy of it
    return h('button', { class: 'wo-a', type: 'button', onclick: () => this.openAffair(i, tp, w) },
      h('span', { class: 't', lang: tlLang }, onTitle && !alt ? h('mark', {}, tl) : tl),
      meta,
      onTitle && !alt ? h('span', { class: 'q dim' }, L.wkOnTitle) : h('span', { class: 'q' }, `«${q}»`));
  }
}

const bare = s => String(s || '').replace(/^\[(.*)\]$/, '$1');
// OPD marks some bilingual parliaments' French titles as German: the version whose text equals the title wins
const langOf = (i, d) => (d && d.title_alt && d.alt_lang && norm(d.title_alt) === norm(bare(D.c.title[i])) ? d.alt_lang : D.c.lang[i]);

function levelBars(lv, mx, L, cls) {
  const lab = [L.federal, L.cantonal, L.communal, L.other];
  return h('div', { class: cls }, ...[0, 1, 2, 3].filter(l => l < 3 || lv[l]).map(l => h('div', { class: 'lr', 'data-tip': `${L.lvl1[LV[l]]}: ${num(lv[l])}` },
    h('span', { class: 'lk' }, lab[l]),
    h('span', { class: 'lt' }, h('span', { class: 'lb', style: `width:${(lv[l] / mx) * 100}%` })),
    h('span', { class: 'lv' }, num(lv[l])))));
}

// «5.–11. Oktober 2026» / «5–11 octobre 2026»
function span(a, b) {
  const loc = UI.lang === 'fr' ? 'fr-CH' : 'de-CH', da = new Date(a * 864e5), db = new Date(b * 864e5);
  const f = (d, o) => d.toLocaleDateString(loc, { timeZone: 'UTC', ...o });
  const sameM = da.getUTCMonth() === db.getUTCMonth(), y = db.getUTCFullYear();
  if (UI.lang === 'fr') return sameM ? `${da.getUTCDate()}–${f(db, { day: 'numeric', month: 'long' })} ${y}` : `${f(da, { day: 'numeric', month: 'long' })} – ${f(db, { day: 'numeric', month: 'long' })} ${y}`;
  return sameM ? `${da.getUTCDate()}.–${f(db, { day: 'numeric', month: 'long' })} ${y}` : `${f(da, { day: 'numeric', month: 'long' })} – ${f(db, { day: 'numeric', month: 'long' })} ${y}`;
}
