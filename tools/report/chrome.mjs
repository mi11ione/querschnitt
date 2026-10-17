// Headless Chrome over the DevTools protocol, no npm deps (same approach as app/dev/shoot.mjs).
//   node tools/report/chrome.mjs pdf  <page.html> <out.pdf>
//        prints the page with its own @page CSS (A4, margins, page numbers); waits for the web fonts and images first
//   node tools/report/chrome.mjs shot <url> <out.png> [--size 1440x900] [--clip x,y,w,h] [--scale 2]
//        screenshot (used for docs/img/pruefstand.png: the Prüfstand lane chart, served app, deviceScaleFactor 2)
// CHROME=/path/to/chrome to override the macOS default.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333 + Math.floor(Math.random() * 500);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const [cmd, src, out, ...rest] = process.argv.slice(2);
const opt = k => { const i = rest.indexOf('--' + k); return i >= 0 ? rest[i + 1] : null; };
if (!['pdf', 'shot'].includes(cmd) || !src || !out) {
  console.error('usage: chrome.mjs pdf <page.html> <out.pdf> | shot <url> <out.png> [--size WxH] [--clip x,y,w,h] [--scale n]');
  process.exit(2);
}
if (!existsSync(CHROME)) { console.error(`no Chrome at ${CHROME} (set CHROME=...)`); process.exit(2); }

async function main() {
  const prof = mkdtempSync(join(tmpdir(), 'qs-report-'));
  const ch = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, '--no-first-run',
    '--hide-scrollbars', '--disable-gpu', '--allow-file-access-from-files', 'about:blank'], { stdio: 'ignore' });
  try {
    let ver;
    for (let i = 0; i < 50; i++) { try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; } catch { await sleep(200); } }
    if (!ver) throw new Error('chrome did not start');
    const ws = new WebSocket(ver.webSocketDebuggerUrl);
    await new Promise(r => ws.addEventListener('open', r, { once: true }));
    let id = 0; const pend = new Map(); const errs = [];
    ws.addEventListener('message', ev => {
      const m = JSON.parse(ev.data);
      if (m.id && pend.has(m.id)) { const { res, rej } = pend.get(m.id); pend.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
      else if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errs.push(m.params.entry.text + ' ' + (m.params.entry.url || ''));
      else if (m.method === 'Runtime.exceptionThrown') errs.push(m.params.exceptionDetails.text);
    });
    const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const i = ++id; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
    const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
    const { sessionId: S } = await send('Target.attachToTarget', { targetId, flatten: true });
    await send('Page.enable', {}, S); await send('Runtime.enable', {}, S); await send('Log.enable', {}, S);
    const evalJs = async e => (await send('Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true }, S)).result?.value;

    if (cmd === 'pdf') {
      await send('Emulation.setEmulatedMedia', { media: 'print' }, S);
      await send('Page.navigate', { url: pathToFileURL(resolve(src)).href }, S);
      for (let i = 0; i < 100 && !(await evalJs(`document.readyState === 'complete'`)); i++) await sleep(100);
      // every face actually used must be loaded, every image decoded, before printing
      const ready = await evalJs(`(async () => { await document.fonts.ready;
        await Promise.all([...document.images].map(i => i.decode().catch(() => 'bad ' + i.src)));
        const bad = [...document.images].filter(i => !i.naturalWidth).map(i => i.getAttribute('src'));
        const faces = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight);
        return { bad, faces }; })()`);
      if (ready.bad.length) throw new Error('images did not load: ' + ready.bad.join(', '));
      if (!ready.faces.some(f => f.includes('Public Sans')) || !ready.faces.some(f => f.includes('Fragment Mono')))
        throw new Error('web fonts not loaded: ' + JSON.stringify(ready.faces));
      const r = await send('Page.printToPDF', { preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false,
        generateTaggedPDF: true, generateDocumentOutline: true }, S);
      writeFileSync(out, Buffer.from(r.data, 'base64'));
    } else {
      const [w, h] = (opt('size') || '1440x900').split('x').map(Number);
      const scale = Number(opt('scale') || 2);
      await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: scale, mobile: false }, S);
      await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }] }, S);
      await send('Page.navigate', { url: src }, S);
      for (let i = 0; i < 100; i++) { if (await evalJs(`document.readyState === 'complete' && !(document.body && document.body.classList.contains('loading'))`)) break; await sleep(100); }
      await sleep(Number(opt('wait') || 1500));   // --wait ms: the app fetches its data after load
      const p = { format: 'png' };
      const c = opt('clip');
      if (c) { const [x, y, cw, chh] = c.split(',').map(Number); p.clip = { x, y, width: cw, height: chh, scale: 1 }; }
      const shot = await send('Page.captureScreenshot', p, S);
      writeFileSync(out, Buffer.from(shot.data, 'base64'));
    }
    if (errs.length) console.error('page errors:\n  ' + errs.join('\n  '));
    ws.close();
  } finally {
    ch.kill('SIGTERM');
    await sleep(300);
    try { rmSync(prof, { recursive: true, force: true }); } catch {}
  }
  console.log(out);
}
main().catch(e => { console.error(e.message || e); process.exit(1); });
