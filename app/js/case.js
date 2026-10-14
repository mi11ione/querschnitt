// The selected affair: title and text in its own language with the quoted passage highlighted, the topic decision,
// chapter and ranked subtopics, lane, provenance, the parliament's page, similar affairs, and the decision bar.
import { D, detail, getDec, API, TOPIC_BY_ID, norm } from './data.js';
import { h, s, esc, t, UI, num, p3, pct, fmtDate, MONTHS } from './util.js';
import { bar, bindTips, grow } from './viz.js';

const EN = /^(parliament|grand council|council|municipal council)$/i;
export const bodyName = (k, long = true) => {
  const b = D.B.get(k); if (!b) return k;
  let nm = UI.lang === 'fr' ? b.name_fr : b.name_de;
  if (!nm || EN.test(nm)) nm = b.name_de || nm;
  const pl = UI.lang === 'fr' ? b.place_fr || b.place_de : b.place_de;
  if (b.level === 'federal') return nm;
  if (b.key === 'LIE') return `${nm} FL`;
  if (!long) return b.level === 'cantonal' ? b.key : pl;
  const a = (nm || '').toLowerCase(), z = (pl || '').toLowerCase();
  return !pl || a.includes(z) ? nm : z.includes(a) ? pl : `${nm} ${pl}`;
};
export const typeOf = i => (UI.lang === 'fr' && D.c.type_h_fr[i]) || D.c.type_h[i] || D.c.type[i] || '';
const lname = l => ({ de: 'de', fr: 'fr', it: 'it', rm: 'rm' }[l] || l || '');

export function highlight(text, ev, field, want) {
  if (!text) return null;
  const el = h('p', { class: 'txt', lang: want });
  if (ev && ev.field === field) {
    let a = ev.start ?? ev.char_start, b = ev.end ?? ev.char_end;
    if (!(a >= 0 && b > a && text.slice(a, b) === ev.quote) && ev.quote) { a = text.indexOf(ev.quote); b = a + ev.quote.length; }
    if (a >= 0 && b > a) { el.append(text.slice(0, a), h('mark', { text: text.slice(a, b) }), text.slice(b)); return el; }
  }
  el.textContent = text; return el;
}

const chapterName = idx => { const c = D.scheme.chapters[idx]; return c ? (UI.lang === 'fr' ? c.fr || c.de : c.de) : String(idx); };
const subName = code => {
  const S = D.scheme.subtopics || {};
  if (typeof code === 'number' || /^\d+$/.test(code)) { const x = S[String(code)]; return x ? x.de : String(code); }
  for (const x of Object.values(S)) if (x.code === code) return x.de;
  return code;
};

// ---------------------------------------------------------------- similar affairs (title words, other parliaments)
let IDX = null;
// procedural words carry no subject: never count them as shared content
const STOP = new Set(('zwischen gegen sowie ueber kanton kantons kantonal gemeinde stadt schweiz schweizer bericht berichts rapport rapporto motion postulat interpellation '
  + 'anfrage fragen frage antrag antrage wahl wahlen election elezione modification modifica projet progetto approbation comptes gestion revision aenderung '
  + 'anderung gesetz gesetzes verordnung reglement millionen franken francs gewahrung kredit kredits credit credito dekret decret arrete beschluss beschlusses '
  + 'jahresbericht rechnung budget voranschlag initiative iniziativa parlamentarische parlementaire parlamentare conseil consiglio grosser grossen rates rat '
  + 'regierungsrat staatsrat municipal municipale commune comune communale cantonal cantonale federal federale bundes bundesrat liechtenstein landtag '
  + 'betreffend concernant concernente relative relatif riguardante sulla della delle dans pour avec contre entre loi legge').split(' ').map(w => w.slice(0, 7)));
