// Virtualised ruled list: fixed row height, only visible rows in the DOM.
import { h } from './util.js';

export const ROW_H = 52;

export class VList {
  constructor(root, { render, onOpen }) {
    this.root = root; this.render = render; this.onOpen = onOpen; this.items = []; this.sel = -1;
    this.sp = h('div', { class: 'sp' }); root.append(this.sp);
    root.setAttribute('tabindex', '0'); root.setAttribute('role', 'listbox');
    root.addEventListener('scroll', () => this.paint());
    root.addEventListener('click', e => { const r = e.target.closest('.row'); if (r) this.onOpen(+r.dataset.i); });
    this.ro = new ResizeObserver(() => this.paint()); this.ro.observe(root);
  }
  set(items, sel = this.sel) { this.items = items; this.sel = sel; this.sp.style.height = `${items.length * ROW_H}px`; this.paint(true); }
  select(pos, scroll = true) {
    this.sel = pos;
    if (scroll && pos >= 0) {
      const top = pos * ROW_H, vh = this.root.clientHeight;
      if (top < this.root.scrollTop) this.root.scrollTop = top;
      else if (top + ROW_H > this.root.scrollTop + vh) this.root.scrollTop = top + ROW_H - vh;
    }
    this.paint(true);
  }
  paint(force) {
    const st = this.root.scrollTop, vh = this.root.clientHeight || 600;
    const a = Math.max(0, Math.floor(st / ROW_H) - 8), b = Math.min(this.items.length, Math.ceil((st + vh) / ROW_H) + 8);
    if (!force && a === this.a && b === this.b) return;
    this.a = a; this.b = b;
    const frag = document.createDocumentFragment();
    for (let p = a; p < b; p++) {
      const el = this.render(this.items[p], p);
      el.classList.add('row'); el.style.top = `${p * ROW_H}px`; el.dataset.i = p;
      el.setAttribute('role', 'option'); el.setAttribute('aria-selected', p === this.sel ? 'true' : 'false');
      frag.append(el);
    }
    this.sp.replaceChildren(frag);
  }
}
