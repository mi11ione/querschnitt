// Neueste Woche (view id `woche`): what Swiss parliaments did in one week, for a reader who has 30 seconds. One line that
// says what the tool does, the week stepper, one sentence (affairs, parliaments), the week by level and language as one
// mono line, then the 6 APS chapters with the most affairs, ranked, each with up to 3 example affairs from different
// parliaments and languages, each with the quoted sentence that supports the topic and a red tick when a person should
// check. Digitalisierung is not an APS chapter: it follows in its own section («Querschnittsthemen»), never in the
// ranking. Default week = the newest week with complete data (data.js newestFullWeek: ≥ 50 % of the median of the 8
// weeks before, so an export-lagged week is not the opener); ‹ › step weeks, later lagged weeks say so quietly.
// Examples come from the pass lane; a please-check row only fills a slot that pass-lane rows cannot.
// Detail files are per 1000 ids: only the buckets that hold this week's candidates are fetched.
import { D, TOPIC_BY_ID, FL_KEY, detail, norm, lastCompleteWeek, newestFullWeek, priorMedian, weekCounts } from './data.js';
import { h, t, UI, num, isoWeek, isoOfDay, dayNum, fmtDate } from './util.js';
import { bodyName } from './case.js';
import { bindTips } from './viz.js';

const NTOP = 6, NEX = 3, QMAX = 160;
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

