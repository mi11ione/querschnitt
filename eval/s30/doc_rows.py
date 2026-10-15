"""S30: the PRUEFSTAND §15 paragraph and its eval/claims.tsv rows, both from eval/s30/results.json (no model calls).
Usage: python eval/s30/doc_rows.py  -> prints the Markdown block; appends claims rows for S30 (once)."""
import json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
R = json.loads((HERE / "results.json").read_text())
SRC = "eval/s30/results.json"; L = "../eval/s30/results.json"
rows = []
f3 = lambda v: f"{v:.3f}".replace("-", "−")


def claim(written, ctx, val, key, note="truncated, never rounded up"):
    rows.append(["S30", "-", written.replace("−", "-"), ctx, str(val), SRC, key, "OK", "", note])
    return f"[{written}]({L})"


def num(v, ctx, key):
    return claim(f3(v), ctx, v, key)


def ci(c, ctx, key):
    a = claim(f3(c[0]), ctx + " ci95[0]", c[0], key + " [0]", "bounds rounded outward in analyze.py")
    b = claim(f3(c[1]), ctx + " ci95[1]", c[1], key + " [1]", "bounds rounded outward in analyze.py")
    return a, b


def prec(t, arm):
    p = R[t][arm]["precision"]; ctx = f"S30 {t} > {arm} precision of flags"
    v = num(p["value"], ctx, f"{t} > {arm} > precision > value") if p["value"] is not None else "–"
    a, b = ci(p["ci"], ctx, f"{t} > {arm} > precision > ci")
    k = claim(str(p["k"]), ctx + " k", p["k"], f"{t} > {arm} > precision > k", "count")
    n = claim(str(p["n"]), ctx + " n", p["n"], f"{t} > {arm} > precision > n", "count")
    return f"{v} [{a}, {b}] ({k}/{n})"


def rec(t, arm):
    r = R[t][arm]["recall_weighted"]; ctx = f"S30 {t} > {arm} weighted recall"
    if r["value"] is None: return "–"
    v = num(r["value"], ctx, f"{t} > {arm} > recall_weighted > value")
    a, b = ci(r["ci"], ctx, f"{t} > {arm} > recall_weighted > ci")
    return f"{v} [{a}, {b}]"


def diff(t, m):
    d = R[t][f"diff_variant_minus_shipped_{m}"]; ctx = f"S30 {t} > paired difference (scope check − shipped) {m}"
    v = claim(("+" if d["value"] > 0 else "") + f3(d["value"]) if d["value"] != 0 else "0.000", ctx, d["value"], f"{t} > diff_variant_minus_shipped_{m} > value")
    a, b = ci(d["ci"], ctx, f"{t} > diff_variant_minus_shipped_{m} > ci")
    return f"{v} [{a}, {b}]"


def kwp(t):
    p = R[t]["kw"]["precision"]
    return num(p["value"], f"S30 {t} > keyword precision", f"{t} > kw > precision > value")


def kwr(t):
    return num(R[t]["kw"]["recall_weighted"]["value"], f"S30 {t} > keyword weighted recall", f"{t} > kw > recall_weighted > value")


names = {"licht": "light pollution", "drohnen": "drones", "pestizide": "pesticides", "pooled": "all three"}
lines = ["| S30, agreement with the AI judge, held out | judge positives | flags shipped / with scope check | precision shipped | precision with scope check | Δ precision, paired | recall shipped | recall with scope check | Δ recall, paired | keyword list: precision / recall (points) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
for t in ("licht", "drohnen", "pestizide", "pooled"):
    jp = claim(str(R[t]["judge_pos_items"]), f"S30 {t} judge positives", R[t]["judge_pos_items"], f"{t} > judge_pos_items", "count")
    fs = claim(str(R[t]["shipped"]["flags"]), f"S30 {t} shipped flags", R[t]["shipped"]["flags"], f"{t} > shipped > flags", "count")
    fv = claim(str(R[t]["variant"]["flags"]), f"S30 {t} scope-check flags", R[t]["variant"]["flags"], f"{t} > variant > flags", "count")
    lines.append(f"| {names[t]} | {jp} | {fs} / {fv} | {prec(t, 'shipped')} | **{prec(t, 'variant')}** | {diff(t, 'P')} | {rec(t, 'shipped')} | {rec(t, 'variant')} | {diff(t, 'R')} | {kwp(t)} / {kwr(t)} |")
pop = claim("1,316", "S30 population (affairs with a title begun 16–31 Mar 2026)", 1316, "licht > strata > neither > N + any > N", "count")
pk = claim(str(sum(R[t]["n_items"] for t in ("licht", "drohnen", "pestizide"))), "S30 judged items", R["pooled"]["n_items"], "pooled > n_items", "count")
ag = claim(f"{R['agree_AB']:.3f}", "S30 judge run A = run B", R["agree_AB"], "agree_AB")
nc = claim(str(R["n_C"]), "S30 tie-breaks", R["n_C"], "n_C", "count")
r120 = claim("120", "S30 random unflagged per topic", 120, "licht > strata > neither > n", "count")
z = claim("0", "S30 judge positives among random unflagged", 0, "<topic> > strata > neither > judge_Y", "count")
md = f"""
**A generated scope as a third question on the flags (S30, held out).** Dev on the S19 packets (four variants, [PREREG-BUILD.md § S30](../eval/PREREG-BUILD.md)) chose: one more plain generation request per topic writes an include and an exclude list in de/fr/it from the user's sentence, and every flag is asked «Gehört das folgende parlamentarische Geschäft zum Thema «…»?» with those lists (plus «affairs whose title does not show the topic» as an exclusion); a flag stays confirmed only if the S27 question and this one both say yes. Test: three new one-sentence topics (light pollution, drones, pesticides; [`eval/s30/sentences.json`](../eval/s30/sentences.json)), every affair with a title begun 16–31 Mar 2026 ({pop}), keywords frozen before the run ([`eval/s30/keywords_frozen.json`](../eval/s30/keywords_frozen.json)). Checked: every affair any arm or keyword flagged plus {r120} random others per topic ({pk} in all), title, long title and the start of the text, blind Claude judge A (shuffled) and B (reversed), run A = run B {ag}, {nc} tie-breaks; judge positives among the random others {z} in each topic. Shipped = the product before S30 (yes/no, kept by the S27 question); recall weighted to the population (stratified bootstrap 2,000).

{chr(10).join(lines)}

Reading: pooled over the three topics the scope check raises precision of the confirmed flags (interval above 0) and loses two judge positives (pesticides: veterinary insecticides, pests and plant diseases); recall can only fall, since the scope check asks only on flags the shipped design already confirms, and the recall interval reaches 0. The pre-registered rule (pooled precision interval above 0, no recall interval below 0) is met, so the product asks it for new topics (`prompts.scope_check_prompt`, `adhoc.SCOPE_PROMPT`); flags it does not confirm go to `please check`, not away. Light pollution and drones hold 4 and 2 judge positives, too few to read per topic. The frozen keyword lists are more precise on these topics. Topic files without the lists (Digitalisierung, the S19 topics) are unchanged.
"""
print(md)
if "--write" in __import__("sys").argv:
    with open(ROOT / "eval/claims.tsv", "a") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")
    (HERE / "pruefstand_s30.md").write_text(md)
    print("claims rows", len(rows))
