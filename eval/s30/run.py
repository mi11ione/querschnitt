"""S30 test (eval/PREREG-BUILD.md § S30). Model calls on build vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840 only
(Client.expect_build), max rate 0.5/s, 2 workers, list-price cap USD 2 for eval/s30/ledger.jsonl.

`python run.py topics`: per topic, the shipped topic (one adhoc.TOPIC_PROMPT generation -> adhoc.build_topic, as Neues
  Thema does) and the variant's scope (one common.SCOPE_PROMPT generation); frozen to topics.json, never regenerated.
`python run.py score`: every affair with a title begun 16-31 Mar 2026 (run_common.population), per topic:
  yn  shipped yes/no (prompts.yesno_prompt; order a, order b when 0.1 < p < 0.9; mean)            all affairs
  vf  S27 check (prompts.verify_prompt, same two-order rule)                                       yn p >= 0.5
  sc  scope check (common.scope_prompt with the generated include/exclude, same two-order rule)    yn p >= 0.5
Resumable: raw.jsonl keyed by (id, topic, step)."""
import json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from common import HERE, P, client, gen_scope, scope_prompt, two
from run_common import population, CUT
from querschnitt.adhoc import TOPIC_PROMPT, build_topic, parse_json, _clean

TOPICS = json.loads((HERE / "sentences.json").read_text())        # slug -> sentence (German), fixed in the pre-registration
c = client(HERE / "ledger.jsonl", "s30-test")


def topics():
    path = HERE / "topics.json"
    out = json.loads(path.read_text()) if path.exists() else {}
    for slug, sentence in TOPICS.items():
        if slug in out:
            continue
        ch, meta = c.chat([{"role": "user", "content": TOPIC_PROMPT.format(sentence=_clean(sentence, 400))}], max_tokens=200, logprobs=None)
        raw = (ch.get("message") or {}).get("content") or ""
        shipped = build_topic(sentence, "de", parse_json(raw), f"s30-{slug}")
        sc = gen_scope(c, sentence)
        out[slug] = dict(sentence=sentence, shipped=shipped, shipped_raw=raw, shipped_fp=meta["fp"], scope=sc["scope"],
                         scope_raw=sc["raw"], scope_fp=sc["fp"])
        path.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(slug, json.dumps(shipped["question"]["de"], ensure_ascii=False), "\n", sc["raw"], flush=True)


def score():
    T = json.loads((HERE / "topics.json").read_text())
    X = population()
    out = HERE / "raw.jsonl"
    R = {}
    if out.exists():
        for r in map(json.loads, open(out)):
            R[(r["id"], r["topic"], r["step"])] = r
    lock = threading.Lock()
    print("population", len(X), "rows", len(R), flush=True)

    def get(x, slug, step, fn):
        k = (x["id"], slug, step)
        if k not in R:
            r = dict(id=x["id"], topic=slug, step=step, **fn())
            with lock, open(out, "a") as f:
                f.write(json.dumps(r) + "\n"); R[k] = r
        return R[k]

    def one(x):
        args = (x["lang"], x["title"], x["title_long"])
        for slug, t in T.items():
            st = t["shipped"]
            yn = get(x, slug, "yn", lambda: two(c, lambda *a, order: P.yesno_prompt(st, *a, order), *args))
            if yn["p"] >= CUT:
                get(x, slug, "vf", lambda: two(c, lambda *a, order: P.verify_prompt(st, *a, order), *args))
                get(x, slug, "sc", lambda: two(c, scope_prompt, st["names"], t["scope"], *args))

    with ThreadPoolExecutor(2) as tp:
        for i, _ in enumerate(tp.map(one, X)):
            if i % 100 == 0:
                print("affairs", i, "usd", round(c.spent, 4), flush=True)
    print("done", sum(1 for _ in open(out)), "usd", round(c.spent, 4))


if __name__ == "__main__":
    {"topics": topics, "score": score}[sys.argv[1]]()