const words = s => [...new Set((norm(s).match(/[a-z]{5,}/g) || []).map(w => w.slice(0, 7)).filter(w => !STOP.has(w)))];
function index() {
  if (IDX) return IDX;
  const inv = new Map(), c = D.c;
  for (let i = 0; i < D.n; i++) for (const w of words(c.title[i])) { let a = inv.get(w); if (!a) inv.set(w, a = []); a.push(i); }
  IDX = inv; return inv;
}
// kept only above a threshold: same first subtopic and ≥ 2 shared content words, or an idf-weighted overlap ≥ SIM_CUT
export const SIM_CUT = 15;
export function similar(i, tp, all = false) {
  const inv = index(), c = D.c, sc = new Map(), sh = new Map();
  for (const w of words(c.title[i])) {
    const a = inv.get(w); if (!a || a.length > 400) continue;
    const idf = Math.log(D.n / a.length);
    for (const j of a) if (c.body[j] !== c.body[i]) { sc.set(j, (sc.get(j) || 0) + idf); sh.set(j, (sh.get(j) || 0) + 1); }
  }
  const sub = c.subs[i] && c.subs[i][0];
  const keep = [...sc].filter(([j, v]) => all || (sub != null && c.subs[j] && c.subs[j][0] === sub && sh.get(j) >= 2) || (v >= SIM_CUT && sh.get(j) >= 3));
  const out = keep.sort((a, b) => b[1] - a[1]).slice(0, 5);
  return all ? out.map(([j, v]) => [j, Math.round(v * 10) / 10, sh.get(j), sub != null && c.subs[j] && c.subs[j][0] === sub]) : out.map(x => x[0]);
}

