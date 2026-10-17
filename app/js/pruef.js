// Prüfstand: the held-out federal results, the parliaments' own schemes as one table, a link to the full list
// (docs/PRUEFSTAND.md), and one coverage–precision chart (black line, red dot at the shipped operating point).
import { D, SRC } from './data.js';
import { h, s, t, UI, num, pct, p3 } from './util.js';
import { bindTips } from './viz.js';

// Local strings for the lead, the cantonal table and the closing lines (kept here, not in util.js).
const nw = x => h('span', { style: 'white-space:nowrap' }, x);   // keep a figure with its % on one line
const DOC = 'https://github.com/mi11ione/querschnitt/blob/main/docs/PRUEFSTAND.md';
const LS = {
  de: {
    intro: 'Wie gut ordnet Apertus zu? Verglichen mit Fachleuten, die dieselben Geschäfte von Hand eingeordnet haben:',
    fed: n => `der ${n} neuen Bundesgeschäfte bekommen von Apertus dasselbe Themenkapitel, das ihnen die Redaktion der Année politique suisse (APS) gegeben hat; keines davon wurde beim Entwickeln benutzt.`,
    fedSub: (lp, kw, tr) => [lp != null ? `nur Kapitelliste ${pct(lp)}` : '', tr != null ? `trainiert auf 1'654 APS-Labels ${pct(tr)}` : '', kw != null ? `Stichwortsuche ${pct(kw)}` : ''].filter(Boolean).join(' · '),
    cmp: 'Vergleich:',
    lane: (n, ok, chk) => [`der ${n} neuen Bundesgeschäfte gehen ohne Prüfung durch, und davon sind `, nw(ok), ` richtig; den Rest legt Querschnitt `, h('span', { class: 'rtick' }), ` einer Person vor (dort `, nw(chk), ` richtig).`],
    laneSub: 'Regel: rekalibriertes p ≥ 0.7, vor dem Test festgelegt',
    cols: ['Parlament', 'eigenes Schema', 'n', 'top-1 [95 %]', 'Stichwort', 'Datei'],
    be: ['Bern, Grosser Rat', k => `${k} Direktionen`],
    bs: ['Basel-Stadt, Grosser Rat', k => `${k} Themen der Kantons- und Stadtentwicklung`],
    ti: ['Tessin, Gran Consiglio', k => `${k} Stellen, italienisch; Text nennt keine`],
    dig: (a, ka, p, kp) => `«Digitalisierung»: ${a} DVS-Geschäfte gefunden (Stichwort ${ka}) · Präzision ${p} gegen KI-Richter (Stichwort ${kp})`,
    doc: 'Alle Tests mit Stichprobe, Intervall, Vergleich und Quelldatei: ',
    internal: 'intern',
    codes: { D0: 'Listen-Prompt', D1: 'ohne Beispiele', D2: 'DE + FR gemittelt', D3: 'fünf Beispiele', D4: 'mit Beispielen, zwei Lesarten', D4s: 'Variante' },
  },
  fr: {
    intro: 'Le classement d’Apertus est-il bon ? Comparé à des spécialistes qui ont classé les mêmes objets à la main :',
    fed: n => `des ${n} nouveaux objets fédéraux reçoivent d’Apertus le chapitre thématique que leur a attribué la rédaction de l’Année politique suisse (APS) ; aucun n’a servi pendant le développement.`,
    fedSub: (lp, kw, tr) => [lp != null ? `liste des chapitres seule ${pct(lp)}` : '', tr != null ? `entraîné sur 1 654 étiquettes APS ${pct(tr)}` : '', kw != null ? `mots-clés ${pct(kw)}` : ''].filter(Boolean).join(' · '),
    cmp: 'comparaison :',
    lane: (n, ok, chk) => [`des ${n} nouveaux objets fédéraux passent sans vérification, dont `, nw(ok), ` sont justes ; Querschnitt soumet le reste `, h('span', { class: 'rtick' }), ` à une personne (là, `, nw(chk), ` justes).`],
    laneSub: 'règle : p recalibré ≥ 0,7, fixée avant le test',
    cols: ['parlement', 'schéma propre', 'n', 'top-1 [95 %]', 'mots-clés', 'fichier'],
    be: ['Berne, Grand Conseil', k => `${k} directions`],
    bs: ['Bâle-Ville, Grand Conseil', k => `${k} thèmes du développement cantonal et urbain`],
    ti: ['Tessin, Gran Consiglio', k => `${k} unités, en italien ; le texte n’en nomme aucune`],
    dig: (a, ka, p, kp) => `« numérique » : ${a} objets DVS trouvés (mots-clés ${ka}) · précision ${p} contre juge IA (mots-clés ${kp})`,
    doc: 'Tous les tests avec échantillon, intervalle, référence et fichier source : ',
    internal: 'interne',
    codes: { D0: 'liste', D1: 'sans exemples', D2: 'DE + FR moyennés', D3: 'cinq exemples', D4: 'avec exemples, deux lectures', D4s: 'variante' },
  },
};
const ls = () => LS[UI.lang === 'fr' ? 'fr' : 'de'];

