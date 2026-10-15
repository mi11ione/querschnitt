// Neues Thema: a topic in one sentence → proposed terms (one editable mono line) → yes/no decisions stream in, newest
// first, with a running line (read / flagged / seconds); the map fills as rows arrive. Needs the live API (CONTRACT §2).
// Without it (the static site) the tab replays a recorded real run (data/neu_replay.json, app/dev/make_replay.py): the
// same POST answer and SSE events, at the recorded pace or faster, through the same code path, labelled as a recording.
// With the API up but the model endpoint down (POST /adhoc 503 within seconds, or no decision for SLOW_S seconds) the run
// line offers the same recording, labelled as such; #neu?rec=1 opens it directly (docs/DEMO.md, Offline).
import { D, API, apiPost, liveTopic, registerTopic } from './data.js';
import { h, t, UI, num, toast, isoOfDay, dayNum, fmtDate } from './util.js';
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
  if (typeof tr === 'object') return Object.entries(tr).filter(([, v]) => v && (!Array.isArray(v) || v.length))
    .map(([l, v]) => `${l}: ${(Array.isArray(v) ? v : [v]).map(x => (x && typeof x === 'object' ? x.term : x)).join(', ')}`).join(' · ');
  return String(tr);
};

// strings of the replay (kept here: util.js holds the shared ones)
const R = {
  de: { lim: n => (n ? `höchstens ${n} Geschäfte` : 'alle Geschäfte'), play: 'Aufzeichnung abspielen', again: 'nochmals abspielen', speed: 'Tempo', rec: 'Aufzeichnung', last: 'zuletzt gelesen, neueste zuerst',
    line: (d, m, b) => `Aufzeichnung eines echten Laufs vom ${d}, Route ${m}, Build ${b}. Ein eigenes Thema liest nur der Live-Dienst; hier ist nichts eingebbar.`,
    down: 'Der Modell-Endpunkt antwortet nicht.', slow: s => `seit ${s} s keine Entscheidung vom Modell-Endpunkt`, fall: 'Aufzeichnung abspielen', back: 'zurück zur Eingabe',
    fallLine: (d, m, b) => `Aufzeichnung eines echten Laufs vom ${d}, Route ${m}, Build ${b}, keine Live-Antwort: der Modell-Endpunkt antwortet gerade nicht.` },
  fr: { lim: n => (n ? `au plus ${n} objets` : 'tous les objets'), play: 'Rejouer l’enregistrement', again: 'rejouer encore', speed: 'vitesse', rec: 'enregistrement', last: 'derniers lus, le plus récent en haut',
    line: (d, m, b) => `Enregistrement d’une exécution réelle du ${d}, route ${m}, build ${b}. Seul le service en ligne lit un thème propre ; ici, rien n’est saisissable.`,
    down: 'Le modèle ne répond pas.', slow: s => `aucune décision du modèle depuis ${s} s`, fall: 'Rejouer l’enregistrement', back: 'retour à la saisie',
    fallLine: (d, m, b) => `Enregistrement d’une exécution réelle du ${d}, route ${m}, build ${b}, pas une réponse en direct : le modèle ne répond pas en ce moment.` },
};
const r = () => R[UI.lang] || R.de;
const SPEEDS = [1, 4];
// a live run can be capped (POST /adhoc `limit`, newest affairs first): #neu?limit=25, or the quiet select beside the
// period; default: no cap. A recorded run plays once by itself per page load (the button replays it).
const LIMITS = [0, 25, 50];
const hashLimit = () => { const v = +new URLSearchParams(location.hash.split('?')[1] || '').get('limit'); return v > 0 ? Math.floor(v) : 0; };
const LIMIT0 = hashLimit(); // read at load, before the shell rewrites the hash
const REC0 = /[?&]rec=1/.test(location.hash); // #neu?rec=1: the recording, also when the API is up
const SLOW_S = 20, POST_S = 35; // a live run with no decision SLOW_S s after Enter (or the last one) offers the recording;
// POST /adhoc gives up after POST_S s (the recorded run: topic 5 s, first decision 4 s later)
let autoPlayed = false;
const dmy = iso => `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(0, 4)}`;

