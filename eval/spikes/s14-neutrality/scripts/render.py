"""results.json -> results_tables.md (tables only; results.md = header + summary written by hand + these tables)."""
import json, os
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(f'{H}/results.json'))
f3 = lambda x: '–' if x is None else f'{x:.3f}'
ci = lambda c: f'[{f3(c[0])}, {f3(c[1])}]'
out = []

def table(title, mets, labels, weighted=False):
    cells = []
    for c in mets[0]['cells']:
        if c['cell'] not in cells: cells.append(c['cell'])
    for D in mets[1:]:
        for c in D['cells']:
            if c['cell'] not in cells: cells.append(c['cell'])
    out.append(f'\n**{title}**\n')
    out.append('| cell | ' + ' | '.join(labels) + ' |'); out.append('|---|' + '---|' * len(labels))
    for g in cells:
        row = []
        for D in mets:
            c = next((x for x in D['cells'] if x['cell'] == g), None)
            if c is None: row.append('–'); continue
            sm = ' small' if c['small'] else ''
            if weighted: row.append(f"{f3(c['p_w'])} {ci(c['ci_w'])} n={c['n']}{sm} (unw. {c['k']}/{c['n']})")
            else: row.append(f"{f3(c['p'])} {ci(c['ci'])} n={c['n']}{sm}")
        out.append(f'| {g} | ' + ' | '.join(row) + ' |')
    ov = []
    for D in mets:
        o = D['overall']; ov.append((f"{f3(o['p_w'])} (unw. {o['k']}/{o['n']})" if weighted else f"{f3(o['p'])} {ci(o['ci'])} n={o['n']}"))
    out.append('| *all* | ' + ' | '.join(ov) + ' |')
    tr = []
    for D in mets:
        t = D['test']; s = f"perm p={t['p_perm']}" + (f", χ² p={t['p_chi2']}" if t.get('p_chi2') is not None else '') + f" (df {t['df']}; {len(t['cells_tested'])} cells)"
        tr.append(s)
    out.append('| *test* | ' + ' | '.join(tr) + ' |')
    gr = []
    for D in mets:
        g = D['gap']
        gr.append('–' if not g else f"{g['hi']} − {g['lo']} = {g['diff']:+.3f} {ci(g['ci'])}" + (' (small cells)' if 'small' in g['basis'] else ''))
    out.append('| *largest gap* | ' + ' | '.join(gr) + ' |')

out.append('## S9 federal (APS chapter vs APS editors, D1 top-1 recomputed from raw; keyword = frozen S9 keyword baseline)')
for dim in ('party', 'submitter kind', 'instrument'):
    v = R['S9'][dim]
    table(f'S9 by {dim}' + (' (test over the 6 main parties)' if dim == 'party' else ''), [v['D1_top1'], v['D1_top3'], v['keyword_top1']],
          ['D1 top-1', 'D1 top-3', 'keyword top-1'])
t = R['S9']['party']['D1_top1_all_categories_test']; out.append(f"\nAll 11 submitter categories (incl. Bundesrat, committees, cantons), D1 top-1: perm p={t['p_perm']}, χ² p={t['p_chi2']} (df {t['df']}).")
L = R['S9']['language (paired, same affairs; single identity-order call)']
out.append(f"\n**S9 language (paired, same {L['n']} affairs; one identity-order L1 call each: DE prompt+DE text `d0a` vs FR prompt+FR text `d2fr`)**: "
           f"DE {f3(L['DE']['p'])} {ci(L['DE']['ci'])}, FR {f3(L['FR']['p'])} {ci(L['FR']['ci'])}; DE−FR {L['diff_DE_minus_FR']:+.4f} {ci(L['diff_ci'])}; "
           f"only DE right {L['only_DE_right']}, only FR right {L['only_FR_right']}; McNemar p={L['p_mcnemar']}.")
out.append(f"\nS9 canton/region: {R['S9']['canton/region']}.")
out.append('\n## S8 digitalisation 2026 (weighted by final_weight; 95% = full-packet bootstrap within packet strata, 2,000; unweighted k/n in brackets)')
names = R['S8_metric_names']
for dim, v in R['S8'].items():
    table(f'S8 by {dim}' + (' (test over the 6 main parties)' if dim == 'party' else ''), [v['aP'], v['aR'], v['kP'], v['kR']],
          [names[m] for m in ('aP', 'aR', 'kP', 'kR')], weighted=True)
out.append('\n## S6 cantonal + communal APS (Apertus final chapter; strict gold = A and B agree, lenient = any overlap of their code sets)')
for dim, v in R['S6'].items():
    table(f'S6 by {dim}' + (' (test over the 6 main parties)' if dim == 'party' else ''), [v['strict'], v['lenient']], ['top-1 vs strict gold', 'top-1 vs lenient gold'])
out.append('\n## S10 bilingual cantons BE/FR/VS (titles only; gold = A==B else C)')
for dim in ('canton', 'shown language', 'party'):
    v = R['S10'][dim]
    table(f'S10 by {dim}' + (' (test over the 6 main parties)' if dim == 'party' else ''), [v['pooled'], v['de'], v['fr']], ['pooled DE+FR', 'DE prompt', 'FR prompt'])
P = R['S10']['prompt in original language vs the other (paired)']
out.append(f"\n**S10 prompt in the affair's shown language vs the other language (paired, n={P['n']})**: matched {f3(P['matched']['p'])} {ci(P['matched']['ci'])}, "
           f"other {f3(P['other']['p'])} {ci(P['other']['ci'])}; diff {P['diff']:+.4f} {ci(P['diff_ci'])}; McNemar p={P['p_mcnemar']}.")
open(f'{H}/results_tables.md', 'w').write('\n'.join(out) + '\n')
print(len(out), 'lines')
