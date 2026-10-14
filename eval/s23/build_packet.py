"""S23 (eval/PREREG-BUILD.md, "S23 evidence on production rows"): 200 evidence rows of the corpus run → blind packet + key.
No model calls, no network. Read-only on runs/ and data/.

Sampling frame (as registered): evidence rows (step "ev") of runs/ev/dd237840-20261014/ev.jsonl and, if present,
runs/main/dd237840-20261014/ev.jsonl, of affairs begun in 2026 (inputs `date`), with a stored quote (ok and non-empty quote).
Kind: "chapter" = the row's topic name is an APS chapter name (the shipped chapter the run asked evidence for);
"digitalisierung" = the topic name is "Digitalisierung" (the run writes those only for flagged or please-check rows).
One row per (affair, kind); if both run folders hold one, the later row (ts) is used.
Draw: rng = random.Random(20261023); 100 affairs from the id-sorted chapter frame (rng.sample), then 100 from the id-sorted
Digitalisierung frame (rng.sample, same rng); the 200 items are then shuffled with the same rng and numbered E001…E200.
An affair may appear once per kind (two separate items).
Substring check (code): the inputs row's field (`title`, `title_long`, `text`) sliced at the stored [start, end) equals the
stored quote. The input hash the run saw (`ih`) is compared with the current inputs `input_hash`; a mismatch means the
affair's text changed after the row was written (the excerpt shown is the current one, the quote is the stored one).
Writes eval/s23/packet/{GUIDE.md, items.txt, ann_TEMPLATE.tsv} and eval/s23/key.jsonl (outside the packet).
Run: querschnitt/.venv/bin/python querschnitt/eval/s23/build_packet.py"""
import gzip, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                   # querschnitt/
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.scheme import APS  # noqa: E402

RUN_FILES = [ROOT / "runs/ev/dd237840-20261014/ev.jsonl", ROOT / "runs/main/dd237840-20261014/ev.jsonl"]
INPUTS = ROOT.parent / "data/inputs.jsonl.gz"
SEED, N_PER_KIND = 20261023, 100
CHAPTERS = set(APS.names["de"][:24])
DIG = "Digitalisierung"
LEVEL_DE = {"federal": "Bund", "cantonal": "Kanton", "communal": "Gemeinde/Stadt"}


