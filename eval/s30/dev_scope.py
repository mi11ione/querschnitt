"""S30 dev: one scope generation request per dev topic (the S19 topics; sentence = name + its S13 scope words). Frozen to dev_scopes.json."""
import json, re
from common import HERE, client, gen_scope
from querschnitt.scheme import adhoc
c = client(HERE / "ledger.jsonl", "s30-dev")
out = {}
for slug in ("wolf", "hitze", "ki-schule"):
    t = adhoc(slug)
    m = re.search(r"»\s*\((.*)\)\?$", t["question"]["de"])
    sentence = f"{t['names']['de']}: {m.group(1)}"
    g = gen_scope(c, sentence)
    out[slug] = dict(sentence=sentence, names=t["names"], **g)
    print(slug, sentence, "\n", g["raw"], "\n")
(HERE / "dev_scopes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
