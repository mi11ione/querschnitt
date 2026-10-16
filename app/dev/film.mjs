// The backup demo video (docs/DEMO.md «Backup video»): plays the storyboard below on the live site in headless Chrome over
// the DevTools protocol (no npm deps) and encodes dist/querschnitt-demo.mp4 with ffmpeg. Deterministic: the page runs on
// virtual time and every video frame is one 1/30 s step of it followed by a screenshot, so the take does not depend on
// how fast this machine or the network is (a fetch holds virtual time until it lands; waiting is never filmed). Motion is
// scripted per frame: eased scrolling of the view's scroll box, a drawn cursor that glides between targets, real mouse
// clicks at its tip; captions are a lower-third in the app's register (black on white, hairline, Public Sans).
// Rendered at 1440×810 CSS px × scale 2 (the app's 1440 px layout) and downscaled to 1920×1080.
//   node app/dev/film.mjs [--base URL] [--out dist/querschnitt-demo.mp4] [--scale 2] [--view 1440x810]
//        [--frames DIR --every N]   preview: every Nth frame as PNG into DIR, no video
//        [--from BEAT] [--until S]   preview: screenshots only from that beat on / stop after S s of video
// CHROME=..., FFMPEG=... (default /opt/homebrew/bin/ffmpeg, else ffmpeg on PATH).
import { spawn, spawnSync } from 'node:child_process';
import { writeFileSync, mkdirSync, mkdtempSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 && process.argv[i + 1] != null ? process.argv[i + 1] : d; };
const BASE = arg('base', 'https://querschnitt.mi11ion.io/');
const OUT = resolve(ROOT, arg('out', 'dist/querschnitt-demo.mp4'));
const SCALE = +arg('scale', 2);
const [VW, VH] = arg('view', '1440x810').split('x').map(Number);
const PREVIEW = arg('frames', null), EVERY = +arg('every', 15), FROM = arg('from', null), UNTIL = +arg('until', 0);
const FPS = 30, DT = 1000 / FPS, OW = 1920, OH = 1080;
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const FFMPEG = process.env.FFMPEG || (existsSync('/opt/homebrew/bin/ffmpeg') ? '/opt/homebrew/bin/ffmpeg' : 'ffmpeg');
const FFPROBE = FFMPEG.replace(/ffmpeg$/, 'ffprobe');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2); // easeInOutCubic
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// ------------------------------------------------------------------------------------------------ storyboard
// Captions: English, at most 8 words, numbers only from docs/PITCH.md (eval/claims.tsv). Times are video seconds.
const CAP = {
  woche: 'Last week in Swiss parliaments, by topic',
  quotes: langs => `Quoted sentences in ${langs}`,
  why: 'Why this topic, in one plain sentence',
  quote: 'The sentence in the affair that supports it',
  tick: 'Red tick: unsure, so a person checks',
  atlas: 'One map per topic, same scale',
  digi: 'Digitalisierung across every parliament',
  judge: 'AI judge: flags 0.905 right, keywords 0.756',
  heldout: '927 unseen federal affairs: 0.696 match the editors',
  lane: 'Two thirds pass unchecked, right in 0.812',
  neu: 'A new topic from one sentence: recorded run',
  anb: 'The topics table and loader for OpenParlData',
  cost: 'On Apertus: USD 0.333 per 1,000 affairs',
  repo: 'github.com/mi11ione/querschnitt',
};

