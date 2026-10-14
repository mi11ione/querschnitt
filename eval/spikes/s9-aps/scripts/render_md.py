"""results.json + verify_s5.json -> results.md (tables only from computed numbers; static notes below)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s9lib import HERE
R = json.load(open(f'{HERE}/results.json')); V = json.load(open(f'{HERE}/verify_s5.json'))
STATUS = sys.argv[1] if len(sys.argv) > 1 else 'interim'
f = lambda x: '—' if x is None else (f'{x:.3f}' if isinstance(x, float) else str(x))
ci = lambda c: f'[{c[0]:.3f}, {c[1]:.3f}]' if c and c[0] == c[0] else '[—]'
sg = lambda x: f'{x:+.3f}'
L = []
A = L.append
A(f'# S9: APS extended held-out (federal), status: {STATUS}\n')
A(f"Generated {R['generated_utc']} by `scripts/analyze.py` + `scripts/render_md.py`; numbers in `results.json`. Tags `bern2-s9-*`, "
  f"spend **USD {R['spend_total_usd']:.4f}** (pai.py ledger, list price; cap 5.00): " + ', '.join(f'{k} {v:.4f}' for k, v in sorted(R['spend_usd'].items())) + '.\n')
A('## Setup')
A(f"- **Set:** APS process captures joined to OPD CHE by Curia number in the slug (S2 method), ideation-1 298 pages and their affairs excluded. "
  f"Items built so far: {R['data']['items']} (periods {R['data']['period']}; join {R['data']['join']}; {R['data']['chapters_present']} of 24 chapters present; "
  f"main subtopic among the 190: {R['data']['sub_gold']}). Curia DE text on {R['data']['de_text']}, FR text on {R['data']['fr_text']}.")
A('- **Route/build:** `swiss-ai/apertus-v1.5-8b` via ideation2 `lib/pai.py`, S5 request shape (no system message, JSON-key prefill, `continue_final_message`, `max_tokens=1`, `top_logprobs=20`).')
A('  Rows by phase/model/fingerprint: ' + '; '.join(f"{b['phase']} {b['n']}× {b['fp']}" for b in R['builds']) + f". Off-build rows: {R['offbuild_rows']}.")
A(f"  Min code mass in top-20 per phase: {R['min_mass']}. Mean prompt tokens per call: {R['pt_mean']}.")
A(f"- **Reuse check (20 of the ideation-1 297, identity order):** payload bytes POSTed by pai equal S5's payload for **{V['bytes_equal']}/20**; "
  f"p reproduces S5 raw q1a within 1e-3 for **{V['within_1e3']}/20** (max abs diff {V['max_diff']:.4f}; top-1 equal {V.get('top1_equal')}/20), same fingerprint `{V['fps'][0]}`. "
  "The 4 deviating items show serving-side numerical drift on identical bytes and build (not a code difference); the one top-1 flip is a near tie (0.47 vs 0.53).")
A(f"- **n per design** (items with all calls of that design): {R['n']}.\n")
A('## Primary: chapter accuracy and paired difference vs D0 (H9.1–H9.3)')
A('| Design | n | top-1 [95% CI] | top-3 [CI] | D0 top-1 same items | Δ top-1 vs D0 [paired 95%] | Δ top-3 [paired] | gain/loss | wins |')
A('|---|---|---|---|---|---|---|---|---|')
for d in ('D0', 'D1', 'D2', 'D3'):
    b = R['chapter'][d]
    if not b.get('n'): A(f'| {d} | 0 | TO MEASURE | | | | | | |'); continue
    if d == 'D0':
        A(f"| D0 (v14: L1 (c), 2 orders, geo) | {b['n']} | {f(b['top1'])} {ci(b['top1_ci'])} | {f(b['top3'])} {ci(b['top3_ci'])} | — | — | — | — | — |")
    else:
        A(f"| {d} | {b['n']} | {f(b['top1'])} {ci(b['top1_ci'])} | {f(b['top3'])} {ci(b['top3_ci'])} | {f(b['D0_top1_same_items'])} | "
          f"{sg(b['diff_top1'])} {ci(b['diff_top1_ci'])} | {sg(b['diff_top3'])} {ci(b['diff_top3_ci'])} | {b['flips']['gain']}/{b['flips']['loss']} | {'yes' if b['wins'] else 'no'} |")
A(f"\nWinners (paired interval excludes 0, positive): {R['winners'] or 'none'}. Best Δ among D1–D3: {R['best_design']}.")
c = R['chapter_all_designs_common']
A(f"On the {c['D0']['n']} items with all four designs: " + '; '.join(f"{d} top-1 {f(c[d].get('top1'))}" for d in c) + '.\n')
b = R['baselines']
A('## Baselines (same items as D0)')
A(f"- Majority chapter ({b['majority_chapter']}): top-1 {f(b['majority_top1'])} {ci(b['majority_ci'])}, n = {b['n']}.")
A(f"- Keyword (APS subtopic-name content words ≥5 chars, DE; `data/keywords_frozen.json`, frozen {b['keyword_frozen_utc']} before any scoring, sha256 {b['keyword_file_sha256'][:12]}…): "
  f"top-1 {f(b['keyword_top1'])} {ci(b['keyword_ci'])}, n = {b['n']}; {b['keyword_zero_match']} items with no keyword match (→ majority).\n")
A('## Subtopic end to end (main subtopic among the 190)')
A(f"Gold chapter inside the D1 shortlist: {R['subtopic_gold_chapter_in_shortlist']['k']}/{R['subtopic_gold_chapter_in_shortlist']['n']} = {f(R['subtopic_gold_chapter_in_shortlist']['share'])} {ci(R['subtopic_gold_chapter_in_shortlist']['ci'])} (all D1 items).\n")
A('| Pipeline | n | subtopic top-1 [CI] | subtopic top-3 [CI] |'); A('|---|---|---|---|')
for k, v in R['subtopic'].items():
    A(f"| {k} | {v['n']} | {f(v['top1'])} {ci(v['top1_ci'])} | {f(v['top3'])} {ci(v['top3_ci'])} |")
A('\n## Strata (chapter top-1)')
for d, S in R['strata'].items():
    A(f'\n**{d}**\n\n| Stratum | n | top-1 [CI] | top-3 [CI] |\n|---|---|---|---|')
    for k, v in S.items():
        A(f"| {k} | {v['n']} | {f(v.get('top1'))} {ci(v.get('top1_ci'))} | {f(v.get('top3'))} {ci(v.get('top3_ci'))} |")
A('\n## Lanes (D0 identity vs permuted order top-1 agree / disagree)')
A('| Design | lane | n | share [CI] | precision [CI] |'); A('|---|---|---|---|---|')
for d, S in R['lanes'].items():
    for k, v in S.items():
        A(f"| {d} | {k} | {v['n']} | {f(v['share'])} {ci(v['share_ci'])} | {f(v['precision'])} {ci(v['ci'])} |")
A('\n## Reliability (top-1 confidence, 10 equal-width bins) and coverage–precision')
for d, X in R['reliability'].items():
    A(f"\n**{d}**: ECE = {X['ece']:.4f}\n\n| p bin | n | mean p | accuracy [CI] |\n|---|---|---|---|")
    for r in X['bins']:
        A(f"| {r['bin']} | {r['n']} | {f(r.get('mean_p'))} | {f(r.get('acc'))} {ci(r.get('ci')) if r['n'] else ''} |")
    A('\n| coverage | n | p threshold | precision [CI] |\n|---|---|---|---|')
    for r in X['coverage_precision']:
        A(f"| {r['coverage']:.0%} | {r['n']} | {r['threshold_p']:.3f} | {f(r['precision'])} {ci(r['ci'])} |")
A('\n## Exploratory')
A(f"- D1 × D2 combination: {R['exploratory_D1xD2'] if isinstance(R['exploratory_D1xD2'], str) else json.dumps(R['exploratory_D1xD2'])}")
A(open(f'{HERE}/scripts/notes.md').read())
open(f'{HERE}/results.md', 'w').write('\n'.join(L) + '\n')
print('results.md written')
