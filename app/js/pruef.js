// Prüfstand: one ruled table per test (human labels first), one coverage–precision chart (black line, red dot at the
// shipped operating point).
import { D, SRC } from './data.js';
import { h, s, t, UI, num, pct, p3 } from './util.js';
import { bindTips } from './viz.js';

export function testCount() {
  const P = D.pruef; if (!P) return 0;
  const rows = Array.isArray(P) ? P : P.rows || [];
  return new Set(rows.map(r => r.test)).size;
}

// Local strings for the plain-language lead and the jargon rewrite (kept here, not in util.js).
const nw = x => h('span', { style: 'white-space:nowrap' }, x);   // keep a figure with its % on one line
const LS = {
  de: {
    intro: 'Wie gut ordnet Apertus zu? Verglichen mit Fachleuten, die dieselben Geschäfte von Hand eingeordnet haben:',
    fed: n => `der ${n} neuen Bundesgeschäfte bekommen von Apertus dasselbe Themenkapitel, das ihnen die Redaktion der Année politique suisse (APS) gegeben hat; keines davon wurde beim Entwickeln benutzt.`,
    fedSub: (lp, kw) => [lp != null ? `nur Kapitelliste ${pct(lp)}` : '', kw != null ? `Stichwortsuche ${pct(kw)}` : ''].filter(Boolean).join(' · '),
    cmp: 'Vergleich:',
    lane: (n, ok, chk) => [`der ${n} neuen Bundesgeschäfte gehen ohne Prüfung durch, und davon sind `, nw(ok), ` richtig; den Rest legt Querschnitt `, h('span', { class: 'rtick' }), ` einer Person vor (dort `, nw(chk), ` richtig).`],
    laneSub: 'Regel: rekalibriertes p ≥ 0.7, vor dem Test festgelegt',
    be: (n, k, other) => `der ${n} Geschäfte des Berner Grossen Rates landen mit deutschem Titel bei der federführenden von ${k} Direktionen; mit französischem Titel ${other}.`,
    beSub: (a, b) => `Stichwortsuche ${pct(a)} / ${pct(b)}`,
    bs: (n, k) => `der ${n} Basler Grossratsgeschäfte bekommen dasselbe der ${k} Themen wie bei der Kantons- und Stadtentwicklung, allein aus der Liste der Themennamen, ohne jede Anpassung.`,
    bsSub: (ex, kw) => [ex != null ? `mit fünf Basler Beispielen ${pct(ex)}` : '', kw != null ? `Stichwortsuche ${pct(kw)}` : ''].filter(Boolean).join(' · '),
    ti: (n, k) => `der ${n} Geschäfte des Tessiner Grossen Rates landen auf Italienisch bei der federführenden von ${k} Stellen (fünf Departemente und Staatskanzlei), allein aus der Liste der Namen, ohne jede Anpassung; gezählt sind die Geschäfte, deren Text die Stelle nicht selbst nennt.`,
    tiSub: (kw, mj) => [kw != null ? `Stichwortsuche ${pct(kw)}` : '', mj != null ? `häufigste Stelle ${pct(mj)}` : ''].filter(Boolean).join(' · '),
    note: 'Darunter alle Tests, auch die schwächeren: jede Zahl mit Stichprobe (n), 95-%-Intervall, Vergleich auf denselben Geschäften und Quelldatei. Vorab registriert ist ein Test nur, wo «vorregistriert» steht.',
    all: 'Alle Tests',
    gloss: [['top-1 / top-3', 'das erste Thema stimmt / das richtige ist unter den ersten drei'],
      ['Präzision', 'Anteil richtig unter den Geschäften einer Spur'],
      ['Spur', 'ohne Prüfung oder bitte prüfen, je nach Konfidenz p'],
      ['Lesart', 'dieselbe Frage zweimal gestellt (z. B. mit und ohne Beispiele); einig = beide Antworten gleich'],
      ['Listen-Prompt', 'nur die Themenliste, ohne Beispiele'],
      ['Stichwort', 'Suche nach Wörtern, ohne Modell'],
      ['KI-Richter', 'ein zweites Modell (Claude) urteilt, wo keine menschlichen Labels existieren'],
      ['S25, D4 …', 'interne Kennungen von Tests und Varianten (Maus darüber); Ordner eval/']],
    internal: 'intern',
    lanesPop: n => `der ${n} neuen Bundesgeschäfte (Test)`,
    codes: { D0: 'Listen-Prompt', D1: 'ohne Beispiele', D2: 'DE + FR gemittelt', D3: 'fünf Beispiele', D4: 'mit Beispielen, zwei Lesarten', D4s: 'Variante' },
  },
  fr: {
    intro: 'Le classement d’Apertus est-il bon ? Comparé à des spécialistes qui ont classé les mêmes objets à la main :',
    fed: n => `des ${n} nouveaux objets fédéraux reçoivent d’Apertus le chapitre thématique que leur a attribué la rédaction de l’Année politique suisse (APS) ; aucun n’a servi pendant le développement.`,
    fedSub: (lp, kw) => [lp != null ? `liste des chapitres seule ${pct(lp)}` : '', kw != null ? `mots-clés ${pct(kw)}` : ''].filter(Boolean).join(' · '),
    cmp: 'comparaison :',
    lane: (n, ok, chk) => [`des ${n} nouveaux objets fédéraux passent sans vérification, dont `, nw(ok), ` sont justes ; Querschnitt soumet le reste `, h('span', { class: 'rtick' }), ` à une personne (là, `, nw(chk), ` justes).`],
    laneSub: 'règle : p recalibré ≥ 0,7, fixée avant le test',
    be: (n, k, other) => `des ${n} objets du Grand Conseil bernois arrivent, avec le titre français, à la direction compétente parmi ${k} ; avec le titre allemand ${other}.`,
    beSub: (a, b) => `mots-clés ${pct(a)} / ${pct(b)}`,
    bs: (n, k) => `des ${n} objets du Grand Conseil bâlois reçoivent le même des ${k} thèmes que chez Kantons- und Stadtentwicklung, à partir des seuls noms des thèmes, sans aucun ajustement.`,
    bsSub: (ex, kw) => [ex != null ? `avec cinq exemples bâlois ${pct(ex)}` : '', kw != null ? `mots-clés ${pct(kw)}` : ''].filter(Boolean).join(' · '),
    ti: (n, k) => `des ${n} objets du Grand Conseil tessinois arrivent, en italien, à l’unité compétente parmi ${k} (cinq départements et la Chancellerie), à partir de la seule liste des noms, sans aucun ajustement ; comptés : les objets dont le texte ne nomme pas lui-même l’unité.`,
    tiSub: (kw, mj) => [kw != null ? `mots-clés ${pct(kw)}` : '', mj != null ? `unité la plus fréquente ${pct(mj)}` : ''].filter(Boolean).join(' · '),
    note: 'Ci-dessous tous les tests, y compris les moins bons : chaque chiffre avec échantillon (n), intervalle 95 %, référence sur les mêmes objets et fichier source. Un test n’est préenregistré que là où « préenregistré » est indiqué.',
    all: 'Tous les tests',
    gloss: [['top-1 / top-3', 'le premier thème est juste / le bon est parmi les trois premiers'],
      ['précision', 'part de réponses justes parmi les objets d’une voie'],
      ['voie', 'sans vérification ou à vérifier, selon la confiance p'],
      ['lecture', 'la même question posée deux fois (p. ex. avec et sans exemples) ; concordantes = deux réponses identiques'],
      ['liste', 'seulement la liste des thèmes, sans exemples'],
      ['mots-clés', 'recherche par mots, sans modèle'],
      ['juge IA', 'un second modèle (Claude) juge là où il n’y a pas d’étiquettes humaines'],
      ['S25, D4 …', 'identifiants internes des tests et variantes (survol) ; dossier eval/']],
    internal: 'interne',
    lanesPop: n => `des ${n} nouveaux objets fédéraux (test)`,
    codes: { D0: 'liste', D1: 'sans exemples', D2: 'DE + FR moyennés', D3: 'cinq exemples', D4: 'avec exemples, deux lectures', D4s: 'variante' },
  },
};
const ls = () => LS[UI.lang === 'fr' ? 'fr' : 'de'];

