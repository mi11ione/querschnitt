// The selected affair: title and text in its own language with the quoted passage highlighted, the topic decision,
// chapter and ranked subtopics, lane, provenance, the parliament's page, similar affairs, and the decision bar.
import { D, detail, getDec, API, TOPIC_BY_ID, norm } from './data.js';
import { h, esc, t, UI, num, p3, pct, fmtDate } from './util.js';

export const bodyName = (k, long = true) => {
  const b = D.B.get(k); if (!b) return k;
  const nm = UI.lang === 'fr' ? b.name_fr : b.name_de, pl = UI.lang === 'fr' ? b.place_fr : b.place_de;
  if (b.level === 'federal') return nm;
  if (b.key === 'LIE') return `${nm} FL`;
  return long ? `${nm} ${pl}` : (b.level === 'cantonal' ? `${b.key}` : pl);
};
export const typeOf = i => (UI.lang === 'fr' && D.c.type_h_fr[i]) || D.c.type_h[i] || D.c.type[i] || '';
const lname = l => ({ de: 'de', fr: 'fr', it: 'it', rm: 'rm' }[l] || l || '');

function highlight(text, ev, field, want) {
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
const words = s => [...new Set((norm(s).match(/[a-z]{5,}/g) || []).map(w => w.slice(0, 7)))];
function index() {
  if (IDX) return IDX;
  const inv = new Map(), c = D.c;
  for (let i = 0; i < D.n; i++) for (const w of words(c.title[i])) { let a = inv.get(w); if (!a) inv.set(w, a = []); a.push(i); }
  IDX = inv; return inv;
}
function similar(i, tp) {
  const inv = index(), c = D.c, sc = new Map();
  for (const w of words(c.title[i])) {
    const a = inv.get(w); if (!a || a.length > 400) continue;
    const idf = Math.log(D.n / a.length);
    for (const j of a) if (c.body[j] !== c.body[i]) sc.set(j, (sc.get(j) || 0) + idf);
  }
  const sub = c.subs[i] && c.subs[i][0];
  for (const [j, v] of sc) {
    let b = v;
    if (sub != null && c.subs[j] && c.subs[j][0] === sub) b += 3;
    if (tp && tp.hit(j)) b += 1.5;
    sc.set(j, b);
  }
  return [...sc].filter(([, v]) => v >= 4).sort((a, b) => b[1] - a[1]).slice(0, 5).map(x => x[0]);
}

// ---------------------------------------------------------------- render
export async function renderCase(root, i, tp, { onOpen, decideBar }) {
  const c = D.c, L = t(), id = c.id[i];
  const scroll = h('div', { class: 'scroll' });
  root.replaceChildren(scroll);
  const back = h('button', { class: 'tb back', type: 'button', onclick: () => root.dispatchEvent(new CustomEvent('close')) }, '← ' + L.list);
  const lang = c.lang[i];
  scroll.append(back, h('h2', { lang }, c.title[i]));
  const sub = c.submitter[i] ? `${c.submitter[i]}${c.party[i] ? ` (${c.party[i]})` : ''}` : '';
  scroll.append(h('p', { class: 'ref' },
    h('b', {}, fmtDate(c.date[i])), ' · ', bodyName(c.body[i]), ' · ', typeOf(i) || '–', c.state[i] ? ` · ${c.state[i]}` : '',
    sub ? ` · ${sub}` : '', ` · ${lname(lang)}`));
  const holder = h('div'); scroll.append(holder);
  if (decideBar) root.append(decideBar);
  const d = await detail(id);
  if (root.dataset.id !== String(id)) return; // a newer selection won
  const ev = d ? ((tp && tp.kind !== 'chapter' && tp.kind !== 'sub' ? d.dig && d.dig.evidence : d.aps && d.aps.evidence) || (d.evidence) || null) : null;
  if (d && d.number) scroll.querySelector('.ref').append(` · ${d.number}`);
  // text
  const tsec = h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.evidence, h('span', { class: 'sp' }, ev && ev.quote ? `${ev.field || ''} ${ev.start ?? ''}–${ev.end ?? ''}` : L.noEvidence)));
  if (ev && ev.field === 'title') tsec.append(highlight(c.title[i], ev, 'title', lang));
  if (d && d.title_long && d.title_long !== c.title[i]) {
    tsec.append(h('div', { class: 'sl dim' }, h('span', { class: 'mono', style: 'font-weight:400;font-size:12px;color:var(--ink2)' }, L.titleLong)));
    tsec.append(highlight(d.title_long, ev, 'title_long', lang));
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
  holder.append(tsec);
  // topic
  const facts = h('dl', { class: 'facts' });
  const add = (k, ...v) => facts.append(h('dt', {}, k), h('dd', {}, ...v));
  const dig = d && d.dig;
  if (!Number.isNaN(c.dp[i]) || dig) {
    const tn = (TOPIC_BY_ID.get('adhoc/digitalisierung') || {}).names || { de: 'Digitalisierung', fr: 'numérique' };
    const ln = c.dl[i] === 1 ? 'please_check' : 'readings_agree';
    add(tn[UI.lang] || tn.de,
      h('span', { class: 'mono' }, `${c.df[i] ? L.yes : L.no} · p ${p3(c.dp[i])}`),
      h('span', { class: 'sub2' }, `${L.lane}: `, h('span', { class: ln === 'please_check' ? 'sig' : '' }, L.lanes[ln]),
        dig && dig.p_a != null ? ` · ${L.readings} ${p3(dig.p_a)}${dig.p_b != null ? ' / ' + p3(dig.p_b) : ''}` : '',
        ` · ${c.kw[i] ? L.kwYes : L.kwNo}`));
  }
  if (tp && tp.kind === 'live') {
    const x = tp.dec.get(id);
    if (x) add(tp.names[UI.lang] || tp.names.de, h('span', { class: 'mono' }, `${x.flag ? L.yes : L.no} · p ${p3(x.p)}`));
  }
  const aps = d && d.aps;
  if (c.ch[i] >= 0 || aps) {
    const ranks = aps && aps.rank ? aps.rank : [c.ch[i]];
    const ps = aps && aps.p ? aps.p : [c.chp[i]];
    const ln = (aps && aps.lane) || (c.lane[i] === 1 ? 'please_check' : 'readings_agree');
    add(L.chapter,
      h('span', {}, chapterName(ranks[0]), ' ', h('span', { class: 'mono dim' }, `p ${p3(ps[0])}`)),
      ranks.slice(1).map((r, k) => h('span', { class: 'sub2' }, `${k + 2}. ${chapterName(r)} · p ${p3(ps[k + 1])}`)),
      h('span', { class: 'sub2' }, `${L.lane}: `, h('span', { class: ln === 'please_check' ? 'sig' : '' }, L.lanes[ln] || ln)));
    const subs = aps && aps.subs ? aps.subs : (c.subs[i] || []).map(x => [x, null]);
    if (subs.length) add(L.subtopics, subs.map(([code, p], k) => h('span', { class: k ? 'sub2' : '' }, `${k + 1}. ${subName(code)}${p != null ? ' · p ' + p3(p) : ''}`, k ? '' : h('br'))));
  } else {
    add(L.chapter, h('span', { class: 'dim' }, L.notScored));
  }
  holder.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.topicSec), facts));
  // provenance
  const pv = h('dl', { class: 'facts' });
  const addp = (k, ...v) => pv.append(h('dt', {}, k), h('dd', {}, ...v));
  if (d && d.url) addp(L.page, h('a', { href: d.url, target: '_blank', rel: 'noopener' }, d.url.replace(/^https?:\/\//, '').slice(0, 64) + ' ↗'));
  addp('OPD', h('span', { class: 'mono' }, `#${id} · ${c.body[i]}`));
  if (d) addp(L.build, h('span', { class: 'mono' }, `${(d.build || '').slice(-8)} · ${d.model || ''}`));
  const pids = d && ((d.aps && d.aps.pids) || d.prompt_ids || []);
  if (pids && pids.length) addp('prompt', h('span', { class: 'mono' }, pids.join(' ')));
  holder.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.prov), pv));
  // similar
  const sim = similar(i, tp);
  if (sim.length) {
    const ul = h('ul', { class: 'sim' });
    for (const j of sim) ul.append(h('li', { onclick: () => onOpen && onOpen(j), lang: c.lang[j] }, c.title[j],
      h('span', { class: 'm' }, `${fmtDate(c.date[j])} · ${bodyName(c.body[j])}${tp && tp.hit(j) ? ' · ' + (tp.names[UI.lang] || tp.names.de) : ''}`)));
    holder.append(h('div', { class: 'sec' }, h('div', { class: 'sl' }, L.similar), ul));
  }
}

export function decisionState(tp, id) {
  const L = t(), r = getDec(tp, id);
  if (!r) return '';
  const when = (r.at || '').replace('T', ' ').slice(0, 16);
  return `<b>${L.decided[r.d] || r.d}</b> · ${esc(r.by || '')} · ${when} · ${r.err ? `<span class="sig">${L.apiErr}</span>` : r.api ? L.apiSaved : L.localSaved}`;
}