def main():
    used = [p for p in RUN_FILES if p.exists()]
    ev = {}
    n_rows = 0
    for p in used:
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if r.get("step") != "ev": continue
            n_rows += 1
            if not (r.get("ok") and r.get("quote")): continue
            kind = "digitalisierung" if r["name"] == DIG else "chapter" if r["name"] in CHAPTERS else None
            if kind is None: continue
            k = (r["aid"], kind)
            if k not in ev or r.get("ts", 0) > ev[k].get("ts", 0):
                ev[k] = dict(r, src=str(p.relative_to(ROOT)))
    aids = {a for a, _ in ev}
    inp = {}
    with gzip.open(INPUTS, "rt", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line)
            if x["id"] in aids: inp[x["id"]] = x
    frame = {kind: sorted(a for (a, k) in ev if k == kind and a in inp and (inp[a].get("date") or "")[:4] == "2026")
             for kind in ("chapter", "digitalisierung")}
    rng = random.Random(SEED)
    pick = [(a, "chapter") for a in rng.sample(frame["chapter"], N_PER_KIND)]
    pick += [(a, "digitalisierung") for a in rng.sample(frame["digitalisierung"], N_PER_KIND)]
    rng.shuffle(pick)

    D = HERE / "packet"; D.mkdir(parents=True, exist_ok=True)
    items, keys = [], []
    for i, (aid, kind) in enumerate(pick, 1):
        r, x = ev[(aid, kind)], inp[aid]
        pid = f"E{i:03d}"
        hay = x.get(r["field"]) or ""
        sub_ok = hay[r["start"]:r["end"]] == r["quote"]
        parts = dict(P.evidence_parts(x))
        lvl = LEVEL_DE.get(x.get("level"), x.get("level") or "-")
        block = [f"=== {pid} ===", f"Parlament: {x.get('parl') or '-'} ({lvl}{', ' + x['canton'] if x.get('canton') else ''})",
                 f"Typ: {x.get('type') or x.get('type_h') or '-'}", "", f"Titel: {x['title']}"]
        if "title_long" in parts:
            block.append(f"Langtitel: {parts['title_long']}")
        block.append(f"Text (Anfang): {parts['text']}" if "text" in parts else "Text: (kein Text, nur Titel)")
        block += ["", f"Vorgeschlagenes Thema: {r['name']}", f"Zitierter Satz: «{r['quote']}»", ""]
        items.append("\n".join(block))
        keys.append(dict(pid=pid, aid=aid, kind=kind, name=r["name"], field=r["field"], start=r["start"], end=r["end"],
                         quote=r["quote"], k=r.get("k"), p=r.get("p"), substring_ok=sub_ok, ih_run=r.get("ih"),
                         ih_now=x.get("input_hash"), ih_match=r.get("ih") == x.get("input_hash"), lang=x.get("lang"),
                         level=x.get("level"), body=x.get("body"), date=x.get("date"), fp=(r.get("meta") or {}).get("fp"),
                         row_pid=r["pid"], src=r["src"]))
    (D / "items.txt").write_text("\n".join(items), encoding="utf-8")
    (D / "ann_TEMPLATE.tsv").write_text("".join(f"{k['pid']}\t\n" for k in sorted(keys, key=lambda k: k["pid"])), encoding="utf-8")
    with open(HERE / "key.jsonl", "w", encoding="utf-8") as f:
        for k in keys: f.write(json.dumps(k, ensure_ascii=False) + "\n")
    (D / "GUIDE.md").write_text(GUIDE.format(n=len(keys)), encoding="utf-8")
    summary = dict(run_files=[str(p.relative_to(ROOT)) for p in used], ev_rows=n_rows, frame={k: len(v) for k, v in frame.items()},
                   packet=len(keys), by_kind={kd: sum(k["kind"] == kd for k in keys) for kd in ("chapter", "digitalisierung")},
                   distinct_affairs=len({k["aid"] for k in keys}), substring_ok=sum(k["substring_ok"] for k in keys),
                   ih_match=sum(k["ih_match"] for k in keys),
                   by_level={lv: sum(k["level"] == lv for k in keys) for lv in sorted({k["level"] for k in keys})},
                   by_lang={lg: sum(k["lang"] == lg for k in keys) for lg in sorted({k["lang"] for k in keys})},
                   by_field={fd: sum(k["field"] == fd for k in keys) for fd in ("title", "title_long", "text")}, seed=SEED)
    (HERE / "packet_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


GUIDE = """# Annotation guide: does the quoted sentence support the proposed topic?

You get {n} parliamentary affairs from Swiss parliaments (federal, cantonal and municipal; begun in 2026), in German, French
or Italian. Each block in `items.txt` shows:

- an opaque id (`E001` …; the ids are shuffled and say nothing about the affair),
- the parliament and the affair type,
- the affair text: title, long title (if any, first 400 characters) and the first 1,500 characters of the text (some affairs
  have a title only),
- a **proposed topic**: either one chapter of the Année Politique Suisse (APS) scheme (e.g. «Landwirtschaft»,
  «Sozialversicherungen») or the topic «Digitalisierung» (digitalisation),
- a **quoted sentence** taken from the affair (title, long title or text).

## Task
For each affair, answer **Y** if the quoted sentence, read on its own, gives a reason to say that the affair concerns the
proposed topic. Answer **N** otherwise.

Judge the sentence, not the topic. The question is not "is this the best topic for the affair?" but "does this sentence, by
itself, point to this topic?". Use the affair text only to understand what the sentence refers to (e.g. what "diese
Massnahme" means).

- **Y**: the sentence names or clearly describes subject matter that belongs to the proposed topic (e.g. a sentence about
  nitrogen losses from farming for «Landwirtschaft»; a sentence asking for changes to the Criminal Code for «Rechtsordnung»;
  a sentence about an online portal or electronic records for «Digitalisierung»).
- **N**: the sentence is generic or procedural and would fit almost any affair ("Der Bundesrat wird beauftragt, einen
  Bericht vorzulegen.", "Il Municipio è invitato a rispondere alle seguenti domande."), or it is about a different subject
  than the proposed topic, or it is a fragment (letterhead, names, dates, addresses) that carries no topical content.
- If the proposed topic looks wrong for the affair but the quoted sentence nevertheless points to it, answer Y. If the topic
  looks right but the sentence gives no reason for it, answer N.
- When in doubt, ask: would a reader who sees only this sentence and the topic name find the sentence a reason for the
  topic? If not clearly, answer N.

Judge only from the text shown; do not look anything up.

## Output
Copy `ann_TEMPLATE.tsv` to `ann_A.tsv` (first annotator), `ann_B.tsv` (second annotator) or `ann_C.tsv` (tie-break
annotator, only the ids listed in `ann_C_TEMPLATE.tsv`) and save it in the folder you are told to use, one line per id,
tab-separated:

```
E001\tY
E002\tN
```

Exactly `Y` or `N` in the second column, one line per id, every id answered. Work independently: do not compare answers
with other annotators, and do not open `key.jsonl` or any file outside `packet/`.
"""

if __name__ == "__main__":
    main()