// Visible jargon → plain words. Design codes (D0…D4s) and test ids (S9…S27) leave the visible text and go to a tooltip;
// the data stay as they are. Returns [text, tip|null].
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

// The lead: three to five results in plain words, each read from the rows (pruefstand.json) or the held-out decisions
// (pruef_confusion.json). A line whose source row is missing is left out.
function lead(rows) {
  const S = ls(), fr = UI.lang === 'fr', out = [];
  const byFile = f => rows.find(r => r.file === f);
  const item = (big, text, sub, file) => h('li', {}, h('b', { class: 'pl-n' }, big),
    h('div', {}, h('p', { class: 'pl-t' }, text), h('p', { class: 'pl-s' }, [sub, file].filter(Boolean).join(' · '))));
  // a collapsed bootstrap interval ([1, 1]: no miss resampled) is not a 95% interval; it is named, not printed
  const ci = r => Array.isArray(r.interval) ? (r.interval[0] === r.interval[1] ? ` (${L.noCi})` : ` [${r.interval.map(v => v.toFixed(3)).join(', ')}]`) : '';
  const fed = byFile('eval/s25/results.json'), cf = D.conf && D.conf.heldout ? D.conf : null;
  if (fed) {
    const top1 = cf && cf.n === fed.n ? cf.correct / cf.n : num1(fed.result, /top-1 ([\d.]+)/);
    if (top1 != null) {
      const cmp = S.fedSub(num1(fed.baseline, /Listen-Prompt ([\d.]+)/), num1(fed.baseline, /Stichwort ([\d.]+)/));
      out.push(item(pct(top1), S.fed(num(fed.n)), `top-1 ${p3(top1)}${ci(fed)}${cmp ? ` · ${S.cmp} ${cmp}` : ''}`, fed.file));
    }
  }
  const lt = cf && cf.lanes_tau;
  if (lt && lt.pass_ && lt.check) {
    out.push(item(pct(lt.pass_.coverage), S.lane(num(lt.pass_.n + lt.check.n), pct(lt.pass_.precision).replace(' ', '\u00a0'), pct(lt.check.precision).replace(' ', '\u00a0')),
      `${S.laneSub} · n ${num(lt.pass_.n)} + ${num(lt.check.n)}`, lt.file));
  }
  const be = byFile('eval/s18/results.json');
  if (be) {
    const de = num1(be.result, /DE ([\d.]+)/), frv = num1(be.result, /FR ([\d.]+)/), k = num1(be.test, /\((\d+)\)/);
    if (de != null && frv != null) {
      const kw = /Stichwort ([\d.]+) \/ ([\d.]+)/.exec(be.baseline || '');
      out.push(item(pct(fr ? frv : de), S.be(num(be.n), k != null ? num(k) : '–', pct(fr ? de : frv)),
        `DE ${p3(de)} · FR ${p3(frv)}${kw ? ` · ${S.beSub(parseFloat(kw[1]), parseFloat(kw[2]))}` : ''}`, be.file));
    }
  }
  const bs = byFile('eval/s20/results.json'), bs2 = byFile('eval/s21/results.json');
  if (bs) {
    const top1 = num1(bs.result, /top-1 ([\d.]+)/), k = num1(bs.test, /\((\d+)\)/);
    if (top1 != null) {
      const sub = S.bsSub(bs2 ? num1(bs2.result, /top-1 ([\d.]+)/) : null, num1(bs.baseline, /Stichwort ([\d.]+)/));
      out.push(item(pct(top1), S.bs(num(bs.n), k != null ? num(k) : '–'), `top-1 ${p3(top1)}${ci(bs)}${sub ? ` · ${sub}` : ''}`, bs.file));
    }
  }
  const ti = byFile('eval/s29/results.json');   // first S29 row = the primary population (inputs that name no unit)
  if (ti) {
    const top1 = num1(ti.result, /top-1 ([\d.]+)/), k = num1(ti.test, /\((\d+)\)/);
    if (top1 != null) {
      const sub = S.tiSub(num1(ti.baseline, /Stichwort ([\d.]+)/), num1(ti.baseline, /Mehrheit ([\d.]+)/));
      out.push(item(pct(top1), S.ti(num(ti.n), k != null ? num(k) : '–'), `top-1 ${p3(top1)}${ci(ti)}${sub ? ` · ${sub}` : ''}`, ti.file));
    }
  }
  if (!out.length) return null;
  return h('div', { class: 'pl' }, h('p', { class: 'pl-in' }, S.intro), h('ol', { class: 'pl-l' }, out), h('p', { class: 'pl-note' }, S.note));
}