// ---------------------------------------------------------------- render
export async function renderCase(root, i, tp, { onOpen, decideBar, group }) {
  const c = D.c, L = t(), id = c.id[i];
  const scroll = h('div', { class: 'scroll' });
  root.replaceChildren(scroll);
  const back = h('button', { class: 'tb back', type: 'button', onclick: () => root.dispatchEvent(new CustomEvent('close')) }, '← ' + L.list);
  const lang = c.lang[i];
  const h2 = h('h2', { lang }, c.title[i]);
  scroll.append(back, h2);
  const sub = c.submitter[i] ? `${c.submitter[i]}${c.party[i] ? ` (${c.party[i]})` : ''}` : '';
  scroll.append(h('p', { class: 'ref' }, h('b', {}, fmtDate(c.date[i])), ' · ', bodyName(c.body[i]), typeOf(i) ? ` · ${typeOf(i)}` : ''));
  const refFull = h('p', { class: 'ref' }, c.state[i] ? `${c.state[i]}` : '', sub ? `${c.state[i] ? ' · ' : ''}${sub}` : '', ` · ${lname(lang)}`);
  const altP = h('p', { class: 'alt', hidden: true }); scroll.append(altP);
  const holder = h('div'); scroll.append(holder);
  let groupSec = null;
  if (group && group.length > 1) {
    const tb = h('table', {}, h('tbody', {}, group.map(j => h('tr', {}, h('td', { class: 'n', style: 'text-align:left' }, `#${c.id[j]}`),
      h('td', {}, c.submitter[j] ? `${c.submitter[j]}${c.party[j] ? ` (${c.party[j]})` : ''}` : '–')))));
    groupSec = h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.same(group.length), h('span', { class: 'sp' }, L.sameNote)), h('div', { class: 'tw' }, tb));
  }
  if (decideBar) root.append(decideBar);
  const d = await detail(id);
  if (root.dataset.id !== String(id)) return; // a newer selection won
  const evOf = x => x && x.evidence && (x.evidence.quote || x.evidence.start != null) ? x.evidence : null;
  const ev = d ? (tp && (tp.kind === 'adhoc' || tp.kind === 'live') ? evOf(d.dig) || evOf(d.aps)
    : tp && tp.kind === 'be' ? evOf(d.be) || evOf(d.aps) : evOf(d.aps) || evOf(d.dig)) || evOf(d) : null;
  if (d && d.number) refFull.append(` · ${d.number}`);
  // text
  const tsec = h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.evidence, h('span', { class: 'sp' }, ev ? `${ev.field || ''} ${ev.start ?? ev.char_start ?? ''}–${ev.end ?? ev.char_end ?? ''}` : L.noEvidence)));
  // the affair in the interface language where it has that version; the original stays visible beside it
  const useAlt = d && d.title_alt && d.alt_lang === UI.lang && d.alt_lang !== lang;
  if (useAlt) {
    h2.textContent = d.title_alt; h2.lang = d.alt_lang;
    altP.hidden = false; altP.replaceChildren(h('span', { class: 'mono dim' }, `${lang} · `), h('span', { lang }, c.title[i]));
  }
  if (ev && ev.field === 'title') {
    const hp = highlight(c.title[i], ev, 'title', lang);
    if (useAlt) altP.replaceChildren(h('span', { class: 'mono dim' }, `${lang} · `), ...hp.childNodes); else h2.replaceChildren(...hp.childNodes);
  }
  const evLong = ev && ev.field === 'title_long';
  const tl = useAlt && d.title_long_alt && !evLong ? d.title_long_alt : d && d.title_long;
  const tlShown = useAlt && !evLong ? d.title_alt : c.title[i];
  if (tl && (tl !== tlShown || evLong)) {
    tsec.append(h('div', { class: 'sl dim' }, h('span', { class: 'mono', style: 'font-weight:400;font-size:12px;color:var(--ink2)' }, `${L.titleLong}${useAlt && !evLong ? ' · ' + d.alt_lang : ''}`)));
    tsec.append(highlight(tl, ev, 'title_long', useAlt && !evLong ? d.alt_lang : lang));
  }
  const text = d && (d.text || d.text_excerpt);
  if (text) {
    tsec.append(h('div', { class: 'sl' }, h('span', { class: 'mono', style: 'font-weight:400;font-size:12px;color:var(--ink2)' }, `${L.text}${d.text_src ? ' · ' + d.text_src : ''}`)));
    const long = text.length > 640 && !(ev && ev.field === 'text');
    const p = highlight(long ? text.slice(0, 600).replace(/\s+\S*$/, '') + ' …' : text, ev, 'text', lang); p.classList.add('sm'); tsec.append(p);
    if (long) {
      const more = h('button', { class: 'tb more', type: 'button' }, `[+] ${L.fullText}`);
      more.addEventListener('click', () => { p.textContent = text; more.remove(); });
      tsec.append(more);
    }
  }
  // topic
  const facts = h('dl', { class: 'facts' });
  const add = (k, ...v) => facts.append(h('dt', {}, k), h('dd', {}, ...v));
  const dig = d && d.dig;
  if (!Number.isNaN(c.dp[i]) || dig) {
    const tn = (TOPIC_BY_ID.get('adhoc/digitalisierung') || {}).names || { de: 'Digitalisierung', fr: 'numérique' };
    add(tn[UI.lang] || tn.de, yesNoGraphic(c.dp[i], dig, c.dl[i] === 1, !!c.df[i], c.kw[i]));
  }
  if (tp && tp.kind === 'live') {
    const x = tp.dec.get(id);
    if (x) add(tp.names[UI.lang] || tp.names.de, h('span', { class: 'mono' }, `${x.flag ? L.yes : L.no} · p ${p3(x.p)}`));
  }
  const be = (d && d.be) || (c.be[i] != null ? { code: c.be[i] } : null);
  const beT = TOPIC_BY_ID.get('be-directorates');
  if (be && beT) {
    const code = String(be.code || '').replace(/^be:/, ''), o = beT.opt.get(code);
    add(L.dir, h('span', {}, o ? h('span', { class: 'mono' }, `${o.abbr[UI.lang] || o.abbr.de} `) : '', o ? (o.name[UI.lang] || o.name.de) : code,
      be.p != null ? h('span', { class: 'mono dim' }, ` p ${p3(be.p)}`) : ''),
      be.gold ? h('span', { class: 'sub2' }, `${L.beField}: ${String(be.gold).trim()}`) : '');
  }
  const aps = d && d.aps;
  const bil = aps && aps.bilingual;
  if (bil && bil.top && !bil.reads) {
    const pc = bil.lane === 'please_check';
    add(L.bilingual, h('span', { class: 'mono', style: 'font-size:12px' }, `DE ${chapterName(bil.top.de)} · FR ${chapterName(bil.top.fr)} → `,
      h('span', { class: pc ? 'sig' : '' }, L.lanes[bil.lane] || bil.lane)));
  } else if (c.bi[i] === 1) {
    add(L.bilingual, h('span', { class: 'mono sig', style: 'font-size:12px' }, L.lanes.please_check));
  }
  let chart = null;
  if (c.ch[i] >= 0 || aps) chart = chapterGraphic(aps, c.ch[i], c.chp[i], c.lane[i] === 1);
  else add(L.chapter, h('span', { class: 'dim' }, L.notScored));
  // order: the decision graphic first (the topic in view leads), then the quoted passage, subtopics, metadata
  const tsec2 = h('div', { class: 'sec first' });
  if (chart && tp && (tp.kind === 'chapter' || tp.kind === 'sub')) tsec2.append(chart.el, facts); else { tsec2.append(facts); if (chart) tsec2.append(chart.el); }
  holder.append(tsec2, tsec);
  if (chart && chart.subs) holder.append(h('div', { class: 'sec' }, chart.subs));
  if (groupSec) holder.append(groupSec);
  // provenance
  const pv = h('dl', { class: 'facts' });
  pv.append(h('dt', {}, L.meta), h('dd', {}, refFull));
  const addp = (k, ...v) => pv.append(h('dt', {}, k), h('dd', {}, ...v));
  if (d && d.url) addp(L.page, h('a', { href: d.url, target: '_blank', rel: 'noopener' }, d.url.replace(/^https?:\/\//, '').slice(0, 64) + ' ↗'));
  addp('OPD', h('span', { class: 'mono' }, `#${id} · ${c.body[i]}`));
  if (d) addp(L.build, h('span', { class: 'mono' }, `${(d.build || '').slice(-8)} · ${d.model || ''}`));
  const pids = d && ((d.aps && d.aps.pids) || d.prompt_ids || []);
  if (pids && pids.length) addp('prompt', h('span', { class: 'mono' }, pids.join(' ')));
  holder.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.prov), pv));
  // similar affairs: one strip per level on the main timeline's weeks, then the titles
  const sim = similar(i, tp);
  if (sim.length) {
    const ul = h('ul', { class: 'sim' });
    for (const j of sim) ul.append(h('li', { onclick: () => onOpen && onOpen(j), lang: c.lang[j], tabindex: '0', onkeydown: e => { if (e.key === 'Enter') onOpen && onOpen(j); } }, c.title[j],
      h('span', { class: 'm' }, `${fmtDate(c.date[j])} · ${bodyName(c.body[j])}${tp && tp.hit(j) ? ' · ' + (tp.names[UI.lang] || tp.names.de) : ''}`)));
    holder.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.similar), simStrip(i, sim, onOpen), ul));
  }
  bindTips(holder); grow(holder);
}

