"""S33 (eval/PREREG-BUILD.md): the 927 S25 held-out federal affairs read from the French text, with the design production runs
for a French federal affair today (engine.ch1_prompt shows examples only for German federal text: D1 read-back, French frame).

    python eval/s33/run.py build   # French inputs -> eval/s33/inputs_fr.jsonl.gz + eval/s33/inputs_counts.json (no calls)
    python eval/s33/run.py run     # the batch runner (production code path) into runs/s33, lock pre-written to the S25 build

French input per affair, from OPD's bulk export (../data/opd-new): title_fr, title_long_fr (cleaned as data.py does), and the
French text of the affair's own OPD text row in production's federal order (data.CHE_ORDER: «Texte déposé» first), first
1,500 characters, used only where it differs from the German text of the same row; otherwise title (+ long title) only.
No attached documents. The other fields are those of the production (German) input row; lang = text_lang = "fr".
Resumable: the batch runner skips every prompt id already in runs/s33."""
import collections, gzip, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import data as D  # noqa: E402

BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
OPD = ROOT.parent / "data/opd-new"
INP = HERE / "inputs_fr.jsonl.gz"
OUT = ROOT / "runs/s33"


def fr_text(rows):
    """Production's text-row choice (data.texts_index filters + data.pick_text_rows for body CHE), French rows only."""
    own = []
    for r in rows:
        ty, t = (r.get("type_fr") or r.get("type_de") or ""), r.get("text_fr")
        if not t or D.REPLY_TYPE.match(ty) or ty.lower().startswith("titel des gesch") or not D.OWN_TEXT.match(ty):
            continue
        c = D.clean(t)
        if len(c) >= 40:
            own.append((ty, "fr", c, r["id"], D.clean(r.get("text_de"))))
    x = D.pick_text_rows(own, "fr", "CHE")
    return x


def build():
    ids = {int(x) for x in (ROOT / "eval/s25/ids.txt").read_text().split()}
    A = {a["id"]: a for a in D.rows(OPD / "affairs.ndjson.gz") if a["id"] in ids}
    T = collections.defaultdict(list)
    for r in D.rows(OPD / "texts/texts_CHE.ndjson.gz"):
        if r["affair_id"] in ids:
            T[r["affair_id"]].append(r)
    base = {x["id"]: x for x in D.rows(ROOT.parent / "data/inputs.jsonl.gz") if x["id"] in ids}
    assert set(A) == set(base) == ids, (len(A), len(base), len(ids))
    c = collections.Counter()
    with gzip.open(INP, "wt") as f:
        for o in sorted(ids):
            a, b = A[o], base[o]
            title = D.clean(a.get("title_fr"))
            assert title, f"{o}: no French title"
            tlong = D.clean(a.get("title_long_fr"))
            tr = fr_text(T.get(o, []))
            text, src = "", None
            if tr and tr[2] != tr[4]:
                text, src = tr[2][:1500], f"text:{tr[3]}"
            elif tr:
                c["fr_text_equal_to_german"] += 1
            x = dict(b, lang="fr", text_lang="fr", title=title, title_long=tlong, text=text, text_src=src,
                     text_kind="text" if text else None, type=a.get("type_name_fr") or b["type"],
                     alt_lang="de", title_alt=D.clean(a.get("title_de")), title_long_alt=D.clean(a.get("title_long_de")))
            x["input_hash"] = D.input_hash(x)
            c["affairs"] += 1; c["with_french_text" if text else "french_title_only"] += 1
            c["with_french_long_title"] += bool(tlong and tlong != title)
            c["title_only_and_german_had_document_text"] += (not text) and b.get("text_kind") == "doc"
            c["title_only_and_german_had_no_text"] += (not text) and not b.get("text")
            c["already_french_in_production"] += b["lang"] == "fr"
            c["identical_to_production_input"] += x["input_hash"] == b["input_hash"]
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    (HERE / "inputs_counts.json").write_text(json.dumps(dict(sorted(c.items())), indent=1))
    print(json.dumps(dict(sorted(c.items())), indent=1))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    st = OUT / "state.json"
    if not st.exists():   # the lock is written before the first call: a call served by any other build stops the run
        st.write_text(json.dumps({"lock": dict(model="swiss-ai/apertus-v1.5-8b", fp=BUILD, key="dd237840-s33",
                                               first_seen="(pre-written)", note="S33: locked before the first call to the "
                                               "S25 build (runs/s25)")}, indent=1))
    lock = json.loads(st.read_text())["lock"]
    assert lock["fp"] == BUILD and not lock.get("mode"), lock
    (OUT / lock["key"]).mkdir(exist_ok=True)   # Store.lock_build makes it only when it writes the lock itself (the first
    # launch, 16 Oct 11:33, lacked this line: its 25 calls were answered, logged in the ledger, and their rows not written)
    from querschnitt.batch import main
    main(["run", "--inputs", str(INP), "--out", str(OUT), "--ids", str(ROOT / "eval/s25/ids.txt"), "--steps", "ch", "sub",
          "--topics", "--conc", "2", "--max-rate", "0.6", "--cap", "0.5"])


if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