// An EventSource stand-in that dispatches the recorded events at their recorded `t` (seconds since job start) × speed.
class Replay {
  constructor(events, speed) {
    this.ev = events; this.i = 0; this.L = new Map(); this.speed = speed; this.base = 0; this.since = performance.now();
    this.onmessage = null; this.onerror = null;
    this.timer = setInterval(() => this.pump(), 50);
  }
  clock() { return this.base + (performance.now() - this.since) / 1000 * this.speed; }
  setSpeed(s) { this.base = this.clock(); this.since = performance.now(); this.speed = s; }
  addEventListener(type, fn) { if (!this.L.has(type)) this.L.set(type, []); this.L.get(type).push(fn); }
  pump() {
    const now = this.clock();
    while (this.timer && this.i < this.ev.length && this.ev[this.i].t <= now) {
      const e = this.ev[this.i++], msg = { type: e.event, data: JSON.stringify(e.data) };
      for (const fn of this.L.get(e.event) || []) fn(msg);
    }
    if (this.i >= this.ev.length) this.close();
  }
  close() { clearInterval(this.timer); this.timer = null; }
}
async function loadReplay() {
  for (const b of ['data/', 'data-fixture/']) {
    try { const res = await fetch(`${b}neu_replay.json`, { cache: 'no-cache' }); if (res.ok) return await res.json(); } catch (e) { /* next */ }
  }
  return null;
}