// ---------------------------------------------------------------- graphics
// yes/no topic: the decision's p on a 0–1 track with the cut-off, the two readings as thin bars beneath
function yesNoGraphic(p, dig, check, flag, kw) {
  const L = t(), cut = 0.5, rn = [L.read1, L.read2];
  const rows = [{ label: `${flag ? L.yes : L.no}`, v: p, tone: flag ? 'ink' : 'grey', value: p3(p), tip: `p ${p3(p)} · ${L.cutoff} ${cut}`, strong: true }];
  if (dig && dig.p_a != null) rows.push({ label: rn[0], v: dig.p_a, tone: dig.p_a >= cut ? 'ink' : 'grey', value: '', thin: true, tip: `${rn[0]} p ${p3(dig.p_a)}` });
  if (dig && dig.p_b != null) rows.push({ label: rn[1], v: dig.p_b, tone: dig.p_b >= cut ? 'ink' : 'grey', value: '', thin: true, tip: `${rn[1]} p ${p3(dig.p_b)}` });
  const el = h('div', { class: 'dg' });
  for (const r of rows) el.append(h('div', { class: `dgr ${r.thin ? 'thin' : ''}`, 'data-tip': r.tip, tabindex: '0' },
    h('span', { class: `rk ${r.strong ? 'on' : 'dim'}` }, r.label),
    h('span', { class: 'rbar cut' }, bar(r.v, r.tone, '', r.thin), h('span', { class: 'cutl', style: `left:${cut * 100}%` })),
    h('span', { class: 'rv' }, r.value)));
  el.append(h('p', { class: 'dgn' }, check ? h('span', { class: 'sig' }, `${L.lanes.please_check}`) : L.lanes.readings_agree, ` · ${kw ? L.kwYes : L.kwNo}`));
  return el;
}