export function renderPruef(root) {
  const L = t(), P = D.pruef;
  root.replaceChildren();
  const wrap = h('div', { class: 'pr' }); root.append(wrap);
  const left = h('div', { class: 'pane' }), right = h('div', { class: 'pane' });
  wrap.append(left, right);
  if (!P) { left.append(h('p', { class: 'empty' }, '–')); return; }
  const rows = Array.isArray(P) ? P : P.rows || [];
  const fr = UI.lang === 'fr';
  const tests = new Map();
  for (const r of rows) { if (!tests.has(r.test)) tests.set(r.test, []); tests.get(r.test).push(r); }
  const order = [...tests.entries()].sort((a, b) => (a[1][0].gold === 'human' ? 0 : 1) - (b[1][0].gold === 'human' ? 0 : 1));
  const ld = lead(rows);
  if (ld) left.append(ld, h('h2', { class: 'pl-h' }, ls().all), h('dl', { class: 'pl-gl' }, ls().gloss.flatMap(([k, v]) => [h('dt', {}, k), h('dd', {}, v)])));
  let lastGold = null;
  for (const [name, rs] of order) {
    const r0 = rs[0];
    if (r0.gold && r0.gold !== lastGold) { left.append(h('p', { class: 'grp' }, r0.gold === 'human' ? L.human : r0.gold === 'judge' ? L.judge : r0.gold)); lastGold = r0.gold; }
    const file = r0.file ? (/^https?:/.test(r0.file) ? h('a', { href: r0.file, target: '_blank', rel: 'noopener' }, r0.file) : r0.file) : '';
    const [title, titleTip] = plain((fr && r0.test_fr) || name);
    const sec = h('section', { class: 'test' },
      h('h3', { 'data-tip': titleTip }, title),
      h('p', { class: 'tm' }, [r0.split ? `${L.split}: ${(fr && r0.split_fr) || r0.split}` : '', r0.file ? `${L.file}: ` : ''].filter(Boolean).join(' · '), file));
    const tb = h('table', {}, h('colgroup', {}, h('col', { class: 'c-d' }), h('col'), h('col'), h('col'), h('col')),
      h('thead', {}, h('tr', {}, h('th', {}, L.design), h('th', { class: 'n' }, 'n'), h('th', {}, L.result), h('th', {}, L.ci), h('th', {}, L.baseline))));
    const body = h('tbody');
    for (const r of rs) {
      const ci = Array.isArray(r.interval) && r.interval[0] === r.interval[1] ? L.noCi : Array.isArray(r.interval) ? `[${r.interval.map(v => typeof v === 'number' ? v.toFixed(3) : v).join(', ')}]` : (r.interval || '–');  // bounds are stored at 3 decimals (truncated / outward)
      const ship = r === order[0][1][0]; // the production row leads the first human-label table
      const [des, desTip] = plain((fr && r.design_fr) || r.design), [base, baseTip] = plain((fr && r.baseline_fr) || r.baseline || '–');
      body.append(h('tr', { class: ship ? 'ship' : '' }, h('td', { 'data-tip': desTip }, des), h('td', { class: 'n' }, num(r.n)), h('td', { class: 'res' }, String((fr && r.result_fr) || r.result)),
        h('td', { class: 'res' }, ci), h('td', { class: 'base', 'data-tip': baseTip }, base)));
    }
    tb.append(body); sec.append(h('div', { class: 'tw' }, tb)); left.append(sec);
  }
  if (SRC['pruefstand.json'] === 'data-fixture/') left.append(h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `pruefstand.json ${L.fromFixture}`));
  if (P.curve) {
    // held out first: the S25 curve (black, red dot at the shipped lane); the design-set curve stays as a grey reference
    const hc = D.conf && D.conf.curve, cv = hc ? { ...hc, ref: P.curve.points, refLabel: [P.curve.test, P.curve.test_fr] } : { ...P.curve };
    right.append(chart(cv));
  }
  if (D.conf) right.append(D.conf.lanes_tau ? lanesTau(D.conf.lanes_tau) : lanesBar(D.conf), confusion(D.conf));
  bindTips(right); bindTips(left);
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
    cv.op ? h('p', { class: 'tm mono', style: 'font-size:12px;margin-top:8px' }, `${(fr ? cv.op.label_fr : cv.op.label_de) || ''}: ${L.cpX} ${pct(cv.op.coverage)}, ${L.cpY} ${p3(cv.op.precision)} (n ${num(cv.op.n)})`) : '',
    cv.ref ? h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `${L.refCurve}: ${plain((fr && cv.refLabel[1]) || cv.refLabel[0])[0]}`) : '',
    cv.file ? h('p', { class: 'tm mono dim', style: 'font-size:12px' }, `${L.file}: ${cv.file}`) : '');
}