// Visible jargon → plain words (the chart's test labels). Design codes (D0…D4s) and test ids (S9…S27) leave the visible
// text; the data stay as they are. Returns [text, tip|null].
function plain(str) {
  if (!str) return [str, null];
  const S = ls(), names = S.codes, codes = [];
  const add = c => { if (!codes.includes(c)) codes.push(c); return ''; };
  let t = String(str)
    .replace(/\s*\((S\d+(?:\/S\d+)*)\)/g, (m, c) => add(c))                 // "(S19)"
    .replace(/,\s*(S\d+(?:\/S\d+)*)\)/g, (m, c) => (add(c), ')'))            // "(hold-out, S25)"
    .replace(/\((S\d+) (?=D\d)/g, (m, c) => (add(c), '('))                   // "(S9 D1)"
    .replace(/\s*\((D\d+s?)\)/g, (m, c) => add(c))                           // "(D3)"
    .replace(/\((D\d+s?),\s*/g, (m, c) => (add(c), '('))                    // "(D4, ausgeliefert)"
    .replace(/\((D\d+s?)( ?;)\s*/g, (m, c, sc, off, all) => {                // "(D4; D1 …)"
      add(c); const nm = names[c];
      return !nm || all.slice(0, off).includes(nm) ? '(' : `(${nm}${sc} `;
    })
    .replace(/^(D\d+s?),\s*/, (m, c) => add(c))                              // "D4, Lesarten einig"
    .replace(/\b(D\d+s?)\b( ?)/g, (m, c, sp, off, all) => {                  // bare code → its plain name
      const nm = names[c]; if (!nm) return m; add(c);
      return all.startsWith(nm, off + m.length) ? '' : `«${nm}»${sp}`;
    });
  if (!codes.length) return [str, null];
  return [t, `${S.internal}: ${codes.map(c => names[c] ? `${c} = ${names[c]}` : c).join(' · ')}`];
}

const num1 = (str, re) => { const m = re.exec(str || ''); return m ? parseFloat(m[1]) : null; };

// The lead: the two federal results in plain words, the three cantonal schemes as one table, the «Digitalisierung» line
// and the link to the full list. Every figure is read from the rows (pruefstand.json) or the held-out decisions
// (pruef_confusion.json); a line or row whose source is missing is left out.
function lead(rows) {
  const S = ls(), L = t(), out = [];
  const byFile = f => rows.find(r => r.file === f);
  const item = (big, text, sub, file) => h('li', {}, h('b', { class: 'pl-n' }, big),
    h('div', {}, h('p', { class: 'pl-t' }, text), h('p', { class: 'pl-s' }, [sub, file].filter(Boolean).join(' · '))));
  // a collapsed bootstrap interval ([1, 1]: no miss resampled) is not a 95% interval; it is named, not printed
  const ci = r => Array.isArray(r.interval) ? (r.interval[0] === r.interval[1] ? ` (${L.noCi})` : ` [${r.interval.map(v => v.toFixed(3)).join(', ')}]`) : '';
  const fed = byFile('eval/s25/results.json'), cf = D.conf && D.conf.heldout ? D.conf : null;
  if (fed) {
    const top1 = cf && cf.n === fed.n ? cf.correct / cf.n : num1(fed.result, /top-1 ([\d.]+)/);
    if (top1 != null) {
      // S34: a classifier trained on the 1,654 APS labels of the example pool, the same 927 affairs (its row's file)
      const tr = byFile('eval/s34/results.json');
      const cmp = S.fedSub(num1(fed.baseline, /Listen-Prompt ([\d.]+)/), num1(fed.baseline, /Stichwort ([\d.]+)/), tr ? num1(tr.result, /top-1 ([\d.]+)/) : null);
      out.push(item(pct(top1), S.fed(num(fed.n)), `top-1 ${p3(top1)}${ci(fed)}${cmp ? ` · ${S.cmp} ${cmp}` : ''}`, fed.file));
    }
  }
  const lt = cf && cf.lanes_tau;
  if (lt && lt.pass_ && lt.check) {
    out.push(item(pct(lt.pass_.coverage), S.lane(num(lt.pass_.n + lt.check.n), pct(lt.pass_.precision).replace(' ', ' '), pct(lt.check.precision).replace(' ', ' ')),
      `${S.laneSub} · n ${num(lt.pass_.n)} + ${num(lt.check.n)}`, lt.file));
  }
  // the parliaments' own schemes: one row each (first row of its file = the primary population)
  const kw = r => { const m = /Stichwort ([\d.]+)(?: \/ ([\d.]+))?/.exec(r.baseline || ''); return m ? [m[1], m[2]].filter(Boolean).map(v => p3(parseFloat(v))).join(' / ') : '–'; };
  const cant = [];
  for (const [key, f] of [['be', 'eval/s18/results.json'], ['bs', 'eval/s20/results.json'], ['ti', 'eval/s29/results.json']]) {
    const r = byFile(f); if (!r) continue;
    const k = num1(r.test, /\((\d+)\)/), [par, sch] = S[key];
    const de = num1(r.result, /DE ([\d.]+)/), frv = num1(r.result, /FR ([\d.]+)/), top1 = num1(r.result, /top-1 ([\d.]+)/);
    const res = de != null && frv != null ? `DE ${p3(de)}${ci(r)} · FR ${p3(frv)}` : top1 != null ? `${p3(top1)}${ci(r)}` : null;
    if (res == null) continue;
    cant.push(h('tr', {}, h('td', {}, par), h('td', { class: 'base' }, sch(k != null ? num(k) : '–')), h('td', { class: 'n' }, num(r.n)),
      h('td', { class: 'res' }, res), h('td', { class: 'res' }, kw(r)), h('td', { class: 'base mono' }, r.file)));
  }
  const tab = cant.length ? h('div', { class: 'tw', style: 'margin-top:16px' }, h('table', {},
    h('thead', {}, h('tr', {}, S.cols.map((c, i) => h('th', { class: i === 2 ? 'n' : '' }, c)))), h('tbody', {}, cant))) : '';
  // «Digitalisierung»: the hand-picked DVS list (human) and the 2026 census precision (judge), each against keywords
  const dvs = rows.find(r => r.file === 'eval/spikes/s8-dvs/results.md'), cen = rows.find(r => r.file === 'eval/s8full/results.json' && r.design === 'Präzision');
  const dk = dvs && /Stichwort (\d+\/\d+)/.exec(dvs.baseline || ''), ck = cen && num1(cen.baseline, /Stichwort ([\d.]+)/), cp = cen && parseFloat(cen.result);
  const dig = dvs && dk && cen && ck != null && !Number.isNaN(cp) ? h('p', { class: 'pl-note' }, S.dig(dvs.result, dk[1], p3(cp), p3(ck))) : '';
  if (!out.length && !cant.length) return null;
  return h('div', { class: 'pl' }, h('p', { class: 'pl-in' }, S.intro), out.length ? h('ol', { class: 'pl-l' }, out) : '', tab, dig,
    h('p', { class: 'pl-note' }, S.doc, h('a', { href: DOC, target: '_blank', rel: 'noopener' }, 'docs/PRUEFSTAND.md')));
}

export function renderPruef(root) {
  const L = t(), P = D.pruef;
  root.replaceChildren();
  const wrap = h('div', { class: 'pr' }); root.append(wrap);
  const left = h('div', { class: 'pane' }), right = h('div', { class: 'pane' });
  wrap.append(left, right);
  if (!P) { left.append(h('p', { class: 'empty' }, '–')); return; }
  const rows = Array.isArray(P) ? P : P.rows || [];
  const ld = lead(rows);
  if (ld) left.append(ld);
  if (SRC['pruefstand.json'] === 'data-fixture/') left.append(h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `pruefstand.json ${L.fromFixture}`));
  if (P.curve) {
    // held out first: the S25 curve (black, red dot at the shipped lane); the design-set curve stays as a grey reference
    const hc = D.conf && D.conf.curve, cv = hc ? { ...hc, ref: P.curve.points, refLabel: [P.curve.test, P.curve.test_fr] } : { ...P.curve };
    right.append(chart(cv));
  }
  if (D.conf && D.conf.m) right.append(confusion(D.conf));
  bindTips(right);
}

function chart(cv) {
  const L = t(), fr = UI.lang === 'fr';
  const W = 400, H = 300, ml = 44, mr = 12, mt = 12, mb = 36;
  const pts = cv.points || [];
  const ys = pts.concat(cv.ref || []).map(p => p[1]);
  const y0 = Math.max(0, Math.floor((Math.min(...ys, cv.op ? cv.op.precision : 1) - .05) * 10) / 10), y1 = 1;
  const X = v => ml + v * (W - ml - mr), Y = v => mt + (1 - (v - y0) / (y1 - y0)) * (H - mt - mb);
  const svg = s('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': L.cpTitle });
  for (let v = 0; v <= 1.0001; v += .2) {
    svg.append(s('line', { class: 'gr', x1: X(v), x2: X(v), y1: mt, y2: H - mb }));
    const tx = s('text', { x: X(v), y: H - mb + 16, 'text-anchor': 'middle' }); tx.textContent = `${Math.round(v * 100)}`; svg.append(tx);
  }
  for (let v = y0; v <= 1.0001; v += .1) {
    svg.append(s('line', { class: 'gr', x1: ml, x2: W - mr, y1: Y(v), y2: Y(v) }));
    const tx = s('text', { x: ml - 6, y: Y(v) + 4, 'text-anchor': 'end' }); tx.textContent = v.toFixed(1); svg.append(tx);
  }
  svg.append(s('line', { class: 'ax', x1: ml, x2: W - mr, y1: H - mb, y2: H - mb }), s('line', { class: 'ax', x1: ml, x2: ml, y1: mt, y2: H - mb }));
  const xl = s('text', { x: W - mr, y: H - 4, 'text-anchor': 'end' }); xl.textContent = `${L.cpX} %`; svg.append(xl);
  if (cv.ref) svg.append(s('path', { class: 'ln ref', d: cv.ref.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join('') }));
  svg.append(s('path', { class: 'ln', d: pts.map((p, i) => `${i ? 'L' : 'M'}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join('') }));
  if (cv.op2) {
    const ox = X(cv.op2.coverage), oy = Y(cv.op2.precision);
    svg.append(s('circle', { class: 'op2', cx: ox, cy: oy, r: 4, tabindex: '0', 'data-tip': `${cv.op2.label_de && UI.lang === 'fr' ? cv.op2.label_fr : cv.op2.label_de}: ${pct(cv.op2.coverage)} · ${p3(cv.op2.precision)}` }));
  }
  if (cv.op) {
    const ox = X(cv.op.coverage), oy = Y(cv.op.precision);
    svg.append(s('circle', { class: 'op', cx: ox, cy: oy, r: 5 }));
    const tx = s('text', { x: ox + 8, y: oy - 9, class: 'opl' }); tx.textContent = `${pct(cv.op.coverage)} · ${p3(cv.op.precision)}`; svg.append(tx);
  }
  return h('div', { class: 'chart' },
    h('h3', {}, L.cpTitle),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 12px' }, `${plain((fr && cv.test_fr) || cv.test || '')[0]} · n ${num(cv.n)}`),
    svg,
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin-top:8px' }, [cv.ref ? `${L.refCurve}: ${plain((fr && cv.refLabel[1]) || cv.refLabel[0])[0]}` : '', cv.file ? `${L.file}: ${cv.file}` : ''].filter(Boolean).join(' · ')));
}

// which chapter the editors gave (rows) against which Querschnitt gave (columns), the 927 held-out affairs; grey = the
// row's share, diagonal outlined; each cell names both chapters and its count on hover
function confusion(cf) {
  const L = t(), m = cf.m, K = m.length, chs = D.scheme.chapters;
  const nm = k => chs[k] ? (UI.lang === 'fr' ? chs[k].fr || chs[k].de : chs[k].de) : String(k);
  const rows = [...Array(K).keys()].filter(r => m[r].some(v => v) || m.some(row => row[r]));
  const n = rows.length, cs = 12, W = n * cs;
  const svg = s('svg', { viewBox: `-1 -1 ${W + 2} ${W + 2}`, class: 'cf', role: 'img', 'aria-label': L.rowsGold });
  rows.forEach((r, ri) => {
    const tot = m[r].reduce((a, b) => a + b, 0);
    rows.forEach((c, cj) => {
      const v = m[r][c], sh = tot ? v / tot : 0, cls = v ? Math.min(5, 1 + Math.floor(sh * 5)) : 0;
      svg.append(s('rect', { x: cj * cs, y: ri * cs, width: cs - 1, height: cs - 1, style: `fill:var(--r${cls})${r === c ? ';stroke:var(--ink);stroke-width:1' : ''}`,
        'data-tip': `${L.gold}: ${nm(r)} → ${L.pred}: ${nm(c)} · ${num(v)} ${L.of} ${num(tot)}${tot ? ` (${pct(sh)})` : ''}` }));
    });
  });
  return h('div', { style: 'margin-top:28px' }, h('h3', { style: 'margin:0;font:600 var(--f3)/1.3 var(--sans)' }, CONF[UI.lang === 'fr' ? 'fr' : 'de']),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 8px' }, `${L.rowsGold} · ${L.colsPred} · n ${num(cf.n)}`), h('div', { style: 'max-width:360px' }, svg));
}
const CONF = { de: 'Welches Kapitel statt welchem', fr: 'Quel chapitre à la place de quel autre' };