// APS chapter: up to 5 chapters; per chapter the shipped read-back value (black for the shipped chapter) and the two
// readings as thin bars (code orders, or DE / FR in bilingual parliaments); the reading's own top chapter in black, so
// agreement is visible; a red tick where the readings point to different chapters. Then the ranked subtopics.
function chapterGraphic(aps, ch, chp, laneCheck) {
  const L = t();
  const rank = (aps && aps.rank) || (ch >= 0 ? [ch] : []);
  const praw = (aps && (aps.p_raw || aps.p)) || [chp];
  // one p per row, the same number as in the list and the Pult: the calibrated p of the shipped chapter; raw values only on hover
  const pShip = aps && aps.p && aps.p[0] != null ? aps.p[0] : (Number.isNaN(chp) ? null : chp);
  const bil = aps && aps.bilingual && aps.bilingual.reads ? aps.bilingual : null;
  const reads = bil ? bil.reads : aps && aps.reads;
  const rnames = bil ? (bil.langs || ['de', 'fr']).map(x => x.toUpperCase()) : [L.read1, L.read2].slice(0, (aps && aps.read_names && aps.read_names.length) || 2);
  const nR = reads ? Math.max(...Object.values(reads).map(v => v.length)) : 0;
  const rp = (k, r) => reads && reads[k] && reads[k][r] != null ? reads[k][r] : null;
  const top = [];
  for (let r = 0; r < nR; r++) { let best = null, bv = -1; for (const k of Object.keys(reads)) { const v = rp(k, r); if (v != null && v > bv) { bv = v; best = +k; } } top.push(best); }
  const disagree = nR > 1 && top[0] != null && top[1] != null && top[0] !== top[1];
  const lane = bil ? bil.lane : (aps && aps.lane) || (laneCheck ? 'please_check' : 'readings_agree');
  const keys = [...rank];
  if (reads) for (const k of Object.keys(reads).sort((a, b) => Math.max(...reads[b]) - Math.max(...reads[a]))) if (!keys.includes(+k)) keys.push(+k);
  const shown = keys.slice(0, 5);
  const el = h('div', { class: 'dg' }, h('div', { class: 'dgh' }, h('span', {}, L.chapter), h('span', { class: 'dim' }, reads ? `p · ${rnames.join(' / ')}` : 'p')));
  for (const k of shown) {
    const ri = rank.indexOf(k), v = ri >= 0 ? praw[ri] : null, shipped = ri === 0;
    const subs = [];
    for (let r = 0; r < nR; r++) { const x = rp(k, r); subs.push({ v: x || 0, tone: top[r] === k ? 'ink' : 'grey', tip: `${rnames[r]} p ${x == null ? '–' : p3(x)}` }); }
    const tick = disagree && (top[0] === k || top[1] === k);
    const tip = `${chapterName(k)}${shipped && pShip != null ? ` · p ${p3(pShip)}` : ''}${v != null ? ` · ${L.chapterP} ${p3(v)}` : ''}${subs.map(x => ` · ${x.tip}`).join('')}`;
    el.append(h('div', { class: 'dgr', 'data-tip': tip, tabindex: '0' },
      h('span', { class: `rk ${shipped ? 'on' : ''}` }, chapterName(k)),
      h('span', { class: 'rbar' }, v != null ? bar(v, shipped ? 'ink' : 'grey') : h('span', { class: 'vb none' }), ...subs.map(x => bar(x.v, x.tone, '', true))),
      h('span', { class: 'rv' }, shipped && pShip != null ? p3(pShip) : '', tick ? h('span', { class: 'rtick' }) : '')));
  }
  el.append(h('p', { class: 'dgn' }, h('span', { class: lane === 'please_check' ? 'sig' : '' }, L.lanes[lane] || lane),
    disagree ? ` · ${rnames[0]} → ${chapterName(top[0])}, ${rnames[1]} → ${chapterName(top[1])}` : nR > 1 ? ` · ${rnames.join(' = ')}` : ''));
  const subs = aps && aps.subs ? aps.subs : [];
  let se = null;
  if (subs.length) {
    se = h('div', { class: 'dg' }, h('div', { class: 'dgh' }, h('span', {}, L.subtopics)));
    subs.slice(0, 3).forEach(([code, p], k) => se.append(h('div', { class: 'dgr', 'data-tip': `${subName(code)} · p ${p3(p)}`, tabindex: '0' },
      h('span', { class: `rk ${k === 0 ? 'on' : ''}` }, `${k + 1}. ${subName(code)}`), h('span', { class: 'rbar' }, bar(p, k === 0 ? 'ink' : 'grey')), h('span', { class: 'rv' }, p3(p)))));
  }
  return { el, subs: se };
}