export class Neu {
  constructor(root) {
    this.root = root;
    this.field = h('textarea', { rows: 1, 'aria-label': 'Thema' });
    this.ex = h('textarea', { rows: 3 });
    this.exd = h('details', { class: 'nt-ex' }, h('summary'), this.ex);
    this.terms = h('input', { class: 'terms', type: 'text', hidden: true, spellcheck: 'false' });
    this.run = h('p', { class: 'runline', 'aria-live': 'polite' });
    this.per = h('select', { class: 'per', 'aria-label': 'Zeitraum' });
    this.perL = h('span', { class: 'perl' });
    this.limit = LIMIT0;
    this.lim = h('select', { class: 'per', 'aria-label': 'Umfang', onchange: () => { this.limit = +this.lim.value; history.replaceState(null, '', `#neu${this.limit ? `?limit=${this.limit}` : ''}`); } });
    this.saveB = h('button', { class: 'tb mono', type: 'button', hidden: true, style: 'font-size:12px', onclick: () => this.save() });
    this.fallB = h('button', { class: 'tb mono', type: 'button', hidden: true, style: 'font-size:12px', onclick: () => this.fallback() });
    this.head = h('div', { class: 'nt' }, h('div', { class: 'nt-field' }, this.field), h('p', { class: 'perrow' }, this.per, ' ', this.lim, this.perL), this.exd, this.terms, h('div', { class: 'runrow' }, this.run, this.saveB, this.fallB));
    this.field.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.start(); } });
    this.field.addEventListener('input', () => { this.field.style.height = 'auto'; this.field.style.height = `${this.field.scrollHeight}px`; });
    this.terms.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); this.start(this.terms.value); } });
    this.board = new Board(root, { topic: liveTopic('neu', { de: '', fr: '' }, new Map()), picker: false, pult: false, order: 'arrival', head: this.head });
    // replay (static site only): label, play button, tempo, the latest decisions
    this.speed = 4;
    this.recL = h('p', { class: 'nt-rec', hidden: true });
    this.playB = h('button', { class: 'box', type: 'button', onclick: () => this.start() });
    this.speedEl = h('span', { class: 'nt-speed' });
    this.backB = h('button', { class: 'tb nt-back', type: 'button', hidden: true, onclick: () => this.back() });
    this.playRow = h('p', { class: 'nt-play', hidden: true }, this.playB, this.speedEl, this.backB);
    this.feed = h('ol', { class: 'nt-feed', hidden: true });
    this.head.querySelector('.perrow').after(this.recL, this.playRow);
    this.board.reg.prepend(this.feed); // the list column: hits only, so the stream of every decision goes above it
    this.relang();
    if (!API.live) loadReplay().then(rec => {
      if (!(rec && rec.events) || API.live) return;
      this.rec = rec; this.relang(); this.shown();
    });
    if (API.live && REC0) this.fallback();
  }
  // the model endpoint is down (or silent): the run line offers the recording; one click plays it, labelled as one
  offer() { if (API.live && !this.fall) { this.fallB.textContent = `[${r().fall}]`; this.fallB.hidden = false; } }
  async fallback() {
    if (this.es) { this.es.close(); this.es = null; }
    clearInterval(this.tick);
    if (this.slug) apiPost(`/adhoc/${encodeURIComponent(this.slug)}/stop`, {}).catch(() => { /* gone already */ });
    if (!this.fall) this.typed = this.field.value;
    const rec = this.rec0 || (this.rec0 = await loadReplay());
    if (!(rec && rec.events)) { this.run.className = 'runline err'; this.run.textContent = `${r().down} (neu_replay.json –)`; return; }
    this.fall = true; this.rec = rec; this.played = false; this.fallB.hidden = true;
    this.relang(); this.start();
  }
  back() { // from the recording to the live field
    if (this.es) { this.es.close(); this.es = null; }
    clearInterval(this.tick); this.runId = (this.runId || 0) + 1;
    this.fall = false; this.rec = null; this.played = false;
    this.field.readOnly = false; this.field.value = this.typed || ''; this.exd.hidden = false;
    this.recL.hidden = true; this.playRow.hidden = true; this.feed.hidden = true; this.perL.textContent = ''; this.board.fixedPer = null;
    this.terms.hidden = true; this.terms.value = ''; this.tp = null; this.board.S.brush = null; // nothing of the recording stays
    this.board.setTopic(liveTopic('neu', { de: '', fr: '' }, new Map()));
    this.run.className = 'runline'; this.relang(); this.field.focus();
  }
  // the tab is open: in static mode the recording starts by itself, once per page load
  shown() { if (this.rec && !autoPlayed && !this.root.hidden && !this.es && !API.live) { autoPlayed = true; this.start(); } }
  renderSpeed() {
    const R0 = r();
    this.speedEl.replaceChildren(`${R0.speed} `, ...SPEEDS.flatMap((s, k) => [k ? ' ' : '', h('button', { class: 'tb', type: 'button', 'aria-pressed': String(s === this.speed),
      onclick: () => { this.speed = s; if (this.es && this.es.setSpeed) this.es.setSpeed(s); this.renderSpeed(); if (this.lineNow) this.lineNow(); } }, `×${s}`)]));
  }
  renderFeed() {
    const L = t(), c = D.c;
    const last = [...this.tp.dec].slice(-6).reverse();
    this.feed.hidden = !last.length;
    this.feed.replaceChildren(h('li', { class: 'hd' }, r().last), ...last.map(([id, d]) => {
      const x = d.rec || {}, i = D.rowOf.get(id);
      const title = x.title || (i != null ? c.title[i] : String(id));
      return h('li', {}, h('button', { type: 'button', lang: x.lang || null, onclick: () => { if (i != null) this.board.select(id); } },
        h('span', { class: `v${d.flag ? ' sig' : ''}` }, `${d.flag ? L.yes : L.no} ${d.p.toFixed(3)}`, h('br'), `${d.t.toFixed(1)} ${L.secs}`),
        h('span', { class: 't' }, title), h('span', { class: 'm' }, `${x.parl || x.body || ''} · ${fmtDate(x.date)}`)));
    }));
  }
  relang() {
    const L = t();
    this.field.placeholder = L.ntPh; this.exd.querySelector('summary').textContent = L.ntEx; this.saveB.textContent = `[${L.ntSave}]`;
    const pv = this.per.value || 'week';
    this.per.replaceChildren(...Object.entries(L.periods).map(([k, v]) => h('option', { value: k, selected: k === pv }, v)));
    this.per.disabled = !API.live || !!this.fall;
    const lv = [...new Set([...LIMITS, this.limit])].sort((a, b) => a - b);
    this.lim.replaceChildren(...lv.map(k => h('option', { value: String(k), selected: k === this.limit }, r().lim(k))));
    this.lim.hidden = !API.live || !!this.fall; // the cap is for a live run only
    this.fallB.textContent = `[${r().fall}]`; this.backB.textContent = r().back; this.backB.hidden = !this.fall;
    this.field.disabled = !API.live && !this.rec; this.ex.disabled = !API.live;
    this.root.classList.toggle('nt-static', !API.live && !this.rec);
    this.root.classList.toggle('nt-replay', !!this.rec);
    if (this.rec) { // a recorded run: its sentence, read-only; the label says what it is
      const R0 = r(), x = this.rec;
      this.field.value = x.sentence || ''; this.field.readOnly = true; this.exd.hidden = true;
      this.field.style.height = 'auto'; this.field.style.height = `${this.field.scrollHeight}px`;
      this.recL.hidden = false; this.playRow.hidden = false;
      this.recL.textContent = (this.fall ? R0.fallLine : R0.line)(dmy(x.recorded), x.model, x.build_short);
      // the screen names one period, the recorded one, from the start (before the replayed POST answer arrives)
      const rp = (x.post && x.post.period) || (x.summary && x.summary.period);
      if (rp && rp[0] && !this.board.fixedPer) { this.board.fixedPer = [dayNum(rp[0]), dayNum(rp[1])]; this.perL.textContent = ` ${L.periodRead} ${rp[0]} – ${rp[1]}`; this.board.refresh(); }
      this.playB.textContent = this.played ? R0.again : R0.play;
      this.renderSpeed();
      if (!this.played) this.run.textContent = '';
    } else if (!API.live) { this.run.textContent = L.ntStatic; }
    else if (!this.es) this.run.textContent = L.ntRun;
    this.board.relang && this.board.relang();
  }
  async start(terms) {
    const L = t(), sentence = this.field.value.trim(), rec = !API.live || this.fall ? this.rec : null;
    if ((!API.live && !rec) || !sentence) return;
    if (this.es) { this.es.close(); this.es = null; }
    clearInterval(this.tick); // a restart: the previous run's clock stops writing the line
    if (rec) { this.played = true; this.playB.textContent = r().again; this.feed.hidden = true; }
    const run = this.runId = (this.runId || 0) + 1;
    const examples = this.ex.value.split('\n').map(x => x.trim()).filter(Boolean);
    const body = { sentence, lang: guessLang(sentence) };
    const pv = this.per.value || 'week';
    if (pv === 'month') { body.from = isoOfDay(D.dmax - 30); body.to = isoOfDay(D.dmax); }
    else if (pv === 'y2526') body.period = '2025-01-01..2026-12-31';
    if (examples.length) body.examples = examples;
    if (this.limit) body.limit = this.limit;
    if (terms) body.terms = terms;
    this.run.className = 'runline'; this.run.textContent = rec ? `${L.read} 0 · ${r().rec} ×${this.speed} · …` : '…';
    if (rec && rec.post && rec.post.topic && rec.post.topic.names) this.board.setTopic(liveTopic('neu', rec.post.topic.names, new Map())); // its name from the first frame
    let res;
    if (rec) { // the recorded POST answer, after the recorded topic generation time
      await new Promise(f => setTimeout(f, (rec.post_lat || 0) * 1000 / this.speed));
      if (run !== this.runId) return;
      res = rec.post;
    } else {
      this.fallB.hidden = true; this.tp = null; this.t0 = performance.now(); // the quiet clock starts at Enter: a slow topic request counts too
      clearTimeout(this.watch); this.watch = setTimeout(() => { if (run === this.runId && !this.tp) this.offer(); }, SLOW_S * 1000);
      try { res = await Promise.race([apiPost('/adhoc', body), new Promise((_, no) => setTimeout(() => no(new Error('timeout')), POST_S * 1000))]); }
      catch (e) { // 503: the API is up, the model endpoint is not (adhoc.py answers in seconds); the recording is one click away
        if (run !== this.runId) return;
        this.run.className = 'runline err'; this.run.textContent = e.message === '503' || e.message === 'timeout' ? r().down : `${L.apiErr} ${e.message}`; this.offer(); return;
      }
      if (run !== this.runId) return;
    }
    const slug = res.slug, topic = res.topic || {};
    if (!rec) this.slug = slug;
    const names = topic.names || { de: sentence, fr: sentence, it: sentence };
    const tp = liveTopic(slug, names, new Map());
    this.tp = tp; this.board.setTopic(tp);
    const tt = termsText(topic.terms || topic.keywords || res.terms);
    this.terms.hidden = !tt; this.terms.value = tt;
    this.saveB.hidden = true;
    const showPeriod = p => {
      if (!p || !p[0]) return;
      const a = String(p[0]).slice(0, 10), z = String(p[1]).slice(0, 10) > isoOfDay(D.dmax) ? isoOfDay(D.dmax) : String(p[1]).slice(0, 10);
      this.perL.textContent = ` ${L.periodRead} ${a} – ${z}`;
      // the run read one period: header, Überblick panel and timeline name that one, not the brushed whole weeks
      // (until a person brushes other weeks)
      this.board.fixedPer = [dayNum(a), dayNum(z)];
      const wa = Math.max(0, Math.floor((dayNum(a) - D.w0) / 7)), wz = Math.min(D.nWeeks - 1, Math.floor((dayNum(z) - D.w0) / 7));
      if (wz >= wa) { this.board.S.brush = [wa, wz]; this.board.refresh(); }
    };
    showPeriod(res.period);
    const t0 = performance.now(); let read = 0, flagged = 0, outside = 0, total = null, done = false, lastT = rec ? t0 : this.t0;
    const line = () => {
      const secs = Math.floor(rec && this.es && this.es.clock ? Math.min(this.es.clock(), rec.summary.seconds) : done && rec ? rec.summary.seconds : (performance.now() - t0) / 1000);
      this.run.innerHTML = `<b>${L.read} ${num(read)}${total ? ' / ' + num(total) : ''}</b> · ${L.flagged} ${num(flagged)} · ${secs} ${L.secs}${outside ? ` · +${num(outside)}` : ''}${rec ? ` · ${r().rec} ×${this.speed}` : ''}${done ? '' : ' · …'}`;
    };
    this.lineNow = () => { if (!done) line(); };
    let pend = false;
    const kick = () => { if (pend) return; pend = true; setTimeout(() => { pend = false; this.board.refresh(); if (rec) this.renderFeed(); if (!done) line(); }, 250); };
    const es = this.es = rec ? new Replay(rec.events, this.speed) : new EventSource(`${API.base}/adhoc/${encodeURIComponent(slug)}/stream`);
    const onData = (raw, type) => {
      let d; try { d = JSON.parse(raw); } catch (e) { return; }
      if (d.id != null && d.p != null) {
        read++; const flag = d.flag != null ? !!d.flag : d.p >= 0.5; if (flag) flagged++;
        if (!D.rowOf.has(d.id)) outside++;
        tp.dec.set(d.id, rec ? { p: d.p, flag, t: d.t, rec: d } : { p: d.p, flag, t: d.t });
        lastT = performance.now(); if (!rec) this.fallB.hidden = true;
        kick();
      }
      const pr = d.progress || (type === 'progress' ? d : null);
      if (pr) { if (pr.total != null) total = pr.total; if (pr.read != null) read = Math.max(read, pr.read); kick(); }
      if (type === 'topic' && d.period) showPeriod(d.period);
      if (type === 'terms' && d.terms) { const x = termsText(d.terms); this.terms.hidden = !x; this.terms.value = x; }
      if (type === 'error') { stopWhy = d.error || L.apiErr; finish(); return; }
      if (d.done || type === 'done') { if (d.error) stopWhy = d.error; if (d.in_period != null && total == null) total = d.in_period; finish(); }
    };
    let stopWhy = null;
    const finish = () => {
      if (done) return;
      done = true; es.close(); this.es = null; this.board.refresh(); line(); if (rec) this.renderFeed();
      const early = stopWhy || (total != null && read < total);
      if (early) { // a run that stopped early says so and is not offered as complete
        this.run.className = 'runline err';
        this.run.textContent = `${L.stopped(num(read), total != null ? num(total) : '?', String(stopWhy || '').replace(/^\w+\(['"]?|['"]?\)$/g, '').slice(0, 80))} · ${L.flagged} ${num(flagged)}`;
        this.saveB.hidden = true;
      } else this.saveB.hidden = !!rec; // a replay is not saved as a topic
      if (early && !rec) this.offer();
    };
    es.onmessage = e => onData(e.data, 'message');
    es.addEventListener('progress', e => onData(e.data, 'progress'));
    es.addEventListener('decision', e => onData(e.data, 'decision'));
    es.addEventListener('done', e => onData(e.data || '{}', 'done'));
    es.addEventListener('topic', e => onData(e.data, 'topic'));
    es.addEventListener('terms', e => onData(e.data, 'terms'));
    es.addEventListener('error', e => { if (e.data) onData(e.data, 'error'); });
    es.onerror = () => { if (!done) { if (read) { stopWhy = stopWhy || L.apiErr; finish(); } else { this.run.className = 'runline err'; this.run.textContent = L.apiErr; es.close(); this.es = null; this.offer(); } } };
    this.tick = setInterval(() => {
      if (done || !this.es) { clearInterval(this.tick); return; }
      line();
      const quiet = Math.floor((performance.now() - lastT) / 1000);
      if (!rec && quiet >= SLOW_S) { this.offer(); this.run.append(` · ${r().slow(quiet)}`); }
    }, 1000);
    line();
  }
  save() { if (!this.tp) return; save(this.tp); toast(t().ntSaved); this.saveB.hidden = true; }
}