// the two lanes of the shipped design as one split bar: width = share of affairs, dark part = precision in that lane
function lanesBar(cf) {
  const L = t(), l = cf.lanes, n = l.agree_n + l.disagree_n, a = l.agree_n / n;
  const seg = (w, k, nn, cls, lab) => h('span', { class: `lseg ${cls}`, style: `width:${w * 100}%`, tabindex: '0', 'data-tip': `${lab} · ${pct(nn / n)} (n ${num(nn)}) · ${L.cpY} ${p3(k / nn)}` },
    h('span', { class: 'lok', style: `width:${(k / nn) * 100}%` }));
  return h('div', { class: 'lanes' }, h('h3', {}, L.lanesT),
    h('div', { class: 'lbar' }, seg(a, l.agree_k, l.agree_n, 'ag', L.agree), seg(1 - a, l.disagree_k, l.disagree_n, 'dis', L.disagree)),
    h('div', { class: 'llab' }, h('span', { style: `width:${a * 100}%` }, `${L.agree} ${pct(a)} · ${p3(l.agree_k / l.agree_n)}`),
      h('span', { style: `width:${(1 - a) * 100}%` }, h('span', { class: 'rtick' }), ` ${L.disagree} · ${p3(l.disagree_k / l.disagree_n)}`)),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:6px 0 0' }, `${L.cpY}: ${L.dark}; n ${num(n)} · ${cf.design}`));
}

// confusion: rows = APS editors' chapter, columns = Querschnitt's; cell grey = share of the row; diagonal outlined
function confusion(cf) {
  const L = t(), m = cf.m, K = m.length, chs = D.scheme.chapters;
  const nm = k => chs[k] ? (UI.lang === 'fr' ? chs[k].fr || chs[k].de : chs[k].de) : String(k);
  const rows = [...Array(K).keys()].filter(r => m[r].some(v => v) || m.some(row => row[r]));
  const n = rows.length, cs = 12, LW = 0, W = n * cs, H = n * cs;
  const svg = s('svg', { viewBox: `-1 -1 ${W + 2} ${H + 2}`, class: 'cf', role: 'img', 'aria-label': L.confusion });
  rows.forEach((r, ri) => {
    const tot = m[r].reduce((a, b) => a + b, 0);
    rows.forEach((c, cj) => {
      const v = m[r][c]; const sh = tot ? v / tot : 0;
      const cls = v ? Math.min(5, 1 + Math.floor(sh * 5)) : 0;
      svg.append(s('rect', { x: cj * cs, y: ri * cs, width: cs - 1, height: cs - 1, style: `fill:var(--r${cls})`, class: r === c ? 'dia' : 'off',
        'data-tip': `${L.gold}: ${nm(r)} → ${L.pred}: ${nm(c)} · ${num(v)} ${L.of} ${num(tot)}${tot ? ` (${pct(sh)})` : ''}` }));
    });
  });
  return h('div', { class: 'cfw' }, h('h3', {}, plain((UI.lang === 'fr' ? cf.title_fr : cf.title_de) || L.confusion)[0]),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 8px' }, `${L.rowsGold} · ${L.colsPred} · n ${num(cf.n)} · top-1 ${p3(cf.correct / cf.n)}`), svg);
}

// the two lanes of the shipped rule as one split bar: width = share of affairs, dark part = precision in that lane
function lanesTau(lt) {
  const L = t(), a = lt.pass_.coverage;
  const seg = (w, x, cls, lab) => h('span', { class: `lseg ${cls}`, style: `width:${w * 100}%`, tabindex: '0', 'data-tip': `${lab} · ${pct(w)} (n ${num(x.n)}) · ${L.cpY} ${p3(x.precision)} [${x.ci.join(', ')}]` },
    h('span', { class: 'lok', style: `width:${x.precision * 100}%` }));
  return h('div', { class: 'lanes' }, h('h3', {}, L.lanesT),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:4px 0 8px' }, ls().lanesPop(num(lt.pass_.n + lt.check.n))),
    h('div', { class: 'lbar' }, seg(a, lt.pass_, 'ag', L.shipped), seg(1 - a, lt.check, 'dis', L.laneCheck)),
    h('div', { class: 'llab' }, h('span', { style: `width:${a * 100}%` }, `${L.shipped} · ${pct(a)} · ${p3(lt.pass_.precision)}`),
      h('span', { style: `width:${(1 - a) * 100}%` }, h('span', { class: 'rtick' }), ` ${L.laneCheck} · ${p3(lt.check.precision)}`)),
    h('p', { class: 'tm mono dim', style: 'font-size:12px;margin:6px 0 0' }, `${L.cpY}: ${L.dark}; n ${num(lt.pass_.n + lt.check.n)} · ${lt.file}`));
}