// similar affairs on the main timeline's weeks, one strip per level; the open affair as a black mark with a hairline
function simStrip(i, sim, onOpen) {
  const L = t(), c = D.c, W = 400, RH = 18, LEFT = 92, rows = [L.federal, L.cantonal, L.communal];
  const svg = s('svg', { viewBox: `0 0 ${W} ${rows.length * RH + 16}`, class: 'strip', role: 'img', 'aria-label': L.similar });
  const X = w => LEFT + (w + .5) / D.nWeeks * (W - LEFT);
  rows.forEach((r, l) => { svg.append(s('line', { x1: LEFT, x2: W, y1: l * RH + RH - 3.5, y2: l * RH + RH - 3.5, class: 'base' })); const tx = s('text', { x: 0, y: l * RH + RH - 4 }); tx.textContent = r; svg.append(tx); });
  const xi = X(c.week[i]);
  svg.append(s('line', { x1: xi, x2: xi, y1: 0, y2: rows.length * RH, class: 'now' }));
  const mark = (j, cur) => {
    const l = Math.min(2, c.lvl[j]), x = X(c.week[j]), y = l * RH + RH - 9;
    const r = s('rect', { x: x - 3, y, width: 6, height: 6, class: cur ? 'cur' : 'sm', tabindex: cur ? null : '0', 'data-tip': `${fmtDate(c.date[j])} · ${bodyName(c.body[j])} · ${c.title[j]}` });
    if (!cur) { r.addEventListener('click', () => onOpen && onOpen(j)); r.addEventListener('keydown', e => { if (e.key === 'Enter') onOpen && onOpen(j); }); }
    svg.append(r);
  };
  sim.forEach(j => mark(j, false)); mark(i, true);
  const y = rows.length * RH + 14, M = MONTHS[UI.lang];
  let last = -99;
  for (let d = D.w0; d <= D.dmax; d++) { const dt = new Date(d * 864e5); if (dt.getUTCDate() !== 1) continue; const x = LEFT + (d - D.w0) / 7 / D.nWeeks * (W - LEFT); if (x - last < 40) continue; last = x;
    const tx = s('text', { x, y }); tx.textContent = dt.getUTCMonth() === 0 ? String(dt.getUTCFullYear()) : M[dt.getUTCMonth()]; svg.append(tx); }
  return svg;
}

export function decisionState(tp, id) {
  const L = t(), r = getDec(tp, id);
  if (!r) return '';
  const d = new Date(r.at || ''), when = isNaN(d) ? (r.at || '') : d.toLocaleString(UI.lang === 'fr' ? 'fr-CH' : 'de-CH', { dateStyle: 'short', timeStyle: 'short' });
  const corr = r.corr === true && r.code ? ` → ${esc(r.code)}` : (typeof r.corr === 'string' ? ` → ${esc(r.corr.replace('aps:', ''))}` : '');
  return `<b>${L.decided[r.d] || r.d}${corr ? ` (${L.corrected}${corr})` : ''}</b>${r.n > 1 ? ` · ${L.sameDec(r.n)}` : ''} · ${esc(r.by || '')} · ${when} · ${r.err ? `<span class="sig">${L.apiErr}</span>` : r.api ? L.apiSaved : L.localSaved}`;
}
