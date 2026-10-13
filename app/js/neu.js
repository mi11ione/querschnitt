// Neues Thema: a topic in one sentence → proposed terms (one editable mono line) → yes/no decisions stream in, newest
// first, with a running line (read / flagged / seconds); the map fills as rows arrive. Needs the live API (CONTRACT §2).
import { D, API, apiPost, liveTopic, registerTopic } from './data.js';
import { h, t, UI, num, toast } from './util.js';
import { Board } from './board.js';

const SAVED = 'qs.adhoc.v1';
export function loadSaved() {
  let arr = [];
  try { arr = JSON.parse(localStorage.getItem(SAVED) || '[]'); } catch (e) { arr = []; }
  for (const x of arr) {
    const dec = new Map(x.dec.map(([id, p, f]) => [id, { p, flag: !!f }]));
    const tp = liveTopic(x.slug, x.names, dec); tp.count = x.dec.filter(d => d[2]).length; registerTopic(tp);
  }
}
function save(tp) {
  let arr = [];
  try { arr = JSON.parse(localStorage.getItem(SAVED) || '[]'); } catch (e) { arr = []; }
  arr = arr.filter(x => x.slug !== tp.id.slice(6));
  arr.push({ slug: tp.id.slice(6), names: tp.names, dec: [...tp.dec].map(([id, d]) => [id, d.p, d.flag ? 1 : 0]) });
  try { localStorage.setItem(SAVED, JSON.stringify(arr)); } catch (e) { /* storage off */ }
  tp.count = [...tp.dec.values()].filter(d => d.flag).length; registerTopic(tp);
}
const guessLang = s => {
  const w = ` ${s.toLowerCase()} `;
  const sc = { de: / (der|die|das|und|für|im|von|mit) /g, fr: / (le|la|les|des|et|pour|dans|du) /g, it: / (il|lo|gli|della|e|per|nel|del) /g };
  let best = UI.lang, m = 0;
  for (const [l, re] of Object.entries(sc)) { const n = (w.match(re) || []).length; if (n > m) { m = n; best = l; } }
  return best;
};
const termsText = tr => {
  if (!tr) return '';
  if (Array.isArray(tr)) return tr.join(', ');
  if (typeof tr === 'object') return Object.entries(tr).map(([l, v]) => `${l}: ${(Array.isArray(v) ? v : [v]).join(', ')}`).join(' · ');
  return String(tr);
};

export class Neu {
  constructor(root) {
    this.root = root;
    this.field = h('textarea', { rows: 1, 'aria-label': 'Thema' });
    this.ex = h('textarea', { rows: 3 });
    this.exd = h('details', { class: 'nt-ex' }, h('summary'), this.ex);
    this.terms = h('input', { class: 'terms', type: 'text', hidden: true, spellcheck: 'false' });
    this.run = h('p', { class: 'runline', 'aria-live': 'polite' });
    this.saveB = h('button', { class: 'tb mono', type: 'button', hidden: true, style: 'font-size:12px', onclick: () => this.save() });
    this.head = h('div', { class: 'nt' }, h('div', { class: 'nt-field' }, this.field), this.exd, this.terms, h('div', { class: 'runrow' }, this.run, this.saveB));
    this.field.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.start(); } });
    this.field.addEventListener('input', () => { this.field.style.height = 'auto'; this.field.style.height = `${this.field.scrollHeight}px`; });
    this.terms.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); this.start(this.terms.value); } });
    this.board = new Board(root, { topic: liveTopic('neu', { de: '', fr: '' }, new Map()), picker: false, pult: false, order: 'arrival', head: this.head });
    this.relang();
  }
  relang() {
    const L = t();
    this.field.placeholder = L.ntPh; this.exd.querySelector('summary').textContent = L.ntEx; this.saveB.textContent = `[${L.ntSave}]`;
    this.field.disabled = !API.live; this.ex.disabled = !API.live;
    this.root.classList.toggle('nt-static', !API.live);
    if (!API.live) { this.run.textContent = L.ntStatic; }
    else if (!this.es) this.run.textContent = L.ntRun;
    this.board.relang && this.board.relang();
  }
  async start(terms) {
    const L = t(), sentence = this.field.value.trim();
    if (!API.live || !sentence) return;
    if (this.es) { this.es.close(); this.es = null; }
    const examples = this.ex.value.split('\n').map(x => x.trim()).filter(Boolean);
    const body = { sentence, lang: guessLang(sentence), period: 'last_week' };
    if (examples.length) body.examples = examples;
    if (terms) body.terms = terms;
    this.run.className = 'runline'; this.run.textContent = '…';
    let res;
    try { res = await apiPost('/adhoc', body); } catch (e) { this.run.className = 'runline err'; this.run.textContent = `${L.apiErr} ${e.message}`; return; }
    const slug = res.slug, topic = res.topic || {};
    const names = topic.names || { de: sentence, fr: sentence, it: sentence };
    const tp = liveTopic(slug, names, new Map());
    this.tp = tp; this.board.setTopic(tp);
    const tt = termsText(topic.terms || topic.keywords || res.terms);
    this.terms.hidden = !tt; this.terms.value = tt;
    this.saveB.hidden = true;
    const t0 = performance.now(); let read = 0, flagged = 0, outside = 0, total = null, done = false;
    const line = () => {
      const secs = Math.floor((performance.now() - t0) / 1000);
      this.run.innerHTML = `<b>${L.read} ${num(read)}${total ? ' / ' + num(total) : ''}</b> · ${L.flagged} ${num(flagged)} · ${secs} ${L.secs}${outside ? ` · +${num(outside)}` : ''}${done ? '' : ' · …'}`;
    };
    let pend = false;
    const kick = () => { if (pend) return; pend = true; setTimeout(() => { pend = false; this.board.refresh(); line(); }, 250); };
    const es = this.es = new EventSource(`${API.base}/adhoc/${encodeURIComponent(slug)}/stream`);
    const onData = (raw, type) => {
      let d; try { d = JSON.parse(raw); } catch (e) { return; }
      if (d.id != null && d.p != null) {
        read++; const flag = d.flag != null ? !!d.flag : d.p >= 0.5; if (flag) flagged++;
        if (!D.rowOf.has(d.id)) outside++;
        tp.dec.set(d.id, { p: d.p, flag, t: d.t });
        kick();
      }
      const pr = d.progress || (type === 'progress' ? d : null);
      if (pr) { if (pr.total != null) total = pr.total; if (pr.read != null) read = Math.max(read, pr.read); kick(); }
      if (d.done || type === 'done') finish();
    };
    const finish = () => { done = true; es.close(); this.es = null; this.board.refresh(); line(); this.saveB.hidden = false; };
    es.onmessage = e => onData(e.data, 'message');
    es.addEventListener('progress', e => onData(e.data, 'progress'));
    es.addEventListener('decision', e => onData(e.data, 'decision'));
    es.addEventListener('done', e => onData(e.data || '{}', 'done'));
    es.onerror = () => { if (!done) { if (read) finish(); else { this.run.className = 'runline err'; this.run.textContent = L.apiErr; es.close(); this.es = null; } } };
    this.tick = setInterval(() => { if (done || !this.es) clearInterval(this.tick); else line(); }, 1000);
    line();
  }
  save() { if (!this.tp) return; save(this.tp); toast(t().ntSaved); this.saveB.hidden = true; }
}
