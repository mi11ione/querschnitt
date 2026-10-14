"""Keyword baseline, frozen BEFORE any scoring: for each APS chapter, the set of content words (>= 5 chars, lowercased, DE)
of its APS subtopic names (s1lib.SUBS, 190 names). Decision rule (also frozen here): for an affair, count per chapter the
number of distinct keywords occurring as a substring of lowercase(title + ' ' + title_long + ' ' + text) [DE, the same
fields the model sees]; predict the chapter with most matches; ties (incl. all-zero) -> the tied chapter most frequent in the
S9 gold (majority order)."""
import json, os, re, sys, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s9lib import SUBS, CH_DE, DATA
STOPW = {"zwischen", "andere", "anderer", "sowie", "allgemeiner"}
kw = {}
for c in range(24):
    ws = set()
    for s in SUBS[c]:
        for w in re.findall(r"[^\W\d_]+", s.lower()):
            if len(w) >= 5 and w not in STOPW: ws.add(w)
    kw[c] = sorted(ws)
doc = dict(frozen_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), rule=__doc__, stopwords=sorted(STOPW),
           chapters={str(c): dict(name=CH_DE[c], keywords=kw[c]) for c in range(24)})
p = f"{DATA}/keywords_frozen.json"
assert not os.path.exists(p), "already frozen"
s = json.dumps(doc, ensure_ascii=False, indent=1); open(p, "w").write(s)
open(p + ".sha256", "w").write(hashlib.sha256(s.encode()).hexdigest() + "\n")
print(sum(len(v) for v in kw.values()), "keywords"); print({CH_DE[c]: len(v) for c, v in kw.items()})
