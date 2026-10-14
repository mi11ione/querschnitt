// Headless check: opens the app in Chrome over the DevTools protocol (no npm deps), runs scripted steps, prints console
// errors and writes screenshots to app/dev/shots/. Usage: node app/dev/shoot.mjs [base-url] [only-name]
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = process.argv[2] || 'http://127.0.0.1:8765/';
const LIVE = process.env.LIVE || 'http://127.0.0.1:8766/';
const ONLY = process.argv[3] || null;
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333 + Math.floor(Math.random() * 500);
const sleep = ms => new Promise(r => setTimeout(r, ms));

const SCEN = [
  { name: 'karte-1440', w: 1440, h: 900, url: '#karte' },
  { name: 'karte-detail-1440', w: 1440, h: 900, url: '#karte', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'karte-search-1440', w: 1440, h: 900, url: '#karte', steps: [`(()=>{const q=document.querySelector('#v-karte .filters input');q.value='rechenzentr|data cent|centre de donn|centri dati|datacenter';q.dispatchEvent(new Event('input'))})()`, 400, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'pult-1440', w: 1440, h: 900, url: '#karte?m=pult&tab=todo', steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'karte-fr-1440', w: 1440, h: 900, url: '#karte', steps: [`localStorage.clear()`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'f'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`, `document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
  { name: 'karte-1100', w: 1100, h: 800, url: '#karte' },
  { name: 'neu-1440', w: 1440, h: 900, url: '#neu' },
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
  { name: 'neu-cap-1440', live: true, w: 1440, h: 900, url: '#neu', steps: [`(()=>{const f=document.querySelector('.nt-field textarea');f.value='Schule, Unterricht, Lehrpersonen und Bildung';f.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))})()`, 4000] },
  { name: 'dark-1440', w: 1440, h: 900, url: '#karte', dark: true, steps: [`document.dispatchEvent(new KeyboardEvent('keydown',{key:'j'}))`] },
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
    await send('Page.navigate', { url: 'about:blank' }, S); await sleep(100);
    const t0 = Date.now();
    await send('Page.navigate', { url: (sc.live ? LIVE : BASE) + '?lang=' + (sc.lang || 'de') + (sc.url || '') }, S);
    for (let i = 0; i < 100; i++) { if (await evalJs(`!!(window.__qs && !document.body.classList.contains('loading'))`)) break; await sleep(100); }
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
