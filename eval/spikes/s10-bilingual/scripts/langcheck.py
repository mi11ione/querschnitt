"""S10 secondary (post hoc, not pre-registered): flag items whose 'German' or 'French' title is not in that language.
(a) untranslated: titles identical after stripping enclosing [ ]; (b) stopword language guess (S6 build_sample STOP lists, de/fr)
on title + long title disagrees with the field language. Writes ../langcheck.json (sid -> flags) and prints the please-check
share on the clean subset. No model calls."""
import json, os, re, sys, math
S10 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = {'de': set('der die und das nicht ist mit für den von zu auf des ein eine wird werden im zur zum bei über'.split()),
        'fr': set('le la les et des du une un est pour dans que qui par sur au aux pas d l'.split())}
strip = lambda t: re.sub(r'^\[|\]$', '', t.strip()).strip()


def guess(t):
    w = re.findall(r"[a-zàâäéèêëïîôöùûüç]+", t.lower()); sc = {k: sum(x in s for x in w) for k, s in STOP.items()}
    return None if sc['de'] == sc['fr'] else max(sc, key=sc.get)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


S = {s['sid']: s for s in json.load(open(f'{S10}/sample.json'))}
K = {k['sid']: k for k in map(json.loads, open(f'{S10}/key.jsonl'))}
flags = {}
for sid, s in S.items():
    f = []
    if strip(s['title_de']) == strip(s['title_fr']): f.append('untranslated')
    for lg in ('de', 'fr'):
        g = guess(s[f'title_{lg}'] + ' ' + s[f'title_long_{lg}'])
        if g and g != lg: f.append(f'{lg}_field_looks_{g}')
    if f: flags[sid] = f
json.dump(flags, open(f'{S10}/langcheck.json', 'w'), indent=0)
clean = [k for sid, k in K.items() if sid not in flags]; bad = [K[sid] for sid in flags]
d = sum(not k['agree'] for k in clean)
print('flagged', len(flags), 'clean n', len(clean), 'disagree', d, round(d / len(clean), 3), wilson(d, len(clean)),
      '| flagged disagree', sum(not k['agree'] for k in bad), '/', len(bad))
for sid, f in flags.items(): print(S[sid]['body'], f, S[sid]['title_de'][:50], '|', S[sid]['title_fr'][:50])