async function story(f) {
  const { beat, hold, cap, glide, click, scroll, settle, js } = f;
  // (a) Neueste Woche: the sentence, then two topic rows with their quoted examples
  await beat('woche');
  await settle(`!document.querySelector('#v-woche .wo-wait') && document.querySelectorAll('#v-woche .wo-a').length > 2`, 'woche examples');
  f.cursorAt(VW * 0.62, VH * 0.62);
  cap(CAP.woche); await hold(5.0);
  // the pair of ranked rows (among the first five) that shows the most languages; Italian first
  const plan = await js(`(() => {
    const box = document.querySelector('#v-woche'), rows = [...box.querySelectorAll('ol.wo-list > .wo-row')].slice(0, 5);
    const lg = r => new Set([...r.querySelectorAll('.wo-a')].map(a => (a.querySelector('.lg') || {}).textContent || 'de'));
    let best = 0, bs = -1;
    for (let i = 0; i + 1 < rows.length; i++) { const u = new Set([...lg(rows[i]), ...lg(rows[i + 1])]); const s = u.size * 2 + (u.has('it') ? 3 : 0) - i * 0.1; if (s > bs) { bs = s; best = i; } }
    const off = r => box.scrollTop + r.getBoundingClientRect().top - box.getBoundingClientRect().top - 12;
    const u = new Set([...lg(rows[best]), ...lg(rows[best + 1] || rows[best])]);
    return { a: off(rows[best]), b: off(rows[best + 1] || rows[best]), langs: ['de', 'fr', 'it'].filter(l => u.has(l)), max: box.scrollHeight - box.clientHeight };
  })()`);
  const names = { de: 'German', fr: 'French', it: 'Italian' };
  await scroll('#v-woche', Math.min(plan.a, plan.max), 2.4);
  cap(CAP.quotes(plan.langs.map(l => names[l]).join(', ').replace(/, ([^,]*)$/, ' and $1'))); await hold(4.0);
  await scroll('#v-woche', Math.min(plan.b, plan.max), 2.0);
  await hold(1.0);
  // a red tick in view: point at it (its hover tip says what it means)
  const tick = await js(`(() => { const box = document.querySelector('#v-woche').getBoundingClientRect();
    const t = [...document.querySelectorAll('#v-woche ol.wo-list .wo-a .rtick')].find(e => { const r = e.getBoundingClientRect(); return r.top > box.top + 40 && r.bottom < box.bottom - 120; });
    if (t) t.dataset.film = 'tick'; return !!t; })()`);
  if (tick) { await glide('[data-film=tick]', { dx: 0.5, dy: 0.6, hover: true }); cap(CAP.tick); await hold(3.5); }
  else await hold(2.0);
  // open one example: in view, the model sure (no red tick), a quoted sentence, German first
  const pick = `(async () => { const box = document.querySelector('#v-woche').getBoundingClientRect();
    const ok = [...document.querySelectorAll('#v-woche ol.wo-list .wo-a')].filter(a => { const r = a.getBoundingClientRect(); return r.top > box.top + 8 && r.bottom < box.bottom - 8 && !a.querySelector('.rtick') && !a.querySelector('.q.dim'); });
    const whole = a => !/^«?…|…»?$/.test(a.querySelector('.q').textContent.trim());
    // the stored quote is what the case view marks: skip affairs whose quote is letterhead (letter-spaced words, ref numbers)
    const junk = q => /(?:\\b\\p{L} ){4,}|\\b\\d+\\/\\d{4}\\b/u.test(q || '');
    const clean = async a => { const id = +a.dataset.id; if (!id) return true;
      const d = await (await fetch('data/detail/' + Math.floor(id / 1000) + '.json')).json(); const x = d[id] || {};
      const ev = (x.aps && x.aps.evidence) || (x.dig && x.dig.evidence); return !junk(ev && ev.quote); };
    const pref = [...ok.filter(a => !a.querySelector('.lg') && whole(a)), ...ok.filter(a => !a.querySelector('.lg')), ...ok];
    let a = null; for (const c of pref) if (await clean(c)) { a = c; break; }
    a = a || ok[0]; if (!a) return null; a.dataset.film = 'pick'; return a.querySelector('.t').textContent; })()`;
  const title = await js(pick);
  if (!title) throw new Error('no example to open on the Woche view');
  console.log(`  opens «${title}»`);
  await glide(`[data-film=pick] .t`, { dx: 0.35, dy: 0.5 });
  await hold(0.6);
  // (b) the affair: the plain why-sentence, then the quote
  await beat('affair');
  await click(`[data-film=pick] .t`, `location.hash.startsWith('#karte') && __qs.karte.S.sel != null && document.querySelector('#v-karte .case .dgs')`, 'affair case');
  await hold(0.8);
  await glide(`#v-karte .case .dgs`, { dx: 0, dy: 0.5, px: -18, py: 2 });
  cap(CAP.why); await hold(4.5);
  if (await js(`!!document.querySelector('#v-karte .case .scroll mark')`)) {
    const y = await js(`(() => { const s = document.querySelector('#v-karte .case .scroll'), m = s.querySelector('mark'), sr = s.getBoundingClientRect();
      return Math.min(s.scrollHeight - s.clientHeight, s.scrollTop + m.getBoundingClientRect().top - sr.top - sr.height * 0.3); })()`);
    await scroll('#v-karte .case .scroll', y, 1.8);
    await glide(`#v-karte .case .scroll mark`, { dx: 0, dy: 0, px: -18, py: 10, hover: false });
    cap(CAP.quote); await hold(4.5);
  }
  // (c) Überblick → Digitalisierung, the map
  await beat('atlas');
  cap(null);
  await click('#t-ueber', `!document.querySelector('#v-ueber').hidden && document.querySelectorAll('#v-ueber .atl-cell').length > 10`, 'atlas');
  cap(CAP.atlas); await hold(4.5);
  await beat('digi');
  const digi = `[...document.querySelectorAll('#v-ueber .atl-cell')].find(b => /^Digitalisierung/.test(b.getAttribute('aria-label')))`;
  await js(`${digi}.dataset.film = 'digi'`);
  await click('[data-film=digi]', `!document.querySelector('#v-karte').hidden && __qs.karte.tp.id === 'adhoc/digitalisierung' && document.querySelector('#v-karte .map svg path')`, 'Digitalisierung map', { dx: 0.5, dy: 0.45 });
  cap(CAP.digi); await hold(0.8);
  await glide(`#v-karte .map svg`, { dx: 0.5, dy: 0.62, hover: false });
  await hold(3.5);
  cap(CAP.judge); await hold(5.5);
  // (d) Prüfstand: the lead block, the held-out result and the lane
  await beat('pruef');
  cap(null);
  await click('#t-pruef', `!document.querySelector('#v-pruef').hidden && document.querySelectorAll('#v-pruef .pl-l > li').length >= 2`, 'Prüfstand');
  await glide(`#v-pruef .pl-l > li:nth-child(1) .pl-t`, { dx: 0, dy: 0.5, px: -18, py: 14 });
  cap(CAP.heldout); await hold(6.0);
  await glide(`#v-pruef .pl-l > li:nth-child(2) .pl-t`, { dx: 0, dy: 0.5, px: -18, py: 14 });
  cap(CAP.lane); await hold(5.5);
  // (e) Neues Thema: on the static site the tab plays the recorded real run, labelled as one
  await beat('neu');
  cap(null);
  await click('#t-neu', `!document.querySelector('#v-neu').hidden && document.querySelector('#v-neu .nt-rec') && !document.querySelector('#v-neu .nt-rec').hidden`, 'Neues Thema recording');
  await hold(0.6);
  await glide(`#v-neu .nt-rec`, { dx: 0.5, dy: 1, py: 8 });
  cap(CAP.neu); await hold(6.0);
  await glide(`#v-neu .runline`, { dx: 0.3, dy: 0.5, py: 10 });
  await hold(4.0);
  await glide(`#v-neu .nt-feed:not([hidden]), #v-neu .runline`, { dx: 0.6, dy: 0.3, hover: false });
  await hold(8.0);
  // (f) Anbindung: the topics table, the Hop loader, /changes, last night
  await beat('anb');
  cap(null);
  await click('#t-anb', `!document.querySelector('#v-anb').hidden && document.querySelector('#v-anb .anb .anb-cols')`, 'Anbindung');
  cap(CAP.anb); await hold(4.5);
  // last night's run (its line carries the cost): scrolled into the upper half if needed, the cursor beside its first line
  const ny = await js(`(() => { const box = document.querySelector('#v-anb'), b = box.getBoundingClientRect();
    const h = [...box.querySelectorAll('h2')].find(e => /^(letzte Nacht|la nuit dernière)/i.test(e.textContent.trim()));
    if (!h) return null; const p = h.nextElementSibling || h; p.dataset.film = 'night';
    const top = p.getBoundingClientRect().top - b.top;
    return top > 40 && top < b.height * 0.6 ? -1 : Math.max(0, Math.min(box.scrollHeight - box.clientHeight, box.scrollTop + top - b.height * 0.3)); })()`);
  if (ny != null) {
    if (ny >= 0) await scroll('#v-anb', ny, 2.0);
    await glide('[data-film=night]', { dx: 0, dy: 0.5, px: -18, py: 2, hover: false });
  }
  cap(CAP.cost); await hold(4.5);
  await beat('end');
  // the rest of the page passes by under the repo address: /changes, the footprint
  cap(CAP.repo);
  const ey = await js(`(() => { const s = document.querySelector('#v-anb'); return Math.min(s.scrollHeight - s.clientHeight, s.scrollTop + 300); })()`);
  if (ey > (await js(`document.querySelector('#v-anb').scrollTop`)) + 20) await scroll('#v-anb', ey, 3.0);
  await hold(3.5);
  await f.fadeOut(0.8);
}