// Procedural boilerplate (docs/APP.md «Procedural quotes»): phrases that say what kind of instrument an affair is, not what
// it is about. A quote counts as procedural when it contains one of them and, once they are removed, fewer than 4 content
// words remain, or none shares a stem with the topic (its names, its subtopics, a saved topic's question) and the rest
// is short (< 6 content words) or carries form labels (FORM). Content words: ≥ 4 letters, not in STOP.
// Such a quote is never shown: the row falls back to its title as evidence («Beleg: der Titel»).
const GOV = '(?:bundesrat|regierungsrat|gemeinderat|stadtrat|staatsrat|landrat|kleine rat|regierung|exekutive)\\p{L}*';
const PROC = [
  // DE
  new RegExp(`\\b(?:der|die) ${GOV} (?:wird|werden) (?:beauftragt|gebeten|ersucht|eingeladen|aufgefordert)(?:,? zu prüfen(?: und bericht zu erstatten)?)?(?:,? (?:die )?folgenden? fragen? zu beantworten)?\\s*[,:]?`, 'giu'),
  new RegExp(`\\b(?:ich )?bitte (?:ich )?(?:den|die) ${GOV} (?:um die beantwortung der folgenden fragen?|(?:um )?folgende fragen? zu beantworten)\\s*:?`, 'giu'),
  /\b(?:haben|hat|steht)\b[^.]{0,40}?\b(?:ratsmitglieder|mitglieder|kommissionen|fraktionen)\b[^.]*?\brecht\b[^.]*?\b(?:einzureichen|zu stellen|einzubringen|zu verlangen)\b\.?/giu,
  /\bgestützt auf (?:art(?:\.|ikel)?|§)[^,:]{0,60}[,:]?/giu,
  /\bder (?:grosse rat|kantonsrat|landrat|einwohnerrat|gemeinderat|stadtrat) (?:wolle|möge) beschliessen\s*:?/giu,
  /\bantwort des (?:bundesrates|regierungsrates|gemeinderates|stadtrates|staatsrates)\b/giu,
  // FR
  /\ble conseil (?:fédéral|d['’]état|communal|municipal|administratif|exécutif) (?:est|sont) (?:chargé|prié|invité)e?s? (?:de|d['’])(?: répondre aux questions suivantes)?\s*:?/giu,
  /\b(?:en vertu|conformément|en application) (?:de l['’]|à l['’]|des |aux |de )?art(?:\.|icles?)[^,:]{0,60}[,:]?/giu,
  /\ble grand conseil (?:décrète|arrête)\s*:?/giu,
  /\bréponse du conseil (?:d['’]état|fédéral|communal|municipal)\b/giu,
  // IT
  /\bil (?:consiglio (?:federale|di stato|comunale)|municipio) (?:è|viene) (?:incaricato|invitato|pregato) (?:di|a)(?: rispondere alle seguenti domande)?\s*:?/giu,
  /\b(?:ai sensi|giusta|conformemente|in virtù) (?:del|dell['’]|dello|degli|all['’])\s*(?:art(?:\.|icolo)|artt\.)[^,:]{0,60}[,:]?/giu,
  /\b(?:chiediamo|chiedo|chiedono) (?:al (?:lodevole )?(?:municipio|consiglio di stato) )?(?:di rispondere alle seguenti domande|quanto segue)\s*:?/giu,
];
// standard form lines and letterheads (labels of a submission form, the address of a Ticino municipality)
const FORM = [
  /\b(?:eingereicht von|erstunterzeichnende?r?|mitunterzeichnende?r?|mitunterzeichnet von|einreichedatum|datum der einreichung|geschäftstyp|urheber\/?in|zuständig|signatur|dringlichkeit(?: verlangt| beantragt)?)\s*:/giu,
  /\b(?:signataires?|cosignataires?|date de dépôt|réception au sgc|département\(s\)|numéro|heure|à compléter par le secrétariat[^.:]*)\s*:/giu,
  /\blodevole (?:municipio|consiglio di stato)\b/giu,
];
const STOP = new Set(('und oder sowie der die das des den dem ein eine einer eines einem für fur über uber mit von vom zum zur bei aus nach auch sich sind wird werden dass nicht '
  + 'andere anderen weitere sonstige allgemein allgemeine allgemeiner fragen frage politik politische politischen politisches bereich bereiche massnahmen schweiz schweizer '
  + 'kanton kantone kantonale bund bundes thema themen betrifft folgende parlamentarische geschäft geschaft '
  + 'les des dans pour avec sans leur sont autres autre questions question générale generale général general politique politiques problèmes problemes mesures suisse '
  + 'canton cantons fédéral federal fédérale federale thème theme objet parlementaire suivant concerne '
  + 'della delle degli dello nella nelle alla alle sulla altri altre questioni generali politica politiche problemi misure svizzera cantone cantoni federale tema oggetto '
  + 'parlamentare seguente riguarda '
  // the vocabulary of a request, not of a subject
  + 'vorzulegen vorlegen anzupassen erforderlichen erforderliche notwendigen notwendige gesetzlichen gesetzliche grundlagen grundlage ergreifen treffen '
  + 'schaffen prüfen bericht erstatten sicherzustellen entsprechend entsprechende aufzunehmen vorzuschlagen ausarbeiten auszuarbeiten unterbreiten '
  + 'parlament bundesversammlung folgenden nécessaires prendre proposer modification rapport présenter afin suivantes necessarie adottare proporre '
  + 'rapporto affinché seguenti').split(' ').map(w => norm(w)));
const words = x => (norm(x).match(/\p{L}{4,}/gu) || []).filter(w => !STOP.has(w));
const STEMS = new Map();
// the topic's stems: its names (and aliases), a chapter's APS subtopics (German names), a saved topic's question in brackets
function stems(tp) {
  if (STEMS.has(tp.id)) return STEMS.get(tp.id);
  const src = [...Object.values(tp.names || {}), ...(tp.aliases || [])];
  if (tp.kind === 'chapter') for (const x of Object.values((D.scheme && D.scheme.subtopics) || {})) if (x.ch === tp.idx) src.push(x.de);
  const st = ((D.scheme && D.scheme.topics) || []).find(x => x.id === tp.id);
  if (st && st.question) for (const q of Object.values(st.question)) for (const m of String(q).matchAll(/\(([^)]*)\)/g)) src.push(m[1]);
  const out = [...new Set(src.flatMap(words).map(w => w.slice(0, 7)))];
  STEMS.set(tp.id, out);
  return out;
}
// [procedural, topic signal] of a cleaned quote
function signalOf(q, tp) {
  let rest = q, hit = false, form = false;
  for (const re of PROC) { re.lastIndex = 0; if (re.test(rest)) { hit = true; re.lastIndex = 0; rest = rest.replace(re, ' '); } }
  for (const re of FORM) { re.lastIndex = 0; if (re.test(rest)) { hit = form = true; re.lastIndex = 0; rest = rest.replace(re, ' '); } }
  const n = norm(rest), sig = stems(tp).some(x => n.includes(x)), k = words(rest).length;
  return [hit && (k < 4 || (!sig && (k < 6 || form))), sig];
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
  // the full data replaced the slice: the same week under the new week numbering
  rebase(oldW0) { if (this.w != null) this.w = Math.floor((oldW0 + this.w * 7 - D.w0) / 7); }
  hashQ() { return this.w != null && this.w !== this.home() ? `d=${isoOfDay(D.w0 + this.w * 7)}` : ''; }
  step(d) {
    const w = (this.w ?? this.home()) + d;
    if (w < D.mainW || w > this.lastFull()) return;
    this.w = w; this.render();
    const q = this.hashQ(); history.replaceState(null, '', `#woche${q ? `?${q}` : ''}`);
  }
  // the ranked list: APS chapters only; the cross-cutting yes/no topics (Digitalisierung, saved ad-hoc topics) apart
  topics() { return [...TOPIC_BY_ID.values()].filter(x => x.kind === 'chapter' && x.code !== 'aps:none'); }
  cross() {
    const dig = TOPIC_BY_ID.get('adhoc/digitalisierung');
    return [dig, ...[...TOPIC_BY_ID.values()].filter(x => x.saved)].filter(Boolean);
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
    this.c = c; this.w0 = D.w0;   // this render's data: the first-screen slice may be replaced by the full data meanwhile
    if (this.w == null) this.w = this.home();
    const w = this.w, d0 = D.w0 + w * 7, d1 = d0 + 6;
    // the week's affairs
    const rows = [], lv = [0, 0, 0, 0], lg = new Map(), bodies = new Set();
    for (let i = 0; i < D.n; i++) {
      if (c.week[i] !== w || c.day[i] > D.dmax || c.day[i] < D.dmin) continue;
      rows.push(i); lv[c.lvl[i]]++; bodies.add(c.body[i]);
      const l = c.lang[i] || '?'; lg.set(l, (lg.get(l) || 0) + 1);
    }
    // chapters by count this week; the cross-cutting topics in their own fixed order (not ranked against the chapters)
    const count = tp => {
      const hits = rows.filter(i => tp.hit(i)), l4 = [0, 0, 0, 0];
      for (const i of hits) l4[c.lvl[i]]++;
      return { tp, hits, l4 };
    };
    const tps = this.topics().map(count).filter(x => x.hits.length).sort((a, b) => b.hits.length - a.hits.length);
    const top = tps.slice(0, NTOP), more = tps.slice(NTOP);
    // Digitalisierung gets a full row; saved ad-hoc topics one quiet line (name and count) under it
    const crsAll = this.cross().map(count).filter(x => x.hits.length);
    const crs = crsAll.filter(x => !x.tp.saved);
    const name = tp => tp.names[UI.lang] || tp.names.de;
    const [, k] = isoWeek(d0);

    // head: week stepper, the sentence, the week by level and language
    const first = w <= D.mainW, last = w >= this.lastFull(), home = this.home(), lag = w > home;
    const nav = h('p', { class: 'wo-nav' },
      h('button', { class: 'tb', type: 'button', disabled: first || null, 'aria-label': L.wkPrev, 'data-tip': first ? null : `${L.wkPrev} [‹]`, onclick: () => this.step(-1) }, '‹'),
      h('span', {}, h('b', {}, `${L.week} ${k}`), ` · ${span(d0, d1)}${w === home ? ` · ${L.wkNewest}` : ''}`),
      h('button', { class: 'tb', type: 'button', disabled: last || null, 'aria-label': L.wkNext, 'data-tip': last ? null : `${L.wkNext} [›]`, onclick: () => this.step(1) }, '›'));
    // the Landtag FL is not a Swiss parliament: named apart («35 Parlamenten und dem Landtag FL»)
    const fl = bodies.has(FL_KEY), nCH = bodies.size - (fl ? 1 : 0);
    const head = h('h2', { class: 'wo-h' }, rows.length ? L.wkLine(k, num(rows.length), num(nCH), nCH, fl, []) : L.wkNone(k));
    // what the page is, in one line, before anything else
    const intro = h('p', { class: 'wo-lede' }, L.wkIntro[0], h('span', { class: 'k' }, h('span', { class: 'rtick', role: 'img', 'aria-label': L.wkCheck }), L.wkIntro[1]));
    // a week after the newest complete one: the export has not caught up yet (quiet, not red)
    const md = lag ? priorMedian(w) : null;
    const lagNote = lag ? h('p', { class: 'wo-lag', 'data-tip': L.wkLagTip(num(weekCounts()[w]), md == null ? '–' : num(Math.round(md))) }, L.wkLag) : '';
    // the week by level and language: one mono line
    const lab = [L.federal, L.cantonal, L.communal, 'FL'];
    const lvs = [0, 1, 2, 3].filter(l => lv[l]).map(l => `${num(lv[l])} ${lab[l]}`);
    const langs = ['de', 'fr', 'it', 'rm'].filter(l => lg.get(l)).map(l => `${num(lg.get(l))} ${l.toUpperCase()}`);
    const sub = h('p', { class: 'wo-lg wo-sub' }, [...lvs, ...langs].join(' · '));
    // topic rows; examples fill in once their detail buckets are in. One bar scale for chapters and cross-cutting topics
    const row = (x, list) => {
      const ex = h('div', { class: 'wo-ex' }, h('p', { class: 'wo-wait' }, '…'));
      list.append(h('li', { class: 'wo-row' },
        h('div', { class: 'wo-tp' },
          h('button', { class: 'wo-name', type: 'button', 'data-tip': L.wkMap, onclick: () => this.openTopic(x.tp.id, this.w0 + w * 7) }, name(x.tp)),
          h('p', { class: 'wo-n' }, h('b', {}, num(x.hits.length)), ` ${x.hits.length === 1 ? L.affair1 : L.affairs}`, x.tp.saved ? ` · ${L.savedMark}` : '')),
        ex));
      return ex;
    };
    const list = h('ol', { class: 'wo-list' }), slots = top.map(x => row(x, list));
    const tail = more.length ? h('p', { class: 'wo-more' }, `${L.wkMore}: `, ...more.slice(0, 12).flatMap((x, j) => [j ? ' · ' : '',
      h('button', { class: 'tb', type: 'button', onclick: () => this.openTopic(x.tp.id, this.w0 + w * 7) }, name(x.tp)), ` ${num(x.hits.length)}`])) : '';
    // cross-cutting topics: own heading, own list (ul, unranked), after the chapters
    const xlist = h('ul', { class: 'wo-list' }), xslots = crs.map(x => row(x, xlist));
    const crossSec = crs.length ? h('section', { class: 'wo-x' }, h('h3', { class: 'wo-xh' }, L.wkCross), xlist) : '';
    root.replaceChildren(h('div', { class: 'wo' }, intro, nav, head, lagNote, sub, rows.length ? list : '', tail, crossSec));
    const all = top.concat(crs);
    if (!all.length) { window.__wocheReady = Promise.resolve(); return; }
    window.__wocheReady = this.fill(all, slots.concat(xslots), tok, w);
  }

  // load the buckets that hold the candidates (largest first; a thin bucket only when a topic still lacks examples)
  async fill(top, slots, tok, w) {
    const c = this.c, L = t();
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
    const c = this.c, used = new Set(), out = [];
    for (const x of top) {
      const cands = [];
      for (const i of x.hits) {
        if (!this.loaded.has(Math.floor(c.id[i] / 1000))) continue;
        const d = await detail(c.id[i]); const ev = this.quote(x.tp, d);
        if (!ev) continue;
        const [q, qual] = cleanQuote(ev.quote), nt = norm(bare(c.title[i]));
        // procedural boilerplate with no topic signal: the title is the evidence instead
        const [proc, sig] = signalOf(q, x.tp);
        const onTitle = proc || ev.field === 'title' || norm(q.replace(/^… /, '')).startsWith(nt.slice(0, 40)), weak = onTitle || qual < 0.6;
        const p = x.tp.p(i);
        // a clean title beats a weak fragment (letterhead, form fields, mid-sentence start); a quote that shares a word
        // with the topic or its subtopics comes first
        const score = (onTitle ? 0 : weak ? -1 : 1) + qual + (!onTitle && sig ? 0.75 : 0) + (Number.isNaN(p) ? 0 : p * 0.5);
        cands.push({ i, d, q, onTitle, proc, weak, score, lang: langOf(c, i, d), chk: !!x.tp.check(i) });
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

  example({ i, d, q, onTitle, proc, lang }, tp, w) {
    const c = this.c, L = t();
    // the title in the interface language where the parliament publishes that version, else the original with its language
    const alt = d && d.title_alt && d.alt_lang === UI.lang && d.alt_lang !== lang;
    const tl = alt ? d.title_alt : bare(c.title[i]), tlLang = alt ? d.alt_lang : lang;
    const check = tp.check(i);
    const meta = h('span', { class: 'm' },
      tlLang && tlLang !== UI.lang ? h('span', { class: 'lg' }, tlLang) : '',
      `${bodyName(c.body[i]).trim()} · ${fmtDate(c.date[i])}`,
      check ? h('span', { class: 'rtick', role: 'img', 'aria-label': L.wkCheck, 'data-tip': L.wkCheck }) : '');
    // the topic rests on the title alone: the title is marked, no second copy of it
    return h('button', { class: 'wo-a', type: 'button', 'data-id': c.id[i], onclick: () => this.openAffair(c.id[i], tp.id, this.w0 + w * 7) },
      h('span', { class: 't', lang: tlLang }, onTitle && !alt ? h('mark', {}, tl) : tl),
      meta,
      (onTitle && !alt) || proc ? h('span', { class: 'q dim' }, L.wkOnTitle) : h('span', { class: 'q' }, `«${q}»`));
  }
}

const bare = s => String(s || '').replace(/^\[(.*)\]$/, '$1');
// OPD marks some bilingual parliaments' French titles as German: the version whose text equals the title wins
const langOf = (c, i, d) => (d && d.title_alt && d.alt_lang && norm(d.title_alt) === norm(bare(c.title[i])) ? d.alt_lang : c.lang[i]);

// «5.–11. Oktober 2026» / «5–11 octobre 2026»
function span(a, b) {
  const loc = UI.lang === 'fr' ? 'fr-CH' : 'de-CH', da = new Date(a * 864e5), db = new Date(b * 864e5);
  const f = (d, o) => d.toLocaleDateString(loc, { timeZone: 'UTC', ...o });
  const sameM = da.getUTCMonth() === db.getUTCMonth(), y = db.getUTCFullYear();
  if (UI.lang === 'fr') return sameM ? `${da.getUTCDate()}–${f(db, { day: 'numeric', month: 'long' })} ${y}` : `${f(da, { day: 'numeric', month: 'long' })} – ${f(db, { day: 'numeric', month: 'long' })} ${y}`;
  return sameM ? `${da.getUTCDate()}.–${f(db, { day: 'numeric', month: 'long' })} ${y}` : `${f(da, { day: 'numeric', month: 'long' })} – ${f(db, { day: 'numeric', month: 'long' })} ${y}`;
}
