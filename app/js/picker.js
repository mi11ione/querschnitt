// Topic picker: ad-hoc topics (any of their names in any language), APS chapters and their subtopics.
import { TOPICS, norm } from './data.js';
import { h, t, UI, num } from './util.js';

export class Picker {
  constructor(root, { onPick }) {
    this.onPick = onPick; this.cur = null; this.pos = 0; this.items = [];
    this.inp = h('input', { type: 'text', 'aria-label': 'Thema', role: 'combobox', 'aria-expanded': 'false', autocomplete: 'off', spellcheck: 'false' });
    this.lb = h('ul', { class: 'lb', role: 'listbox', hidden: true });
    root.append(this.inp, this.lb);
    this.inp.addEventListener('focus', () => { this.inp.select(); this.open(''); });
    this.inp.addEventListener('input', () => this.open(this.inp.value));
    this.inp.addEventListener('blur', () => setTimeout(() => this.close(), 150));
    this.inp.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') { this.move(1); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { this.move(-1); e.preventDefault(); }
      else if (e.key === 'Enter') { const it = this.items[this.pos]; if (it) this.pick(it); e.preventDefault(); }
      else if (e.key === 'Escape') { this.close(); this.inp.blur(); e.stopPropagation(); }
    });
    this.lb.addEventListener('mousedown', e => { const li = e.target.closest('li[data-i]'); if (li) { e.preventDefault(); this.pick(this.items[+li.dataset.i]); } });
  }
  label(tp) { return tp ? (tp.names[UI.lang] || tp.names.de) : ''; }
  set(tp) { this.cur = tp; this.inp.value = this.label(tp); this.inp.placeholder = t().topicPh; }
  open(q) {
    const n = norm(q), L = t();
    const match = tp => !n || tp.aliases.some(a => norm(a).includes(n)) || Object.values(tp.names).some(v => norm(v).includes(n)) || norm(tp.code).includes(n);
    const groups = [[L.allGroup, TOPICS.filter(x => x.kind === 'all')], [L.adhoc, TOPICS.filter(x => x.kind === 'adhoc' && !x.saved)], [L.savedTopics, TOPICS.filter(x => x.saved || x.kind === 'live')], [L.ownSchemes, TOPICS.filter(x => x.kind === 'be')], [L.chapters, TOPICS.filter(x => x.kind === 'chapter' || x.kind === 'sub')]];
    const curCh = this.cur && (this.cur.kind === 'chapter' ? this.cur.idx : this.cur.kind === 'sub' ? this.cur.ch : null);
    this.items = []; const frag = [];
    for (const [g, list] of groups) {
      const sel = list.filter(tp => tp.kind !== 'sub' ? match(tp) : (n ? match(tp) : tp.ch === curCh));
      if (!sel.length) continue;
      frag.push(h('li', { class: 'grp', role: 'presentation' }, g));
      for (const tp of sel) {
        const i = this.items.length; this.items.push(tp);
        const cd = tp.kind === 'chapter' ? tp.code.replace('aps:', '') : tp.kind === 'sub' ? '' : tp.kind === 'live' ? 'neu' : tp.kind === 'be' ? tp.scope : tp.kind === 'all' ? '' : 'ad hoc';
        frag.push(h('li', { 'data-i': i, role: 'option', class: `${tp.kind === 'sub' ? 'sub' : ''} ${tp.count ? '' : 'off'}` },
          h('span', { class: 'cd' }, cd), h('span', { class: 'nm' }, this.label(tp)), h('span', { class: 'n' }, tp.count ? num(tp.count) : '–')));
      }
    }
    this.lb.replaceChildren(...frag);
    this.pos = Math.max(0, this.items.indexOf(this.cur)); if (n) this.pos = 0;
    this.lb.hidden = !this.items.length; this.inp.setAttribute('aria-expanded', String(!this.lb.hidden));
    this.mark();
  }
  move(d) { this.pos = Math.max(0, Math.min(this.items.length - 1, this.pos + d)); this.mark(); }
  mark() {
    for (const li of this.lb.querySelectorAll('li[data-i]')) {
      const on = +li.dataset.i === this.pos; li.setAttribute('aria-selected', String(on));
      if (on) li.scrollIntoView({ block: 'nearest' });
    }
  }
  close() { this.lb.hidden = true; this.inp.setAttribute('aria-expanded', 'false'); if (this.cur) this.inp.value = this.label(this.cur); }
  pick(tp) { this.set(tp); this.close(); this.inp.blur(); this.onPick(tp); }
  focus() { this.inp.focus(); }
}
