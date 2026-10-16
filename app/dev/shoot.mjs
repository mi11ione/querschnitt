// Headless check: opens the app in Chrome over the DevTools protocol (no npm deps), runs scripted steps, prints console
// errors and writes screenshots to app/dev/shots/. Usage: node app/dev/shoot.mjs [base-url|-] [only-name]
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = process.argv[2] && process.argv[2] !== '-' ? process.argv[2] : 'http://127.0.0.1:8765/';
const LIVE = process.env.LIVE || 'http://127.0.0.1:8766/';
const ONLY = process.argv[3] || null;
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333 + Math.floor(Math.random() * 500);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const SCEN = [
  { name: 'woche-1440', w: 1440, h: 900, url: '', steps: [`window.__wocheReady`], print: `[...document.querySelectorAll('.wo-a')].map(e=>e.querySelector('.m').textContent+' | '+e.querySelector('.q').textContent).join(String.fromCharCode(10))` },
  // what the landing view fetches (bytes as served by the dev server, i.e. uncompressed)
  { name: 'firstload', w: 1440, h: 900, url: '', steps: [`window.__wocheReady`, 500], print: `(()=>{const r=performance.getEntriesByType('resource').filter(e=>/\.(json|js|css|woff2)$/.test(e.name));return r.map(e=>e.name.replace(location.origin+'/','')+' '+(e.decodedBodySize/1e6).toFixed(2)).join(', ')+' | total MB '+(r.reduce((a,e)=>a+e.decodedBodySize,0)/1e6).toFixed(2)})()` },
  { name: 'woche-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#woche', steps: [`window.__wocheReady`] },
  { name: 'woche-375', w: 375, h: 812, mobile: true, url: '#woche', full: true, steps: [`window.__wocheReady`] },
  { name: 'woche-prev-1440', w: 1440, h: 900, url: '#woche', steps: [`window.__wocheReady`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'['}))`, `window.__wocheReady`], print: `location.hash` },
  // a week after the newest complete one (export lag): the quiet note under the sentence
  { name: 'woche-lag-1440', w: 1440, h: 900, url: '#woche', steps: [`window.__wocheReady`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:']'}))`, `window.__wocheReady`], print: `location.hash + ' | ' + (document.querySelector('.wo-lag')||{}).textContent` },
  { name: 'woche-lag-fr-375', w: 375, h: 812, mobile: true, lang: 'fr', url: '#woche', steps: [`window.__wocheReady`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:']'}))`, `window.__wocheReady`] },
  { name: 'woche-open-1440', w: 1440, h: 900, url: '#woche', steps: [`window.__wocheReady`, `document.querySelector('.wo-a').click()`, 800], print: `location.hash` },
  { name: 'ueber-1440', w: 1440, h: 900, url: '#ueber' },
  { name: 'ueber-saved-1440', w: 1440, h: 900, url: '#ueber', steps: [`document.querySelector('.atl-sv').scrollIntoView({ block: 'center' })`] },
  { name: 'ueber-saved-fr-375', w: 375, h: 812, mobile: true, lang: 'fr', url: '#ueber', steps: [`document.querySelector('.atl-sv').scrollIntoView({ block: 'center' })`] },
  { name: 'ueber-375', w: 375, h: 812, mobile: true, url: '#ueber', full: true },
  { name: 'ueber-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#ueber' },
  { name: 'karte-1440', w: 1440, h: 900, url: '#karte' },
  { name: 'karte-detail-1440', w: 1440, h: 900, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'karte-search-1440', w: 1440, h: 900, url: '#karte', steps: [`(()=>{const q=document.querySelector('#v-karte .filters input');q.value='rechenzentr|data cent|centre de donn|centri dati|datacenter';q.dispatchEvent(new Event('input'))})()`, 400, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'pult-1440', w: 1440, h: 900, url: '#karte?m=pult&tab=todo', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'karte-fr-1440', w: 1440, h: 900, url: '#karte', steps: [`localStorage.clear()`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'f'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'karte-1100', w: 1100, h: 800, url: '#karte' },
  { name: 'neu-1440', w: 1440, h: 900, url: '#neu', print: `document.querySelector('#v-neu .runline').textContent` },
  { name: 'pruef-1440', w: 1440, h: 900, url: '#pruef' },
  { name: 'karte-375', w: 375, h: 812, mobile: true, url: '#karte', full: true },
  { name: 'detail-375', w: 375, h: 812, mobile: true, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.querySelector('#v-karte .case').scrollIntoView()`] },
  { name: 'pruef-375', w: 375, h: 812, mobile: true, url: '#pruef', full: true },
  { name: 'karte-320', w: 320, h: 700, mobile: true, url: '#karte', check320: true },
  { name: 'pult-decide-1440', w: 1440, h: 900, url: '#karte?m=pult&tab=todo', steps: [`localStorage.setItem('qs.who','R. Test')`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'1'}))`, 400, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'2'}))`, 400, `document.querySelectorAll('#v-karte .tab')[3].click()`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'neu-live-1440', live: true, w: 1440, h: 900, url: '#neu', steps: [`(()=>{const f=document.querySelector('.nt-field textarea');f.value='Schule, Unterricht, Lehrpersonen und Bildung';f.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()`, 5000, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'pult-live-1440', live: true, w: 1440, h: 900, url: '#karte?m=pult&tab=todo', steps: [`localStorage.setItem('qs.who','R. Test')`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'1'}))`, 600, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'k'}))`] },
  { name: 'picker-1440', w: 1440, h: 900, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'t'}))`, `(()=>{const i=document.querySelector('.picker input');i.value='verk';i.dispatchEvent(new Event('input'))})()`] },
  { name: 'chapter-1440', w: 1440, h: 900, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'t'}))`, `(()=>{const i=document.querySelector('.picker input');i.value='numérique';i.dispatchEvent(new Event('input'));i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'t'}))`, `(()=>{const i=document.querySelector('.picker input');i.value='Gesundheit';i.dispatchEvent(new Event('input'));i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `window.__csv = __qs.karte.exportCsv().then(()=>'ok',e=>'ERR '+e)`] },
  { name: 'bern-1440', w: 1440, h: 900, url: '#karte?t=be-directorates', steps: [`(()=>{const k=__qs.karte, c=__qs.D.c; const i=k.items.find(i=>c.bi[i]===1); if(i!=null) k.select(c.id[i]);})()`] },
  { name: 'bern-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#karte?t=be-directorates', steps: [`(()=>{const k=__qs.karte, c=__qs.D.c; const i=k.items.find(i=>c.bi[i]===1); if(i!=null) k.select(c.id[i]);})()`,
     `(URL.createObjectURL=b=>{b.text().then(t=>window.__csv=t);return '#'},HTMLAnchorElement.prototype.click=function(){})`, `__qs.karte.exportCsv()`, 800], print: `(()=>{const L=(window.__csv||'').split(String.fromCharCode(10));return L.slice(0,2).concat(L.slice(-1)).join(' ¶ ')})()` },
  { name: 'csv-fr', w: 1440, h: 900, lang: 'fr', url: '#karte', steps: [`(URL.createObjectURL=b=>{b.text().then(t=>window.__csv=t);return '#'},HTMLAnchorElement.prototype.click=function(){})`, `__qs.karte.exportCsv()`, 1500], print: `(()=>{const L=(window.__csv||'').split(String.fromCharCode(10));return L.slice(0,2).concat(L.slice(-1)).join(' ¶ ')})()` },
  { name: 'evidence', w: 1440, h: 900, url: '#karte', steps: [], print: `import('./js/case.js').then(m=>[m.highlight('abc def ghi',{field:'text',start:4,end:7,quote:'def'},'text','de').innerHTML, m.highlight('abc def ghi',{field:'text',start:1,end:2,quote:'ghi'},'text','de').innerHTML, m.highlight('abc',{field:'title_long',start:0,end:1,quote:'a'},'text','de').innerHTML].join(' | '))` },
  { name: 'pult-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#karte?m=pult&tab=todo', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'pruef-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#pruef' },
  { name: 'neu-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#neu' },
  { name: 'group-1440', w: 1440, h: 900, url: '#karte', steps: [`(()=>{const k=__qs.karte; const p=k.rows.findIndex(g=>g.length>1); k.select(__qs.D.c.id[k.rows[p][0]]);})()`] },
  { name: 'evidence-text-1440', w: 1440, h: 900, url: '#karte?a=340930' },
  { name: 'evidence-title-1440', w: 1440, h: 900, url: '#karte?a=340883' },
  { name: 'pult-week-1440', w: 1440, h: 900, url: '#karte?m=pult&tab=neu', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'overwrite-1440', w: 1440, h: 900, url: '#karte', steps: [`localStorage.setItem('qs.who','R. Test')`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'2'}))`, 600, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'k'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'1'}))`] },
  { name: 'chapter-corr-1440', w: 1440, h: 900, url: '#karte?t=aps%3A1.6.2.&m=pult&tab=neu', steps: [`localStorage.setItem('qs.who','R. Test')`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'2'}))`, 800] },
  { name: 'bern-corr-1440', w: 1440, h: 900, url: '#karte?t=be-directorates&m=pult&tab=todo', steps: [`localStorage.setItem('qs.who','R. Test')`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'2'}))`, 800] },
  { name: 'alt-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#karte?a=340038' },
  { name: 'all-1440', w: 1440, h: 900, url: '#karte?t=all&q=wolf%7Cw%C3%B6lf%7Cloup%7Clupo%7CHerdenschutz' },
  { name: 'brush-esc-1440', w: 1440, h: 900, url: '#karte?w=80-90', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))`] },
  { name: 'sync-live-1440', live: true, w: 1440, h: 900, url: '#karte?m=pult&tab=ok', pre: async () => { for (const id of [340652, 340520]) await fetch(LIVE + 'affairs/' + id + '/topics/adhoc%2Fdigitalisierung%3Ayes/confirm', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ by: 'Kollegin (DVS)', scheme: 'adhoc/digitalisierung' }) }); }, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'neu-limit-1440', live: true, w: 1440, h: 900, url: '#neu?limit=25', steps: [`(()=>{const f=document.querySelector('.nt-field textarea');f.value='Schule, Unterricht, Lehrpersonen und Bildung';f.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()`, 3000], print: `location.hash + ' | ' + document.querySelector('.runline').textContent` },
  { name: 'neu-cap-1440', live: true, w: 1440, h: 900, url: '#neu', steps: [`(()=>{const f=document.querySelector('.nt-field textarea');f.value='Schule, Unterricht, Lehrpersonen und Bildung';f.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()`, 4000] },
  { name: 'why-1440', w: 1440, h: 900, url: '#karte?a=96375', steps: [`document.querySelector('#v-karte .dg').scrollIntoView()`] },
  { name: 'quote-ctx-1440', w: 1440, h: 900, url: '#karte?a=340316', steps: [`(document.querySelector('#v-karte mark') || document.querySelector('#v-karte .dg')).scrollIntoView({ block: 'center' })`] },
  { name: 'readme-entscheid', w: 1440, h: 900, url: '#karte?a=334708', steps: [`(document.querySelector('#v-karte mark') || document.querySelector('#v-karte .dg')).scrollIntoView({ block: 'center' })`] },   // docs/img/entscheid.png: the Gate 1 demo affair
  // an APS-chapter affair: Digitalisierung «nein» is one collapsed line; [+] opens its graphic
  { name: 'why-collapse-1440', w: 1440, h: 900, url: '#karte?a=96375', steps: [`[...document.querySelectorAll('#v-karte .case dd button')].find(b=>b.textContent==='[+]').click()`, 300, `document.querySelector('#v-karte .case dd .dg').scrollIntoView({block:'center'})`], print: `document.querySelectorAll('#v-karte .case .dg').length + ' graphics · ' + __qs.karte.tp.id` },
  { name: 'why-bil-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#karte?a=40171', steps: [`document.querySelector('#v-karte .dg').scrollIntoView()`] },
  { name: 'why-dig-1440', w: 1440, h: 900, url: '#karte?a=340652', steps: [`document.querySelector('#v-karte .dg').scrollIntoView()`] },
  { name: 'similar-1440', w: 1440, h: 900, url: '#karte?a=340652', steps: [`document.querySelector('#v-karte .strip').scrollIntoView()`] },
  { name: 'matrix-1440', w: 1440, h: 900, url: '#karte?v=matrix' },
  { name: 'matrix-375', w: 375, h: 812, mobile: true, url: '#karte?v=matrix', full: true },
  { name: 'overview-375', w: 375, h: 812, mobile: true, url: '#karte', full: true },
  { name: 'simcal', w: 800, h: 600, url: '#karte', steps: [], print: `import('./js/case.js').then(m=>{const D=__qs.D,c=D.c;const out=[];const ids=[];for(let i=0;i<D.n&&ids.length<20;i+=1601){if(c.df[i]||c.ch[i]>=0)ids.push(i)}for(const i of ids){out.push('## '+c.title[i].slice(0,80));for(const [j,v,n,ss] of m.similar(i,null,true))out.push('   '+v+' '+n+(ss?' S':'  ')+' '+c.body[j]+' '+c.title[j].slice(0,80))}return out.join(String.fromCharCode(10))})` },
  { name: 'basel-1440', w: 1440, h: 900, url: '#karte?t=bs-themen' },
  { name: 'basel-detail-1440', w: 1440, h: 900, url: '#karte?t=bs-themen', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'basel-pult-1440', w: 1440, h: 900, url: '#karte?t=bs-themen&m=pult&tab=todo', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  // Ticino's own scheme (S29, lead department): the picker group, one department's map + timeline, an affair with the canton's label
  { name: 'ti-picker-1440', w: 1440, h: 900, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'t'}))`, `(()=>{const i=document.querySelector('.picker input');i.value='Tessin';i.dispatchEvent(new Event('input'))})()`],
    print: `[...document.querySelectorAll('.picker .lb li')].map(li=>li.textContent).join(' | ')` },
  { name: 'ti-scheme-1440', w: 1440, h: 900, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'t'}))`, `(()=>{const i=document.querySelector('.picker input');i.value='Tessin';i.dispatchEvent(new Event('input'));i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()`, 400,
    `(()=>{const s=document.querySelector('#v-karte .filters .fl.wide select');s.value='DT';s.dispatchEvent(new Event('change'))})()`], print: `__qs.karte.tp.id + ' | ' + __qs.karte.tsub.textContent` },
  { name: 'ti-scheme-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#karte?t=ti-dipartimenti', print: `__qs.karte.tsub.textContent` },
  { name: 'ti-affair-1440', w: 1440, h: 900, url: '#karte?t=ti-dipartimenti', steps: [`(()=>{const k=__qs.karte, c=__qs.D.c; const i=k.items.find(i=>c.ownGold[i]&&c.ownGold[i][0]!==c.own[i][1]&&c.own[i][2]===1); if(i!=null) k.select(c.id[i]);})()`],
    print: `[...document.querySelectorAll('#v-karte .case dl.facts')][0].textContent` },
  { name: 'saved-1440', w: 1440, h: 900, url: '#karte?t=adhoc%2Fwolf' },
  { name: 'anb-1440', w: 1440, h: 900, url: '#anb' },
  { name: 'anb-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#anb' },
  { name: 'anb-375', w: 375, h: 812, mobile: true, url: '#anb', full: true },
  { name: 'anb-live-1440', live: true, w: 1440, h: 900, url: '#anb' },
  { name: 'neu-replay-1440', w: 1440, h: 900, url: '#neu', steps: [`document.querySelector('.nt-play .box').click()`, 6000] },
  // #neu?limit=25 on the static site: the recording plays by itself, its first 25 decisions (≈ 20 s at ×4), then stops
  { name: 'neu-replay-limit-1440', w: 1440, h: 900, url: '#neu?limit=25', steps: [22000], print: `document.querySelector('#v-neu .runline').textContent` },
  { name: 'neu-replay-fr-1440', w: 1440, h: 900, lang: 'fr', url: '#neu', steps: [`document.querySelector('.nt-play .box').click()`, 6000] },
  { name: 'neu-replay-done-1440', w: 1440, h: 900, url: '#neu', steps: [`document.querySelector('.nt-play .box').click()`, 82000] },
  { name: 'neu-replay-375', w: 375, h: 812, mobile: true, url: '#neu', full: true, steps: [`document.querySelector('.nt-play .box').click()`, 6000] },
  { name: 'dark-1440', w: 1440, h: 900, url: '#karte', dark: true, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  // Gate 1 rehearsal (docs/DEMO.md): one page session against `make demo` (LIVE=http://127.0.0.1:<port>/), keys as on stage,
  // with the model endpoint blocked (QS_BASE_URL=http://10.255.255.1/v1): node app/dev/shoot.mjs - rehearsal
  { name: 'rehearsal-00-woche', live: true, w: 1440, h: 900, url: '#woche', steps: [`window.__wocheReady`, 1000] },
  { name: 'rehearsal-01-atlas', live: true, w: 1440, h: 900, url: '#ueber', steps: [`localStorage.clear()`, `localStorage.setItem('qs.who','Demo')`, 3000] },
  { name: 'rehearsal-02-digi', live: true, keep: true, w: 1440, h: 900, steps: [`[...document.querySelectorAll('.atl-cell')].find(b=>/^Digitalisierung/.test(b.getAttribute('aria-label'))).click()`, 800], print: `location.hash` },
  { name: 'rehearsal-03-affair', live: true, keep: true, w: 1440, h: 900, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'/'}))`, `(()=>{const q=__qs.karte.q;q.value='strebt digital';q.dispatchEvent(new Event('input'));q.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()`, 400, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, 1200], print: `__qs.karte.S.sel + ' | ' + location.hash` },
  { name: 'rehearsal-04-why', live: true, keep: true, w: 1440, h: 900, steps: [`(document.querySelector('#v-karte mark') || document.querySelector('#v-karte .dg')).scrollIntoView({ block: 'center' })`] },
  { name: 'rehearsal-05-decide', live: true, keep: true, w: 1440, h: 900, steps: [`window.__t1=performance.now()`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'1'}))`, 1000, `__qs.karte.st.scrollIntoView({ block: 'center' })`], print: `__qs.karte.S.sel + ' | ' + __qs.karte.st.textContent` },
  { name: 'rehearsal-06-neu-down', live: true, keep: true, w: 1440, h: 900, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'n'}))`, 600, `window.__t0=performance.now()`, `(()=>{const f=document.querySelector('.nt-field textarea');f.value='Wölfe, Grossraubtiere und Herdenschutz';f.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()`, 6000],
    print: `document.querySelector('#v-neu .runline').textContent + ' | offer shown: ' + !document.querySelector('#v-neu .runrow > button:last-child').hidden` },
  { name: 'rehearsal-07-neu-recording', live: true, keep: true, w: 1440, h: 900, steps: [`document.querySelector('#v-neu .runrow > button:last-child').click()`, 9000], print: `document.querySelector('#v-neu .nt-rec').textContent + ' | ' + document.querySelector('#v-neu .runline').textContent` },
  { name: 'rehearsal-08-pruef', live: true, keep: true, w: 1440, h: 900, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'b'}))`, 1200] },
  { name: 'rehearsal-09-anb', live: true, keep: true, w: 1440, h: 900, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'i'}))`, 1500] },
  { name: 'rehearsal-10-basel', live: true, keep: true, w: 1440, h: 900, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'m'}))`, `(()=>{const q=__qs.karte.q;q.value='';q.dispatchEvent(new Event('input'))})()`, 400, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'t'}))`, `(()=>{const i=document.querySelector('.picker input');i.value='Basel';i.dispatchEvent(new Event('input'));i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()`, 1200], print: `location.hash` },
  { name: 'rehearsal-11-affair-url', live: true, w: 1440, h: 900, url: '#karte?a=334708', steps: [1000], print: `__qs.karte.st.textContent` },
  { name: 'rehearsal-12-affair-fr', live: true, keep: true, w: 1440, h: 900, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'f'}))`, 800] },
  { name: 'rehearsal-13-rec-url', live: true, w: 1440, h: 900, url: '#neu?rec=1', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'d'}))`, 8000], print: `document.querySelector('#v-neu .nt-rec').textContent` },
  { name: 'rehearsal-15-finals-ticino', live: true, w: 1440, h: 900, url: '#karte?t=adhoc%2Fdigitalisierung', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'/'}))`, `(()=>{const q=__qs.karte.q;q.value='sovranit';q.dispatchEvent(new Event('input'));q.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()`, 400, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, 1000],
    print: `(()=>{const c=__qs.D.c,i=__qs.D.rowOf.get(__qs.karte.S.sel);return __qs.karte.S.sel+' '+c.body[i]+' '+c.title[i]})()` },
  // an endpoint that accepts connections and never answers (LIVE = a make demo whose QS_BASE_URL points at such a port)
  { name: 'neu-hang-1440', live: true, w: 1440, h: 900, url: '#neu', steps: [`(()=>{const f=document.querySelector('.nt-field textarea');f.value='Wölfe, Grossraubtiere und Herdenschutz';f.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()`, 23000],
    print: `document.querySelector('#v-neu .runline').textContent + ' | offer shown: ' + !document.querySelector('#v-neu .runrow > button:last-child').hidden` },
  { name: 'rehearsal-14-neu-back', live: true, keep: true, w: 1440, h: 900, steps: [`document.querySelector('#v-neu .nt-back').click()`, 600], print: `document.querySelector('#v-neu .nt-field textarea').readOnly + ' | ' + document.querySelector('#v-neu .runline').textContent` },
];