// ------------------------------------------------------------------------------------------------ the page overlay
// cursor (an arrow, black with a white edge), the caption bar and a white fade; pointer-events off, above everything
const OVERLAY = `(() => {
  if (window.__film) return;
  const d = document.createElement('div'); d.id = '__film';
  d.innerHTML = '<svg id="__fc" width="20" height="26" viewBox="0 0 20 26" style="position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform-origin:2px 2px;will-change:transform;overflow:visible">'
    + '<path d="M2 2 L2 20.5 L6.6 16.3 L9.6 23.2 L12.6 21.9 L9.7 15.1 L15.9 15.1 Z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>'
    + '<div id="__fband" style="position:fixed;left:0;right:0;bottom:0;z-index:2147483646;pointer-events:none;background:#fff;border-top:1px solid #111;opacity:0;will-change:opacity;'
    + 'display:flex;align-items:center;padding:0 24px;box-sizing:border-box"><span id="__fcap" style="will-change:opacity;color:#111;font:500 15px/1.3 \\'Public Sans\\',Arial,sans-serif;letter-spacing:0;white-space:nowrap"></span></div>'
    + '<div id="__ffade" style="position:fixed;inset:0;z-index:2147483647;pointer-events:none;background:#fff;opacity:0;will-change:opacity"></div>';
  document.documentElement.append(d);
  const c = d.querySelector('#__fc'), band = d.querySelector('#__fband'), cap = d.querySelector('#__fcap'), fade = d.querySelector('#__ffade');
  // the band covers the app's footer (provenance and keys) while a caption shows
  const ft = document.querySelector('footer'); band.style.height = (ft ? Math.ceil(innerHeight - ft.getBoundingClientRect().top) : 56) + 'px';
  if (innerWidth > 1600) band.style.paddingLeft = band.style.paddingRight = Math.max(24, (innerWidth - 1680) / 2 + 24) + 'px';
  window.__film = {
    set(s) {
      c.style.transform = 'translate(' + (s.x - 2) + 'px,' + (s.y - 2) + 'px) scale(' + s.k + ')';
      if (cap.textContent !== s.t) cap.textContent = s.t;
      cap.style.opacity = s.t ? s.o : 0; band.style.opacity = s.t ? s.b : 0;
      fade.style.opacity = s.f;
      if (s.sc) { const el = document.querySelector(s.sc[0]); if (el) el.scrollTop = s.sc[1]; }
    } };
})()`;