async function main() {
  mkdirSync(join(HERE, 'shots'), { recursive: true });
  const prof = mkdtempSync(join(tmpdir(), 'qs-chrome-'));
  const ch = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, '--no-first-run', '--hide-scrollbars', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
  let ver;
  for (let i = 0; i < 50; i++) { try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; } catch (e) { await sleep(200); } }
  if (!ver) throw new Error('chrome did not start');
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  let id = 0; const pend = new Map(), handlers = [];
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { const { res, rej } = pend.get(m.id); pend.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
    else for (const f of handlers) f(m);
  });
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId: S } = await send('Target.attachToTarget', { targetId, flatten: true });
  const errs = [];
  handlers.push(m => {
    if (m.sessionId !== S) return;
    if (m.method === 'Runtime.exceptionThrown') errs.push('EXC ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'warning')) errs.push(m.params.type + ' ' + m.params.args.map(a => a.value ?? a.description).join(' '));
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errs.push('LOG ' + m.params.entry.text + ' ' + (m.params.entry.url || ''));
  });
  await send('Runtime.enable', {}, S); await send('Log.enable', {}, S); await send('Page.enable', {}, S);
  const evalJs = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }, S); return r.result?.value; };
  for (const sc of SCEN) {
    if (ONLY && !sc.name.includes(ONLY)) continue;
    errs.length = 0;
    if (sc.pre) await sc.pre();
    await send('Emulation.setDeviceMetricsOverride', { width: sc.w, height: sc.h, deviceScaleFactor: sc.mobile ? 2 : 1, mobile: !!sc.mobile }, S);
    await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: sc.dark ? 'dark' : 'light' }] }, S);
    const t0 = Date.now();
    if (!sc.keep) { // keep: go on in the page the previous scenario left (a rehearsal walks one session)
      await send('Page.navigate', { url: 'about:blank' }, S); await sleep(100);
      await send('Page.navigate', { url: (sc.live ? LIVE : BASE) + '?lang=' + (sc.lang || 'de') + (sc.url || '') }, S);
      for (let i = 0; i < 100; i++) { if (await evalJs(`!!(window.__qs && !document.body.classList.contains('loading'))`)) break; await sleep(100); }
    }
    const ready = Date.now() - t0;
    await sleep(500);
    for (const st of sc.steps || []) { if (typeof st === 'number') await sleep(st); else { await evalJs(st); await sleep(350); } }
    await sleep(600);
    const info = await evalJs(`JSON.stringify({sw:document.documentElement.scrollWidth, cw:document.documentElement.clientWidth, h:document.documentElement.scrollHeight, wide:[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth+1).slice(0,4).map(e=>e.tagName+'.'+e.className+' '+Math.round(e.getBoundingClientRect().right))})`);
    const params = { format: 'png' };
    if (sc.full) { const m = JSON.parse(info); params.clip = { x: 0, y: 0, width: sc.w, height: Math.min(m.h, 6000), scale: 1 }; params.captureBeyondViewport = true; }
    const shot = await send('Page.captureScreenshot', params, S);
    writeFileSync(join(HERE, 'shots', `${sc.name}.png`), Buffer.from(shot.data, 'base64'));
    if (sc.print) console.log(await evalJs(sc.print));
    console.log(`${sc.name}: ready ${ready} ms ${info}${errs.length ? '\n  ' + errs.join('\n  ') : ''}`);
  }
  ws.close(); ch.kill('SIGTERM');
}
main().catch(e => { console.error(e); process.exit(1); });