// ------------------------------------------------------------------------------------------------ Chrome
async function main() {
  const t00 = Date.now();
  const prof = mkdtempSync(join(tmpdir(), 'qs-film-'));
  const PORT = 9333 + Math.floor(Math.random() * 500);
  // the scale is the browser's (--force-device-scale-factor): an emulated deviceScaleFactor stalls screenshots on paused virtual time
  const ch = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, '--no-first-run', '--hide-scrollbars',
    `--force-device-scale-factor=${SCALE}`, `--window-size=${VW},${VH}`, '--mute-audio', '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--disable-extensions', 'about:blank'], { stdio: 'ignore' });
  let ver;
  for (let i = 0; i < 50; i++) { try { ver = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); break; } catch (e) { await sleep(200); } }
  if (!ver) throw new Error('chrome did not start (CHROME=...)');
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  let id = 0; const pend = new Map(), handlers = [];
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { const { res, rej } = pend.get(m.id); pend.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); }
    else for (const fn of handlers) fn(m);
  });
  // every call has a watchdog: a stalled renderer fails the take with the call's name instead of hanging
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
    const i = ++id, to = setTimeout(() => { if (pend.has(i)) { pend.delete(i); rej(new Error(`${method} got no answer in 90 s`)); } }, 90000);
    pend.set(i, { res: v => { clearTimeout(to); res(v); }, rej: e => { clearTimeout(to); rej(e); } });
    ws.send(JSON.stringify({ id: i, method, params, sessionId }));
  });
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId: S } = await send('Target.attachToTarget', { targetId, flatten: true });
  const s = (m, p) => send(m, p, S);
  const errs = [], inflight = new Set();
  let expired = null;
  handlers.push(m => {
    if (m.sessionId !== S) return;
    if (m.method === 'Network.requestWillBeSent' && !/^data:/.test(m.params.request.url)) inflight.add(m.params.requestId);
    if (m.method === 'Network.loadingFinished' || m.method === 'Network.loadingFailed') inflight.delete(m.params.requestId);
    if (m.method === 'Network.loadingFailed' && !m.params.canceled) errs.push(`net ${m.params.errorText} ${m.params.type}`);
    if (m.method === 'Runtime.exceptionThrown') errs.push('EXC ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    if (m.method === 'Emulation.virtualTimeBudgetExpired' && expired) { const f = expired; expired = null; f(); }
  });
  const js = async expr => {
    const r = await s('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(`page: ${expr.slice(0, 90)}… ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
    return r.result?.value;
  };
  await s('Runtime.enable'); await s('Page.enable'); await s('Network.enable');
  await s('Network.setCacheDisabled', { cacheDisabled: false });
  await s('Emulation.setDeviceMetricsOverride', { width: VW, height: VH, deviceScaleFactor: 0, mobile: false });
  // reduced motion: the app then drops its CSS transitions (bar growth), which can stall a screenshot on paused virtual time;
  // all motion in the take is the script's own, per frame
  await s('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'light' }, { name: 'prefers-reduced-motion', value: 'reduce' }] });

  // load in real time, then wait for real readiness: the app booted, the Woche examples filled, fonts in, network quiet
  const url = `${BASE}${BASE.includes('?') ? '&' : '?'}lang=de#woche`;
  console.log(`film: ${url} at ${VW}×${VH} × ${SCALE} → ${OW}×${OH} @ ${FPS} fps`);
  await s('Page.navigate', { url });
  const realWait = async (cond, what, ms = 60000) => {
    const t0 = Date.now(); let quiet = 0;
    while (Date.now() - t0 < ms) {
      const ok = await js(`(() => { try { return !!(${cond}); } catch (e) { return false; } })()`).catch(() => false);
      quiet = ok && inflight.size === 0 ? quiet + 1 : 0;
      if (quiet >= 5) return;
      await sleep(100);
    }
    throw new Error(`not ready after ${ms / 1000} s: ${what}`);
  };
  await realWait(`window.__qs && !document.body.classList.contains('loading') && window.__wocheReady`, 'app boot');
  await js(`window.__wocheReady.then(() => document.fonts.ready).then(() => 1)`);
  await realWait(`document.fonts.status === 'loaded' && !document.querySelector('#v-woche .wo-wait')`, 'Woche examples');
  await js(OVERLAY);
  await js(`document.fonts.load('500 15px "Public Sans"').then(() => 1)`);

  // from here on the page runs on virtual time: one step = one frame
  await s('Emulation.setVirtualTimePolicy', { policy: 'pause' });
  const vstep = (dt = DT) => new Promise((res, rej) => {
    expired = res;
    s('Emulation.setVirtualTimePolicy', { policy: 'pauseIfNetworkFetchesPending', budget: dt }).catch(rej);
    setTimeout(() => { if (expired === res) rej(new Error('virtual time stalled for 60 s (a fetch that never ends?)')); }, 60000);
  });

  // the encoder (or the preview folder)
  let ff = null, ffErr = '';
  if (PREVIEW) { rmSync(PREVIEW, { recursive: true, force: true }); mkdirSync(PREVIEW, { recursive: true }); }
  else {
    mkdirSync(dirname(OUT), { recursive: true });
    const scale = VW * SCALE === OW && VH * SCALE === OH ? '' : `scale=${OW}:${OH}:flags=lanczos+accurate_rnd+full_chroma_int:out_color_matrix=bt709:out_range=tv,`;
    ff = spawn(FFMPEG, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-vf', `${scale}format=yuv420p`, '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS),
      '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', '-movflags', '+faststart', OUT],
      { stdio: ['pipe', 'ignore', 'pipe'] });
    ff.stderr.on('data', d => { ffErr += d; });
  }
  const ffDone = ff ? new Promise(r => ff.on('close', r)) : null;
  let ffBroken = null; if (ff) ff.stdin.on('error', e => { ffBroken = e; });
  const put = buf => new Promise((res, rej) => { if (ffBroken) return rej(new Error(`ffmpeg: ${ffBroken.message} ${ffErr}`)); if (ff.stdin.write(buf)) res(); else ff.stdin.once('drain', res); });

  // ---------------------------------------------------------------------------------------------- frame state
  const stalls = []; let F = 0, cx = VW / 2, cy = VH / 2, press = 0, fade = 0, fadeIn = false, filming = !FROM, curBeat = '';
  const caps = []; // {t, f0, f1, cin, cout}: cin/cout = the band stays while one caption hands over to the next
  const beats = [];
  const capNow = () => {
    for (const c of caps) if (F >= c.f0 && F < c.f1) {
      const i = Math.min(1, (F - c.f0 + 1) / 9), o = Math.min(1, (c.f1 - F) / 7);
      return [c.t, Math.min(i, o), Math.min(c.cin ? 1 : i, c.cout ? 1 : o)];
    }
    return ['', 0, 0];
  };
  const frame = async (scrollTo) => {
    const [t, o, b] = capNow();
    const k = press > 0 ? 0.86 : 1;
    await js(`__film.set(${JSON.stringify({ x: +cx.toFixed(2), y: +cy.toFixed(2), k, t, o: +o.toFixed(3), b: +b.toFixed(3), f: +fade.toFixed(3), sc: scrollTo || null })})`);
    await vstep();
    if (filming && (!PREVIEW || F % EVERY === 0)) {
      // now and then (after a mouse event) a screenshot waits for a frame that paused virtual time never schedules:
      // let the clock run for a moment (20 ms and up, real time), then pause it again
      const shot = s('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true, captureBeyondViewport: false });
      let r = null, nudges = 0;
      while (!r) {
        r = await Promise.race([shot, sleep(4000).then(() => null)]);
        if (!r) {
          if (++nudges > 5) throw new Error(`screenshot stalled at frame ${F}`);
          stalls.push(F); await s('Emulation.setVirtualTimePolicy', { policy: 'advance' }); await sleep(20 * nudges);
          await s('Emulation.setVirtualTimePolicy', { policy: 'pause' });
        }
      }
      const buf = Buffer.from(r.data, 'base64');
      if (PREVIEW) writeFileSync(join(PREVIEW, `${String(F).padStart(5, '0')}-${curBeat}.png`), buf);
      else await put(buf);
    }
    if (press > 0) press--;
    if (fadeIn && fade > 0) fade = Math.max(0, fade - 1 / 10); // in from white over the first 10 frames
    F++;
    if (UNTIL && F >= UNTIL * FPS) throw new Error('UNTIL');
    if (F % 150 === 0) process.stdout.write(`  ${(F / FPS).toFixed(0)} s (${((Date.now() - t00) / 1000).toFixed(0)} s real)\n`);
  };
  const rectOf = async (sel) => {
    const r = await js(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; })()`);
    if (!r) throw new Error(`no element ${sel}`);
    return r;
  };
  const target = async (sel, o = {}) => {
    const r = await rectOf(sel);
    return [clamp(r.x + r.w * (o.dx ?? 0.5) + (o.px || 0), 4, VW - 20), clamp(r.y + r.h * (o.dy ?? 0.5) + (o.py || 0), 4, VH - 26)];
  };
  const mouse = (type, x, y, extra = {}) => s('Input.dispatchMouseEvent', { type, x, y, button: type === 'mouseMoved' ? 'none' : 'left', buttons: type === 'mousePressed' ? 1 : 0, clickCount: type === 'mouseMoved' ? 0 : 1, ...extra });

  const f = {
    cursorAt(x, y) { cx = x; cy = y; },
    async beat(name) {
      curBeat = name; beats.push({ name, t: +(F / FPS).toFixed(2) });
      if (FROM && name === FROM) filming = true;
      console.log(`  ${(F / FPS).toFixed(1).padStart(6)} s  ${name}`);
    },
    async hold(sec) { for (let n = Math.round(sec * FPS); n > 0; n--) await frame(); },
    cap(text) {
      const cur = caps.find(c => c.f1 === Infinity);
      let f0 = F;
      if (cur) { cur.f1 = F + 7; f0 = F + 7; cur.cout = !!text; }
      if (text) caps.push({ t: text, f0, f1: Infinity, cin: !!cur });
    },
    // the cursor glides along a slight arc; the duration grows with the distance
    async glide(sel, o = {}) {
      const [x1, y1] = await target(sel, o), x0 = cx, y0 = cy, d = Math.hypot(x1 - x0, y1 - y0);
      if (d < 2) return;
      const n = Math.round(clamp(0.45 + d / 1500, 0.55, 1.2) * FPS), bow = Math.min(40, d * 0.06);
      const nx = -(y1 - y0) / d, ny = (x1 - x0) / d;
      for (let i = 1; i <= n; i++) {
        const e = ease(i / n), b = Math.sin(Math.PI * e) * bow;
        cx = x0 + (x1 - x0) * e + nx * b; cy = y0 + (y1 - y0) * e + ny * b;
        await frame();
      }
      if (o.hover !== false) await mouse('mouseMoved', cx, cy);
    },
    // glide, press (the cursor dips for 4 frames), a real click at the tip, then wait — unfilmed — until the page is ready
    async click(sel, ready, what, o = {}) {
      await f.glide(sel, o);
      await f.hold(0.25);
      press = 4; await frame();
      await mouse('mousePressed', cx, cy); await mouse('mouseReleased', cx, cy);
      await f.settle(ready, what);
    },
    async settle(cond, what, ms = 45000) {
      const t0 = Date.now(); let ok = 0;
      while (Date.now() - t0 < ms) {
        const c = await js(`(() => { try { return !!(${cond}) && document.fonts.status === 'loaded'; } catch (e) { return false; } })()`);
        ok = c && inflight.size === 0 ? ok + 1 : 0;
        if (ok >= 2) return;
        await vstep();
      }
      throw new Error(`not ready after ${ms / 1000} s: ${what}`);
    },
    // eased scroll of a scroll box to y, per frame
    async scroll(sel, y, sec) {
      const y0 = await js(`document.querySelector(${JSON.stringify(sel)}).scrollTop`), n = Math.round(sec * FPS);
      for (let i = 1; i <= n; i++) await frame([sel, y0 + (y - y0) * ease(i / n)]);
    },
    async fadeOut(sec) { fadeIn = false; const n = Math.round(sec * FPS); for (let i = 1; i <= n; i++) { fade = i / n; await frame(); } },
    js, rect: rectOf,
  };
  let stopped = false;
  try { await story(f); }
  catch (e) { if (e.message !== 'UNTIL') throw e; stopped = true; }
  if (stalls.length) console.log(`screenshot stalls released by letting the clock run briefly, at frame(s) ${[...new Set(stalls)].join(', ')}`);
  if (errs.length) console.log(`page errors:\n  ${[...new Set(errs)].join('\n  ')}`);
  ws.close(); ch.kill('SIGTERM');
  await Promise.race([new Promise(r => ch.once('exit', r)), sleep(5000)]);
  try { rmSync(prof, { recursive: true, force: true }); } catch (e) { /* Chrome still closing its profile */ }
  writeFileSync(OUT.replace(/\.mp4$/, '.beats.json'), JSON.stringify({ fps: FPS, frames: F, seconds: +(F / FPS).toFixed(2), beats, captions: caps.map(c => ({ t: c.t, from: +(c.f0 / FPS).toFixed(2), to: c.f1 === Infinity ? +(F / FPS).toFixed(2) : +(c.f1 / FPS).toFixed(2) })) }, null, 1));
  if (PREVIEW) { console.log(`preview: ${F} frames (${(F / FPS).toFixed(1)} s), every ${EVERY}th in ${PREVIEW}${stopped ? ' (stopped by --until)' : ''}`); return; }
  ff.stdin.end();
  const code = await ffDone;
  if (code !== 0) throw new Error(`ffmpeg failed (${code}): ${ffErr}`);
  // check: the encoded frame count, rate and duration against what was filmed
  const pr = spawnSync(FFPROBE, ['-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=nb_read_frames,r_frame_rate,avg_frame_rate,width,height,pix_fmt:format=duration,size', '-of', 'json', OUT], { encoding: 'utf8' });
  const P = JSON.parse(pr.stdout || '{}'), st = (P.streams || [])[0] || {}, fm = P.format || {};
  const okN = +st.nb_read_frames === F, okR = st.r_frame_rate === `${FPS}/1` && st.avg_frame_rate === `${FPS}/1`, okD = +fm.duration <= 120;
  console.log(`${OUT}: ${(+fm.duration).toFixed(2)} s, ${st.width}×${st.height} ${st.pix_fmt}, ${st.r_frame_rate} fps, ${st.nb_read_frames} frames (filmed ${F}), ${(+fm.size / 1e6).toFixed(1)} MB, ${((Date.now() - t00) / 60000).toFixed(1)} min`);
  if (!okN || !okR || !okD) { console.error(`CHECK FAILED: frames ${okN ? 'ok' : 'MISMATCH'}, rate ${okR ? 'ok' : 'NOT CONSTANT'}, duration ${okD ? 'ok' : 'OVER 120 s'}`); process.exit(1); }
  console.log('check ok: constant 30 fps, every filmed frame encoded, ≤ 120 s; beats in ' + OUT.replace(/\.mp4$/, '.beats.json'));
}
main().catch(e => { console.error(e); process.exit(1); });
