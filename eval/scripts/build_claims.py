"""Build eval/claims.tsv: every number in VISION-topics-v2.md §0, §1, §3, §6, §8 against its source file (read-only, no calls).

Status rules (strict; written down so anyone can re-apply them):
  OK        the written value equals the value displayed in the source file (equal digits, or the same number with fewer
            trailing zeros), or is a fixed design/event fact stated in the source.
  ROUNDED   nearest rounding of the source value that does not favour Querschnitt: an approximation marked as such
            ("≈", "about", "at least", spelled ratios like "nine in ten"), an estimated count rounded to whole affairs,
            a neutral figure, or a figure rounded against us.
  MISMATCH  differs from the source beyond rounding; or rounded in Querschnitt's favour without an approximation mark
            (our metric up, a baseline down, a time down); or written with more confidence than the source (an interval
            bound rounded inward); or the wording around the number is not what the source says.
  NOT FOUND no results file holds the number.
Kinds: pt+ (higher favours us), pt- (lower favours us: baselines, times), pt0 (neutral), lo / hi (interval bounds),
cnt (estimated count), eq (must match exactly).
Paths in the file column are relative to the repository root (the S1–S15 spikes are vendored under eval/spikes/); "../" marks a file
of the wider workspace that is not in the repository (the VISION draft, the build brief, the OPD export from `make data`).
Run: python3 -I eval/scripts/build_claims.py"""
import csv, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

EVAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(EVAL)  # repository root
sys.path.insert(0, os.path.join(os.path.dirname(EVAL), "tools"))
import claims_check as cc  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numfmt as NF  # noqa: E402

VISION = "../VISION-topics-v2.md"  # the draft these rows check (workspace, not in the repository)
I1, I2 = "eval/spikes", "eval/spikes"
S8M, S8CH, S8S, S8OP, S8L = (f"{I2}/s8-dvs/results.md", f"{I2}/s8-dvs/score_ch.json", f"{I2}/s8-dvs/score.json",
                             f"{I2}/s8-dvs/operating_points_ch.json", f"{I2}/s8-dvs/loop.json")
S9M, S9R, S9C, S9P = (f"{I2}/s9-aps/results.md", f"{I2}/s9-aps/results.json", f"{I2}/s9c-calibration/results.json",
                      f"{I2}/s9c-calibration/perlevel.json")
S10M, S10S, S10V = f"{I2}/s10-bilingual/results.md", f"{I2}/s10-bilingual/score.json", f"{I2}/s10-bilingual/secondary.txt"
S11, S12, S13M, S8B = f"{I2}/s11-anchor/anchor.json", f"{I2}/s12-evidence/results.json", f"{I2}/s13-timing/results.md", f"{I2}/s13-timing/s8b.json"
S14M, S15 = f"{I2}/s14-neutrality/results.md", f"{I2}/s15-judgecheck/results.json"
S1M, S2M, S3M, S5M = (f"{I1}/s1-runtime/results.md", f"{I1}/s2-oracles/results.md", f"{I1}/s3-accuracy/results.md",
                      f"{I1}/s5-aps/results.md")
S6M, S6S, S7M, S7S = f"{I1}/s6-cantonal/results.md", f"{I1}/s6-cantonal/score.json", f"{I1}/s7-crossfamily/results.md", f"{I1}/s7-crossfamily/score.json"
CEN = "eval/spikes/census_counts.json"
PRE = "eval/spikes/PREREG.md"
BRIEF = "../BUILD-BRIEF.md"
DECK = "eval/research/R1-parts/deck-topic-classification.md"
R1 = "eval/research/R1-opd-topics.md"
PRIOR = "eval/research/R1-parts/prior-art.md"

F = {}


def fact(fid, v, file, key, kind="eq", note="", correct="", status=""):
    F[fid] = dict(v=str(v), file=file, key=key, kind=kind, note=note, correct=correct, status=status)


# ---- corpus, runtime
fact("n33195", "33195", CEN, "begin_2025_2026", "eq")
fact("h44", "44.3", "derived", "(33,195 × 1.431 + 33,195 + 33,195) calls / 0.714 req/s = 159,500 s; 1.431 = S6 second-order share 0.431 (ideation/spikes/s6-cantonal/results.md A1 table); 0.714 = S8 P8.6", "pt-")
fact("h63", "63.3", "derived", "113,859 calls / 0.5 req/s = 227,700 s", "pt-")
fact("r0714", "0.714", S8M, "P8.6 line: '0.714 req/s overall (5,975 calls / 8,366 s)'", "eq")
fact("r05", "0.5", S3M, "line 10: 'about 0.5 requests/s at 8 workers'", "eq", status="MISMATCH",
     correct="the slowest multi-worker spike rate (0.5 req/s, S3) — S1 at 1 worker measured 0.41 req/s (≈ 77 h)",
     note="'slowest spike rate' is not true as written: S1 measured 0.41 req/s at concurrency 1 (s1-runtime/results.md line 86)")
fact("aff_day50", "50.4", "derived", f"{CEN} begin_2025 18,404 / 365 days", "cnt")
fact("parl90", "90", DECK, "line 43: 'Collects data from **90 Swiss parliaments**'", "eq")
fact("usd10", "8.9", "derived", "50 affairs × USD 0.49 / 1,000 × 365 (S5 USD 0.39 + S3 yes/no 0.037 + S12 evidence 0.051; FACTCHECK.md)", "eq",
     note="'under USD 10 a year' holds: 8.9", status="OK")
# ---- S9 (APS, human)
for fid, v, key in (("d3", "0.722", "D3 top-1"), ("d3lo", "0.698", "D3 top-1 CI"), ("d3hi", "0.745", "D3 top-1 CI"), ("d3t3", "0.875", "D3 top-3"),
                    ("d1", "0.704", "D1 top-1"), ("d1lo", "0.679", "D1 CI"), ("d1hi", "0.727", "D1 CI"), ("d1t3", "0.843", "D1 top-3"),
                    ("d0", "0.655", "D0 top-1"), ("d0lo", "0.629", "D0 CI"), ("d0hi", "0.680", "D0 CI"), ("d2", "0.634", "D2 top-1"),
                    ("kw9", "0.192", "Baselines: keyword top-1"), ("maj9", "0.080", "Baselines: majority top-1"),
                    ("dd1", "0.049", "D1 Δ top-1 vs D0"), ("dd1lo", "0.032", "D1 Δ CI"), ("dd1hi", "0.066", "D1 Δ CI"),
                    ("dd3", "0.067", "D3 Δ top-1 vs D0"), ("dd3lo", "0.049", "D3 Δ CI"), ("dd3hi", "0.085", "D3 Δ CI"),
                    ("dd2", "-0.021", "D2 Δ"), ("dd2lo", "-0.037", "D2 Δ CI"), ("dd2hi", "-0.004", "D2 Δ CI"),
                    ("n1357", "1357", "Setup: items built"), ("n1221", "1221", "subtopic n"), ("sub1", "0.521", "subtopic top-1"),
                    ("sub3", "0.677", "subtopic top-3"), ("p883", "883", "periods 2020+"), ("p446", "446", "periods 2010-19"), ("p28", "28", "periods pre-2010"),
                    ("lag", "0.610", "Lanes D0 orders agree share"), ("lagp", "0.781", "Lanes D0 agree precision"), ("ldis", "0.390", "Lanes D0 disagree share"),
                    ("ldisp", "0.458", "Lanes D0 disagree precision"), ("l3ag", "0.813", "Lanes D3 agree precision"), ("l3dis", "0.580", "Lanes D3 disagree precision"),
                    ("cp50", "0.895", "D3 coverage 50%"), ("cp70", "0.842", "D3 coverage 70%"), ("cp90", "0.765", "D3 coverage 90%"),
                    ("cov50", "0.50", "coverage 50%"), ("cov70", "0.70", "coverage 70%"), ("cov90", "0.90", "coverage 90%")):
    kind = "eq"
    if fid.endswith("lo"): kind = "lo"
    if fid.endswith("hi"): kind = "hi"
    fact(fid, v, S9M, key, kind)
fact("ch22", "22", S9P, "D1 > chapters", "eq")
fact("mf1", "0.677", S9P, "D1 > macro_F1", "eq"); fact("mf3", "0.692", S9P, "D3 > macro_F1", "eq")
for d, raw, cal in (("D0", "0.262", "0.035"), ("D1", "0.279", "0.037"), ("D3", "0.221", "0.017")):
    fact(f"ece{d}r", raw, S9C, f"{d} > ece_raw", "eq"); fact(f"ece{d}c", cal, S9C, f"{d} > ece_isotonic_crossfit", "eq")
fact("ci95", "95%", PRE, "'Intervals: Wilson (proportions), paired bootstrap 2,000 resamples' (95% intervals)", "eq")
fact("ch25", "25", f"{I2}/s9-aps/scripts/analyze.py", "docstring: 'Chapter vectors (25 = 24 APS chapters + none)'", "eq")
# ---- DVS 30 (human) and S8 (judge)
fact("n30", "30", S2M, "B. DVS list: '30 items, 30/30 matched to OPD affairs'", "eq")
fact("dvs27", "27", S8M, "'DVS recall (P8.2, all 30): Apertus 27/30 [0.744, 0.965]'", "eq")
fact("dvs27_30", "27/30", S8M, "'DVS recall (P8.2, all 30): Apertus 27/30'", "eq")
fact("dvs23", "23", S8M, "'(P8.2, begin_date in window): Apertus 23/24'", "eq"); fact("dvs24", "24", S8M, "'Apertus 23/24'", "eq")
fact("kw21", "21", S8M, "'keyword 21/30 [0.521, 0.833]'", "eq"); fact("kw21_30", "21/30", S8M, "'keyword 21/30'", "eq")
fact("j27", "27", S15, "both_Y", "eq"); fact("j27_30", "27/30", S15, "both_Y / n_dvs", "eq"); fact("j70", "70", f"{I2}/s15-judgecheck/RESULTS.md", "'+ 70 random 2026 affairs'", "eq")
fact("pop14790", "14790", S8M, "'Window affairs (begin_date 2026-01-01..2026-10-06): 14790'", "eq")
fact("sw14513", "14513", S8M, "Gold-based results / PREREG-ADDENDA S8 reporting addition; 14,790 − 277 LIE (By level table 'other 277')", "eq")
fact("c577", "577", S8M, "'census C ... N=n=577'", "eq")
fact("f376", "0.3756", S8M, "'sampling fraction 0.3756'", "pt0")
fact("n5338", "5338", S8M, "'n_R=5338'", "eq"); fact("n14212", "14212", S8M, "'N_R=14212'", "eq")
fact("n8139", "8139", S8M, "'Scored so far:     8139 order-A rows'", "eq")
fact("cut05", "0.5", PRE, "S8: 'Flag = p ≥ 0.5 (the S3/S4 cut-off, not re-fitted)'", "eq")
fact("st29", "29", f"{I1}/s4-blindcheck/results.md", "'Regex of 29 de/fr/it stems'", "eq")
fact("n464", "464", S8S, "annotators > nA", "eq")
fact("ab976", "0.976", S8S, "annotators > AB[1]", "eq"); fact("dis15", "15", S8S, "annotators > disagreements", "eq")
fact("qa81", "0.812", S8S, "annotators > AQ[2] (kappa)", "pt+"); fact("qb82", "0.824", S8S, "annotators > BQ[2] (kappa)", "pt+")
fact("j200", "200", S11, "A[1]", "eq")
fact("j79", "0.790", S11, "A[2]", "pt+"); fact("j79lo", "0.728", S11, "A[3]", "lo", correct="72.8%"); fact("j79hi", "0.841", S11, "A[4]", "hi", correct="84.1%")
fact("j790", "0.790", S11, "A[2]", "eq"); fact("j728", "0.728", S11, "A[3]", "lo"); fact("j841", "0.841", S11, "A[4]", "hi")
fact("j695", "0.695", S11, "apertus_same_items > D1 > apertus_vs_editors[2]", "eq"); fact("j720", "0.720", S11, "apertus_same_items > D3 > apertus_vs_editors[2]", "eq")
fact("aflags", "653.294", S8CH, "point > aflags", "cnt"); fact("kflags", "734.167", S8CH, "point > kflags", "cnt")
fact("aP", "0.914", S8CH, "point > aP", "pt+"); fact("aPlo", "0.876", S8CH, "ci > aP[0]", "lo"); fact("aPhi", "0.952", S8CH, "ci > aP[1]", "hi")
fact("kP", "0.753", S8CH, "point > kP", "pt-", correct="75.3%"); fact("kPlo", "0.714", S8CH, "ci > kP[0]", "lo"); fact("kPhi", "0.790", S8CH, "ci > kP[1]", "hi")
fact("aR", "0.654", S8CH, "point > aR", "pt+"); fact("aRlo", "0.486", S8CH, "ci > aR[0]", "lo"); fact("aRhi", "0.894", S8CH, "ci > aR[1]", "hi")
fact("kR", "0.605", S8CH, "point > kR", "pt-"); fact("kRlo", "0.451", S8CH, "ci > kR[0]", "lo"); fact("kRhi", "0.827", S8CH, "ci > kR[1]", "hi")
fact("dP", "0.161", S8CH, "point > aP − point > kP (0.914 − 0.753)", "pt+"); fact("dPlo", "0.122", S8CH, "ci > dP[0]", "lo"); fact("dPhi", "0.202", S8CH, "ci > dP[1]", "hi")
fact("dR", "0.049", S8CH, "point > aR − point > kR (0.654 − 0.605)", "pt+"); fact("dRlo", "0.017", S8CH, "ci > dR[0]", "lo"); fact("dRhi", "0.090", S8CH, "ci > dR[1]", "hi")
fact("qaP", "0.863", S8CH, "qwen_only > aP", "pt+"); fact("qaR", "0.811", S8CH, "qwen_only > aR", "pt+")
fact("qkP", "0.691", S8CH, "qwen_only > kP", "pt-", correct="69.1%"); fact("qkR", "0.729", S8CH, "qwen_only > kR", "pt-")
fact("pos913", "913.256", S8CH, "point > pos", "cnt"); fact("pos669", "668.987", S8CH, "ci > pos[0]", "cnt"); fact("pos1217", "1217.298", S8CH, "ci > pos[1]", "cnt")
fact("wk23", "22.9", "derived", f"{S8CH} point > pos 913.256 / 39.86 weeks (1 Jan–6 Oct 2026 = 279 days)", "cnt")
fact("wk364", "364.1", "derived", "14,513 / 39.86 weeks", "cnt")
fact("wk16", "16.4", S8OP, "0.5 > per_week", "cnt")
fact("wk15", "15.0", "derived", "16.4 × 0.914 (operating_points_ch.json 0.5 > per_week × score_ch.json point > aP)", "cnt")
fact("wk18", "18.4", "derived", "734.167 / 39.86", "cnt"); fact("wk14", "13.9", "derived", "18.4 × 0.753", "cnt")
fact("pos190", "190", S8CH, "positives > n", "eq"); fact("parl45", "45", S8CH, "positives > parliaments", "eq")
fact("lv87", "87", S8CH, "positives > by_level > cantonal", "eq"); fact("lv62", "62", S8CH, "positives > by_level > federal", "eq")
fact("lv41", "41", S8CH, "positives > by_level > communal", "eq"); fact("lg141", "141", S8CH, "positives > by_lang > de", "eq")
fact("lg35", "35", S8CH, "positives > by_lang > fr", "eq"); fact("lg14", "14", S8CH, "positives > by_lang > it", "eq")
fact("sep16", "16", S8M, "'CHE D462 (16 Sep, A only)'", "eq")
fact("lp60", "60", S8L, "PREREG P8.5 'the first 60 annotated items'", "eq"); fact("lp4", "4", PRE, "P8.5 'the 4 most similar of those 60'", "eq")
fact("lp404", "404", S8L, "n", "eq"); fact("lpF0", "0.866", S8L, "before > F1", "eq"); fact("lpF1", "0.906", S8L, "after > F1", "eq")
fact("lpd", "0.040", S8L, "dF1", "eq"); fact("lpdlo", "0.007", S8L, "dF1_ci[0]", "lo"); fact("lpdhi", "0.075", S8L, "dF1_ci[1]", "hi")
fact("lpR0", "0.826", S8L, "before > R", "eq"); fact("lpR1", "0.895", S8L, "after > R", "eq")
fact("lpP0", "0.910", S8L, "before > P (0.91)", "eq"); fact("lpP1", "0.917", S8L, "after > P", "eq")
fact("nei4", "4", S8S, "by_stratum > neither > gold_Y", "eq"); fact("nei180", "180", S8S, "by_stratum > neither > n", "eq")
fact("cut01", "0.1", S8OP, "key '0.1'", "eq"); fact("op660", "0.66", S8OP, "0.1 > R", "eq"); fact("op659", "659", S8OP, "0.1 > flags", "eq")
fact("op653", "653", S8OP, "0.5 > flags", "eq")
fact("b120", "120", S8B, "all > n", "eq"); fact("bP0", "0.896", S13M, "S8b table: title only P 0.896", "eq"); fact("bP1", "1.000", S13M, "title + text P 1.000", "eq")
fact("bR0", "0.768", S13M, "title only R 0.768", "eq"); fact("bR1", "0.679", S13M, "title + text R 0.679", "eq")
fact("n453", "453", f"{I2}/s8-dvs/key.jsonl", "464 packet items − 11 LIE (FACTCHECK.md)", "eq")
# ---- Curia, Bern, S12, S6/S7, S10, S3
fact("c200", "200", S3M, "'Headline numbers are test, n = 200' (clean pool: submitted ≥ 2024-11-06, after the BFH upload; s2-oracles line 29)", "eq")
fact("cuF", "0.654", S5M, "Q4 table V3 fused micro-F1", "eq"); fact("cuFlo", "0.623", S5M, "V3 CI", "lo"); fact("cuFhi", "0.686", S5M, "V3 CI", "hi")
fact("pool", "52408", S3M, "'drawn from 52,408 Curia-tagged affairs submitted before 2024-11-06'", "eq")
fact("e2t1", "0.865", S3M, "E2 desc, average of 2 orders: top-1 P 0.865", "eq")
fact("bfhn", "15007", PRIOR, "'15,007 German training docs'", "eq")
fact("bfhF", "0.687", S3M, "BFH Omikuji thr 0.25 micro-F1", "eq"); fact("bfhlo", "0.652", S3M, "BFH CI", "lo")
fact("bfhhi", "0.722", S3M, "BFH CI", "hi", correct="0.722 (or [0.65, 0.73] rounded outward)")
fact("bfht1", "0.855", S3M, "BFH top-1 P", "eq")
fact("cudlo", "-0.079", S5M, "'vs BFH micro **−0.079 to +0.010**'", "lo"); fact("cudhi", "0.010", S5M, "'−0.079 to +0.010'", "hi")
fact("be8", "8", S6M, "'Scheme: 8 directorates'", "eq"); fact("be200", "200", S6M, "'A2 ... (200 Grand Council affairs)'", "eq")
fact("beDE", "0.615", S6M, "Apertus, DE title", "eq"); fact("beFR", "0.645", S6M, "Apertus, FR title", "eq")
fact("bekDE", "0.520", S6M, "Keyword stems DE", "eq"); fact("bekFR", "0.495", S6M, "Keyword stems FR", "eq"); fact("bemaj", "0.175", S6M, "Majority class (BVD)", "eq")
fact("ev120", "120", S12, "support > overall > n", "eq"); fact("ev85", "0.850", S12, "support > overall > rate (0.85)", "eq")
fact("evlo", "0.775", S12, "support > overall > ci95[0] (0.7753)", "lo"); fact("evhi", "0.903", S12, "support > overall > ci95[1]", "hi")
fact("ev120_120", "120/120", S12, "substring_pass k/n", "eq")
fact("s6k", "0.952", S6S, "agreement > A_vs_B > kappa", "pt+"); fact("s6n", "153", S6S, "accuracy > all > final_top1 > strict > n", "eq")
fact("s6", "0.686", S6S, "accuracy > all > final_top1 > strict > acc", "eq"); fact("s6c", "0.726", S6S, "level=cantonal", "eq")
fact("s6m", "0.621", S6S, "level=communal", "eq"); fact("s6de", "0.672", S6S, "lang=de", "eq"); fact("s6fr", "0.708", S6S, "lang=fr", "eq")
fact("s6it", "0.684", S6S, "lang=it", "eq"); fact("s7x2", "2", S7M, "'Majority of 3 (A, B, Qwen)': two Claude runs + Qwen", "eq")
fact("s7", "0.684", S7S, "aps > apertus > (c) majority of 3 first choices > all > acc", "eq")
fact("s10n", "210", S10S, "accuracy > de > n", "eq"); fact("s10de", "0.543", S10S, "accuracy > de > p", "eq"); fact("s10fr", "0.529", S10S, "accuracy > fr > p", "eq")
fact("s10delo", "0.475", S10S, "accuracy > de > ci[0]", "lo"); fact("s10dehi", "0.609", S10S, "accuracy > de > ci[1]", "hi")
fact("s10frlo", "0.461", S10S, "accuracy > fr > ci[0]", "lo"); fact("s10frhi", "0.595", S10S, "accuracy > fr > ci[1]", "hi")
fact("s10po", "0.552", S10S, "accuracy > pooled > p", "eq"); fact("s10polo", "0.485", S10S, "pooled ci[0]", "lo"); fact("s10pohi", "0.618", S10S, "pooled ci[1]", "hi")
fact("s10ag", "0.957", S10S, "annotators > AB_agree > p", "eq"); fact("s10k", "0.954", S10S, "annotators > kappa_AB", "eq")
fact("s10t3de", "0.771", S10V, "line 1 top3", "eq"); fact("s10t3fr", "0.738", S10V, "line 2 top3", "eq"); fact("s10t3po", "0.810", S10V, "line 3 top3 (0.81)", "eq")
fact("s10d", "0.014", S10S, "paired_diff > de-fr > diff", "eq"); fact("s10dlo", "-0.043", S10S, "paired_diff > de-fr > ci[0]", "lo")
fact("s10dhi", "0.076", S10S, "paired_diff > de-fr > ci[1]", "hi")
fact("s10agr", "70.5%", S10M, "'languages agree (148, 70.5%)'", "eq"); fact("s10agacc", "0.622", S10S, "strata > languages agree > de > p", "eq")
fact("s10dis", "29.5%", S10M, "'disagree (62, 29.5%)'", "eq"); fact("s10disde", "0.355", S10S, "strata > languages disagree > de > p", "eq")
fact("s10disfr", "0.306", S10S, "strata > languages disagree > fr > p", "eq")
fact("s10w", "0.2975", S10S, "no_gold > please_check_weighted", "eq")
fact("vmed", "10.0", S10M, "'Clerk load: ... (median 10.0, mean 25.5, p90 76.7 ...) = 3.0 / 7.6 / 22.8'", "eq")
fact("vmean", "25.5", S10M, "Clerk load line", "eq"); fact("vp90", "76.7", S10M, "Clerk load line", "eq")
fact("cl3", "3.0", S10M, "Clerk load line", "eq"); fact("cl76", "7.6", S10M, "Clerk load line", "eq"); fact("cl228", "22.8", S10M, "Clerk load line", "eq")
fact("fg40", "40", S3M, "'Free generation (40 test affairs, DE)'", "eq"); fact("fg36", "36/40", S3M, "'36/40 = 90 % [77, 96]'", "eq")
fact("fg0", "0/40", S3M, "'0/40 say \"kein Thema\"'", "eq")
fact("cu28", "28", S3M, "'Curia needs 29 codes (28 labels + \"none\")'", "eq")
# ---- S14
fact("n14l", "0.017", S14M, "Summary 1: 'DE−FR is +0.017 [−0.003, +0.036]'", "eq"); fact("n14llo", "-0.003", S14M, "same", "lo"); fact("n14lhi", "0.036", S14M, "same", "hi")
fact("n14s6", "0.93", S14M, "Summary 1: 'S6: de/fr/it ... p=0.93'", "eq"); fact("n14s8P", "0.86", S14M, "Summary 1: 'S8 ... (p=0.86)'", "eq")
fact("n14s8R", "0.90", S14M, "Summary 1: 'recall p=0.90'", "eq")
fact("n14sp", "0.701", S14M, "Summary 2: 'Grüne 0.579 to SP 0.701, p=0.47'", "eq"); fact("n14gr", "0.579", S14M, "same", "eq"); fact("n14pp", "0.47", S14M, "same", "eq")
fact("n14s6p", "0.17", S14M, "Summary 2: 'S6: p=0.17'", "eq"); fact("n14s10p", "0.61", S14M, "Summary 2: 'S10: p=0.61'", "eq")
fact("svp7", "7", S14M, "Summary 2: 'SVP cell: 7/11 confirmed'", "eq"); fact("svp11", "11", S14M, "same", "eq")
fact("svpk", "7/20", S14M, "'Keyword precision dips for SVP too (7/20'", "eq"); fact("n20", "20", S14M, "'Among cells with n ≥ 20'", "eq")
fact("pg", "0.016", S14M, "'+0.016 [−0.104, +0.128]'", "eq"); fact("pglo", "-0.104", S14M, "same", "lo"); fact("pghi", "0.128", S14M, "same", "hi")
fact("lvf", "0.877", S14M, "Summary 4: federal 0.877", "eq"); fact("lvc", "0.937", S14M, "cantonal 0.937", "eq"); fact("lvm", "0.908", S14M, "communal 0.908", "eq")
fact("lvp", "0.46", S14M, "'p=0.46'", "eq"); fact("cs10", "0.91", S14M, "Summary 5: 'S10 ... p=0.91'", "eq"); fact("cs6", "0.30", S14M, "'S6 (19 cantons, all small): p=0.30'", "eq")
fact("sub792", "0.792", S14M, "Summary 3: 'Bundesrat business scores 0.792'", "eq"); fact("sub654", "0.654", S14M, "'against member motions 0.654'", "eq")
fact("subd", "0.138", S14M, "'Regierungsgeschäft − Motion is +0.138 [0.069, 0.200]'", "eq"); fact("subdlo", "0.069", S14M, "same", "lo")
fact("subdhi", "0.200", S14M, "same", "hi")
# ---- §6.5 / §8 event and plan facts
fact("bs2437", "2437", R1, "Basel-Stadt '2,437' hand-tagged motions", "eq")
fact("plan200", "200", VISION, "§6.5 plan: 'municipal slice grown to ~200' (target, not a measurement)", "eq")
fact("min5", "5", BRIEF, "'≈5 min live demo + 3 min Q&A'; finals '5 min'", "eq"); fact("min3", "3", BRIEF, "'3 min Q&A'", "eq")
fact("v9h2", "", "—", "planning estimate (§11 table, V9 '2–3 h'); no results file", "eq", status="NOT FOUND")
fact("v9h3", "", "—", "planning estimate (§11 table, V9 '2–3 h'); no results file", "eq", status="NOT FOUND")
fact("s13f50", "50", S13M, "S13 table 'first 50 decisions'", "eq")
fact("s13a", "12.607", S13M, "S13 table wolf: first 50 decisions 12.607 s", "pt-", correct="12.607 s (or 13 s)")
fact("s13b", "75.108", S13M, "S13 table hitze: first 50 decisions 75.108 s (max of the three)", "pt-", correct="75.108 s (or 76 s)")
fact("w7in10", "0.704", S9M, "D1 top-1", "pt+"); fact("w9in10", "0.914", S8CH, "point > aP", "pt+"); fact("w3in4", "0.753", S8CH, "point > kP", "pt-")
fact("p91", "0.914", S8CH, "point > aP", "pt+"); fact("p86", "0.863", S8CH, "qwen_only > aP", "pt+")
fact("about900", "913.256", S8CH, "point > pos (Swiss)", "cnt")
fact("about50", "50.4", "derived", f"{CEN} begin_2025 18,404 / 365", "cnt")

# token → fact, per VISION line (order = claims_check.extract order)
LINES = {
    6: ["n33195", "h44", "r0714", "h63", "r05"],
    8: ["n1357", "d1", "d3", "d0", "kw9", "n30", "dvs27", "kw21"],
    9: ["about900", "parl45", "p91", "kP", "p86", "qkP"],
    13: ["cu28"],
    14: ["lp60", "lpF0", "lpF1"],
    15: ["j79", "j27", "n30"],
    16: ["n33195"],
    35: ["n30"],
    37: ["pop14790", "sw14513", "c577", "f376", "n5338", "n14212", "n8139", "cut05", "st29", "n464", "ab976", "dis15", "n30", "j27", "j70",
         "j200", "ch25", "j79", "j79lo", "j79hi", "qa81", "qb82"],
    39: ["ci95", "st29"],
    41: ["aflags", "kflags"],
    42: ["aP", "aPlo", "aPhi", "kP", "kPlo", "kPhi"],
    43: ["aR", "aRlo", "aRhi", "kR", "kRlo", "kRhi"],
    44: ["dP", "dPlo", "dPhi", "dR", "dRlo", "dRhi"],
    45: ["qaP", "qaR", "qkP", "qkR"],
    46: ["n30", "dvs27", "dvs23", "dvs24", "kw21"],
    48: ["pos913", "pos669", "pos1217", "wk23", "wk364", "wk16", "wk15", "wk18", "wk14"],
    49: ["pos190", "parl45", "lv87", "lv62", "lv41", "lg141", "lg35", "lg14"],
    50: ["sep16", "st29"],
    52: ["lp60", "lp4", "lp404", "lpF0", "lpF1", "lpd", "lpdlo", "lpdhi", "lpR0", "lpR1", "lpP0", "lpP1"],
    53: ["nei4", "nei180", "cut01", "op660", "op659", "op653", "b120", "bP0", "bP1", "bR0", "bR1"],
    96: ["ci95"],
    101: ["n1357", "d3", "d3lo", "d3hi", "d3t3", "d0", "kw9", "maj9"],
    102: ["n1357", "d1", "d1lo", "d1hi", "d1t3"],
    103: ["n1221", "sub1", "sub3"],
    104: ["n30", "n30", "dvs27_30", "j27_30", "kw21_30"],
    105: ["c200", "c200", "cuF", "cuFlo", "cuFhi", "pool", "e2t1", "bfhn", "bfhF", "bfhlo", "bfhhi", "bfht1", "cudlo", "cudhi"],
    106: ["be8", "be200", "beDE", "beFR", "bekDE", "bekFR", "bemaj"],
    107: ["ev120", "ev85", "evlo", "evhi", "ev120_120"],
    108: ["j200", "j790", "j728", "j841", "j695", "j720"],
    109: ["sw14513", "n453", "aP", "aR", "kP", "kR"],
    110: ["s6k", "s6n", "s6", "s6c", "s6m", "s6de", "s6fr", "s6it", "s7x2", "s7"],
    111: ["s10n", "s10de", "s10fr"],
    112: ["fg40", "fg36", "fg0"],
    115: ["n1357", "p883", "p446", "p28"],
    117: ["ci95"],
    119: ["d0", "d0lo", "d0hi"],
    120: ["d1", "d1lo", "d1hi", "dd1", "dd1lo", "dd1hi"],
    121: ["d2", "dd2", "dd2lo", "dd2hi"],
    122: ["d3", "d3lo", "d3hi", "dd3", "dd3lo", "dd3hi"],
    123: ["mf1", "mf3", "ch22"],
    124: ["lag", "lagp", "ldis", "ldisp", "l3ag", "l3dis"],
    125: ["eceD0r", "eceD1r", "eceD3r", "eceD0c", "eceD1c", "eceD3c", "cp50", "cov50", "cp70", "cov70", "cp90", "cov90"],
    128: ["s10n", "s10ag", "s10k"],
    132: ["s10de", "s10delo", "s10dehi", "s10fr", "s10frlo", "s10frhi", "s10po", "s10polo", "s10pohi"],
    133: ["s10t3de", "s10t3fr", "s10t3po"],
    134: ["s10d", "s10dlo", "s10dhi", "s10n"],
    135: ["s10agr", "s10agacc", "s10dis", "s10disde", "s10disfr"],
    136: ["s10w", "vmed", "vmean", "vp90", "cl3", "cl76", "cl228"],
    139: ["n1357", "n14l", "n14llo", "n14lhi", "n14s6", "n14s8P", "n14s8R"],
    140: ["n14sp", "n14gr", "n14pp", "n14s6p", "n14s10p", "svp7", "svp11", "svpk", "n20", "pg", "pglo", "pghi"],
    141: ["lvf", "lvc", "lvm", "lvp"],
    142: ["cs10", "cs6", "n20"],
    143: ["sub792", "sub654", "subd", "subdlo", "subdhi"],
    146: ["bs2437", "plan200"],
    175: ["min5", "min3"],
    178: ["n30", "dvs27", "kw21", "about900", "parl45"],
    179: ["s13f50", "s13a", "s13b"],
    180: ["n1357", "d1", "d3", "d0", "kw9", "p91", "kP", "bfhF", "cuF"],
    183: ["v9h2", "v9h3", "aR", "j27_30", "j79"],
    185: ["w7in10", "w9in10", "min5", "about900"],
    188: ["parl90", "about50"],
    190: ["d1", "d3", "d0", "kw9", "sub1", "n1357"],
    191: ["w9in10", "w3in4", "about900"],
    192: ["s13f50", "s13a", "s13b"],
    193: ["beDE", "beFR", "bekDE", "bekFR"],
    195: ["usd10"],
}
# spelled-out numbers (not caught by the extractor except "x in y"); (line, written, fact or (value, file, key))
WORDS = [
    (9, "seven (data-centre affairs)", ("7", S8M, "Examples: data centres VD D029, GE D051, SH D139, VD D162, BE D093, CHE D462, CHE D298")),
    (9, "two (keyword list on the data-centre affairs)", ("2", S8M, "'5 of 7 missed by the keyword list' → keyword flags 2")),
    (37, "two runs / a third run (judge)", ("2+1", S8S, "annotators nA, nB 464; nC 15")),
    (50, "seven (data centres, judge confirms all seven)", ("7", S8M, "Examples: data centres … 7 blind-confirmed")),
    (50, "five contain none of the 29 stems", ("5", S8M, "'5 of 7 missed by the keyword list' (A only)")),
    (50, "two affairs in the Federal Assembly", ("2", S8M, "CHE D462 (16 Sep), CHE D298 (30 Sep)")),
    (101, "five APS-labelled examples", ("5", S9M, "D3: 'the 5 BM25-nearest gold affairs'")),
    (115, "Four designs", ("4", S9M, "D0, D1, D2, D3")),
    (140, "six main parties", ("6", S14M, "'Party tests run over the 6 main parties'")),
    (178, "seven data-centre affairs; flags all seven, the keyword list two", ("7; 2", S8M, "Examples line; 5 of 7 missed by keywords")),
    (191, "seven affairs; flags all seven, the keyword list two", ("7; 2", S8M, "Examples line; 5 of 7 missed by keywords")),
]

APPROX_LINES = {185}  # "(plain words; spoken numbers: 900, seven in ten, nine in ten)" lists the approximations said in §8.2
SEC = [(5, 9, "§0"), (11, 16, "§1"), (34, 53, "§3"), (95, 112, "§6.1"), (114, 125, "§6.2"), (127, 136, "§6.3"), (138, 143, "§6.4"),
       (145, 146, "§6.5"), (172, 183, "§8.1"), (185, 195, "§8.2")]


def section(ln):
    for a, b, s in SEC:
        if a <= ln <= b: return s
    return "?"


def dec(x):
    return Decimal(x.replace("−", "-").replace(",", "").replace("+", "").replace("'", ""))


def classify(tok, written_norm, f, line, approx):
    if f["status"]:
        return f["status"]
    if "/" in f["v"] or "/" in written_norm:
        return "OK" if f["v"] == written_norm else "MISMATCH"
    if written_norm.endswith("%") and not f["v"].endswith("%"):
        w = dec(written_norm[:-1]) / 100
        wd = max(0, -dec(written_norm[:-1]).as_tuple().exponent) + 2
    elif written_norm.endswith("%"):
        return "OK" if written_norm == f["v"] else "MISMATCH"
    else:
        w = dec(written_norm); wd = max(0, -w.as_tuple().exponent)
    s = dec(f["v"])
    if f["kind"] == "lo" or f["kind"] == "hi" or f["kind"].startswith("pt") or f["kind"] in ("eq", "cnt"):
        pass
    if w == s:
        return "OK"
    sd = max(0, -s.as_tuple().exponent)
    if wd >= sd:
        return "MISMATCH"
    precs = [wd] + ([p for p in (-1, -2, -3) if approx] if wd == 0 else [])
    for p in precs:
        q = s.quantize(Decimal(1).scaleb(-p), rounding=ROUND_HALF_UP) if p >= 0 else (s / Decimal(10) ** -p).quantize(Decimal(1), rounding=ROUND_HALF_UP) * Decimal(10) ** -p
        if q == w:
            break
    else:
        return "MISMATCH"
    if approx or f["kind"] in ("cnt", "pt0"):
        return "ROUNDED"
    up = w > s
    k = f["kind"]
    if k == "eq":
        return "ROUNDED"
    if (k == "pt+" and up) or (k == "pt-" and not up) or (k == "lo" and up) or (k == "hi" and not up):
        return "MISMATCH"
    return "ROUNDED"


# ---- rows not built from VISION: the build-week rows of claims.tsv (S16 …, written by hand when each result landed) are kept as they
# are; the S19 / S26 / S27 and S25 rows are generated from eval/pruefstand.json (run build_pruefstand.py first).
ADHOC = ("adhoc_new_topics", "adhoc_editor_examples", "adhoc_verification")
GEN_SECTIONS = {"S19-27", "S25"}


def adhoc_rows():
    """S19 / S26 / S27, three one-sentence topics against the blind AI judge: every per-topic block of eval/pruefstand.json → the point
    (truncated, never rounded up) and its interval bounds (outward), with the results file and key it was read from."""
    P = json.load(open(os.path.join(EVAL, "pruefstand.json"), encoding="utf-8"))
    T = {t["id"]: t for t in P["tests"]}
    rows = []

    def r(ctx, written, src, file, key, note):
        rows.append(dict(section="S19-27", line="-", written=written, context=ctx, source_value=str(src), file=file, key=key, status="OK",
                         correct="", note=note))

    def block(tid, path, b):
        at = b["at"]; v = b["value"]; ctx = (f"{tid} {path}" + (f" ({b['metric']})" if b.get("metric") else "")).replace("\t", " ")
        whole = isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) >= 2)
        if whole:
            r(ctx, NF.t(int(v)), v, at["file"], at["key"], "count" if isinstance(v, int) else "estimated count (whole affairs)")
        else:
            r(ctx, NF.t(v), v, at["file"], at["key"], "truncated, never rounded up")
        ci = b.get("ci95")
        if not ci: return
        if "Wilson" in str(b.get("ci_method", "")):
            src_ci = b.get("ci95_source")
            how = f"k = {b['k']}, n {b['n']} → Wilson 95% exact, bounds rounded outward at 3 decimals"
            for i, (fn, side) in enumerate(((NF.lo, "floored"), (NF.hi, "ceiled"))):
                note = "recomputed outward" + (f" (file stores {src_ci[i]})" if src_ci and src_ci[i] != ci[i] else " (equals the file)")
                r(f"{ctx} ci95[{i}]", fn(ci[i]), ci[i], at["file"], f"{at['key']}: {how} ({side})", note)
        else:
            cat = b.get("ci_at") or at
            for i, fn in enumerate((NF.lo, NF.hi)):
                d = 0 if whole else 3
                r(f"{ctx} ci95[{i}]", fn(ci[i], d) if d else NF.t(int(ci[i])), ci[i], cat["file"], f"{cat['key']} [{i}] ({b.get('ci_method', '')})",
                  "bootstrap percentile as stored, rounded outward")

    def walk(tid, path, o):
        if not isinstance(o, dict): return
        if "at" in o and isinstance(o.get("value"), (int, float)) and not isinstance(o.get("value"), bool):
            block(tid, path, o); return
        for k, v in o.items():
            if k != "strata": walk(tid, f"{path} > {k}" if path else k, v)

    t19 = T["adhoc_new_topics"]
    r("adhoc_new_topics population (affairs with a title begun 1 Aug–6 Oct 2026)", NF.t(t19["n"]), t19["n"], "eval/s19/results.json",
      "<topic> > strata > N, summed (equal for the three topics)", "count")
    r("adhoc_new_topics affairs checked by the judge (three packets)", NF.t(t19["n_checked"]), t19["n_checked"], "eval/s19/results.json",
      "<topic> > n_packet, summed", "count")
    j = t19["judge"]
    r("adhoc_new_topics judge run A = run B", NF.t(j["agree_AB"]), j["agree_AB"], j["at"]["file"], j["at"]["key"], "truncated, never rounded up")
    r("adhoc_new_topics tie-break run C", str(j["tie_break_C"]), j["tie_break_C"], j["tie_break_at"]["file"], "rows", "count")
    for tid in ADHOC:
        for topic, b in T[tid]["breakdowns"]["per_topic"].items():
            walk(tid, topic, b)
    return rows


def s25_rows():
    """S25, the shipped federal design held out on fresh APS-labelled affairs (gold = APS editors' chapter): every k/n block of
    eval/pruefstand.json > aps_chapter_heldout_s25 → the share (truncated, never rounded up), its Wilson bounds (outward, as stored by
    eval/s25/analyze.py and re-checked by build_pruefstand.py), k/n, n, and the lane shares as percentages (truncated); the S25b plain list
    prompting baseline and its paired difference (eval/s25b/results.json); and the S25 subtopic / hierarchical figures
    (aps_hierarchical_heldout_s25, computed after the result, not pre-registered)."""
    P = json.load(open(os.path.join(EVAL, "pruefstand.json"), encoding="utf-8"))
    t = next(x for x in P["tests"] if x["id"] == "aps_chapter_heldout_s25")
    rows = []

    def r(ctx, written, src, file, key, note):
        rows.append(dict(section="S25", line="-", written=written, context=f"S25 {ctx}".replace("\t", " "), source_value=str(src), file=file,
                         key=key, status="OK", correct="", note=note))

    def block(ctx, b, pct_of=None):
        at = b["at"]; ctx = ctx + (f" ({b['metric']})" if b.get("metric") else "")
        key = at.get("key") or f"line {at['line']}: {at['text']}"
        r(ctx, NF.t(b["value"]), b["value"], at["file"], key, "truncated, never rounded up")
        for i, (fn, side) in enumerate(((NF.lo, "floored"), (NF.hi, "ceiled"))):
            r(f"{ctx} ci95[{i}]", fn(b["ci95"][i]), b["ci95"][i], at["file"],
              f"{key}: k = {b['k']}, n {b['n']} → Wilson 95%, bounds rounded outward at 3 decimals ({side})", b.get("ci_method", ""))
        r(f"{ctx} k/n", b["kn"], b["kn"], at["file"], key, "count")
        r(f"{ctx} n", NF.t(b["n"]), b["n"], at["file"], key, "count")
        for x in ("share", "coverage"):
            if x in b:
                r(f"{ctx} {x}", NF.pct(b[x]), b[x], at["file"], f"{key} > {x}", "share of the scored affairs as a percentage, truncated")

    def point(ctx, b, signed=False):
        """a value + bootstrap interval without k/n (point truncated, bounds outward as stored)."""
        at = b["at"]; ctx = ctx + (f" ({b['metric']})" if b.get("metric") else "")
        sg = NF.signed if signed else (lambda x: x)
        r(ctx, sg(NF.t(b["value"])), b["value"], at["file"], at["key"], "truncated, never rounded up")
        for i, (fn, side) in enumerate(((NF.lo, "floored"), (NF.hi, "ceiled"))):
            r(f"{ctx} ci95[{i}]", sg(fn(b["ci95"][i])), b["ci95"][i], at["file"], f"{at['key']}: bootstrap bound, rounded outward at 3 decimals ({side})",
              b.get("ci_method") or b.get("method") or "")

    sc = t["breakdowns"]["scored"]
    r("affairs scored (fresh APS-labelled federal affairs, none missing)", NF.t(t["n"]), t["n"], sc["at"]["file"], sc["at"]["key"], "count")
    block("chapter top-1, held out", t["result"])
    rm = t["results_more"]
    block("chapter top-3", rm[0])
    for i, b in enumerate(rm[1:], 1):
        block(f"pre-fix reading {i} (amendment)", b)
        r(f"pre-fix reading {i} (amendment) as written there", NF.t(b["value"], 4), b["value"], b["at"]["file"],
          f"line {b['at']['line']}: {b['at']['text']}",
          "4 decimals as written in the amendment (truncated)")
    block("plain list prompting D0 (S25b)", t["baselines"][0])
    block("keyword baseline (S9 frozen rule)", t["baselines"][1])
    bd = t["breakdowns"]
    for k, b in bd["lanes"].items():
        if isinstance(b, dict): block(f"lane {k}", b)
    for b in bd["routing_by_p_cal"]["points"]:
        block(f"routing, recalibrated p ≥ {b['threshold']}", b)
    for c in bd["by_design"]["cells"]:
        block(f"by design {c['cell']}", c)
    cy = bd["curia_year"]
    for k in ("before_2015", "from_2015"):
        r(f"Curia year {k}", NF.t(cy[k]), cy[k], cy["at"]["file"], f"{cy['at']['key']} (years summed by build_pruefstand.py)", "count")
    gc = bd["gold_chapters"]
    r("gold chapters present", str(gc["chapters"]), gc["chapters"], gc["at"]["file"], gc["at"]["key"], "count")
    we = bd["with_examples"]
    r("affairs with examples (D4)", NF.t(we["value"]), we["value"], we["at"]["file"], we["at"]["key"], "count")
    lp = bd["list_prompting_s25b"]
    block("S25b shipped on the same affairs as D0", lp["shipped_same_affairs"])
    point("S25b paired shipped − D0", lp["paired_shipped_minus_D0"], signed=True)
    ns = lp["not_scored"]
    r("S25b affairs not scored (no second reading)", NF.t(ns["value"]), ns["value"], ns["at"]["file"], ns["at"]["key"], "count")
    # subtopic / hierarchy on the S25 items: computed after the result, NOT pre-registered (eval/s25/hierarchical.json)
    h = next(x for x in P["tests"] if x["id"] == "aps_hierarchical_heldout_s25")
    r("hierarchical: affairs with a subtopic gold among the 190 (not pre-registered)", NF.t(h["n"]), h["n"], h["result"]["at"]["file"],
      "subtopic_gold_items", "count")
    point("hierarchical, not pre-registered", h["result"])
    for b in h["results_more"]:
        if "kn" in b:
            block("hierarchical, not pre-registered", b)
        else:
            point("hierarchical, not pre-registered", b)
            if "chapters" in b:
                r("hierarchical, not pre-registered: chapters present (macro-F1)", str(b["chapters"]), b["chapters"], b["at"]["file"],
                  f"{b['at']['key']} > chapters", "count")
                r("hierarchical, not pre-registered: affairs in the macro-F1", NF.t(b["n"]), b["n"], h["sources"][0], "items", "count")
    return rows


# old workspace-relative paths (hackapertus root) -> repository-relative; applied to the file column of the kept rows (idempotent)
WS_MAP = (("bern/querschnitt/", ""), ("bern/ideation2/spikes/", "eval/spikes/"), ("bern/ideation/spikes/", "eval/spikes/"),
          ("bern/ideation2/PREREG", "eval/spikes/PREREG"), ("bern/ideation2/census_counts.json", "eval/spikes/census_counts.json"),
          ("bern/research/", "eval/research/"), ("bern/", "../"), ("spikes/", "../../spikes/"), ("loop/", "../../loop/"))


def repo_path(f):
    for a, b in WS_MAP:
        if f.startswith(a):
            return b + f[len(a):]
    return f


def main():
    L = open(os.path.join(ROOT, VISION), encoding="utf-8").read().splitlines()
    rows = []
    for ln, fids in LINES.items():
        line = L[ln - 1]
        toks = cc.extract(line)
        if len(toks) != len(fids):
            raise SystemExit(f"line {ln}: {len(toks)} tokens {[t[1] for t in toks]} vs {len(fids)} facts")
        pos = 0
        for (_, tok, nrm), fid in zip(toks, fids):
            f = F[fid]
            if " in " in tok:
                i = line.find(tok)
            else:
                i = line.find(tok, pos); pos = i + len(tok) if i >= 0 else pos
            pre = line[max(0, i - 14):i].lower() if i >= 0 else ""
            approx = bool(re.search(r"(≈|about|around|~|at least|under)\s*(usd\s*)?$", pre)) or " in " in tok or ln in APPROX_LINES
            if " in " in tok:  # spelled ratio: nearest fraction of that denominator
                a, b = (int(x) for x in nrm.split(" in "))
                s = dec(f["v"]); st = "ROUNDED" if (s * b).quantize(Decimal(1), rounding=ROUND_HALF_UP) == a else "MISMATCH"
            else:
                st = classify(tok, nrm, f, line, approx)
            ctx = line[max(0, i - 45):i + len(tok) + 25].replace("\t", " ").replace("|", "¦") if i >= 0 else ""
            note = f["note"]
            if st == "ROUNDED" and not note:
                note = "approximation marked in the text" if approx else ""
            if st == "MISMATCH" and not note:
                note = "rounded in Querschnitt's favour" if f["kind"] in ("pt+", "pt-") else (
                    "interval bound rounded inward (more confidence than the source)" if f["kind"] in ("lo", "hi") else "differs from source")
            correct = f["correct"] or (f["v"] if st == "MISMATCH" else "")
            rows.append(dict(section=section(ln), line=ln, written=tok, context=" ".join(ctx.split()), source_value=f["v"] or "—",
                             file=f["file"], key=f["key"], status=st, correct=correct, note=note))
    for ln, written, (v, file, key) in WORDS:
        rows.append(dict(section=section(ln), line=ln, written=written, context="", source_value=v, file=file, key=key, status="OK",
                         correct="", note="spelled-out number"))
    rows.sort(key=lambda r: (r["line"], r["written"] if not r["context"] else ""))
    out = os.path.join(EVAL, "claims.tsv")
    cols = ["section", "line", "written", "context", "source_value", "file", "key", "status", "correct", "note"]
    # keep the hand-written build-week rows byte for byte (raw lines: their quotes are literal); regenerate VISION and GEN_SECTIONS
    vision_secs = {s for _, _, s in SEC} | {"?"}
    kept = []
    if os.path.exists(out):
        kept = [l for l in open(out, encoding="utf-8").read().splitlines()[1:]
                if l.strip() and l.split("\t", 1)[0] not in vision_secs | GEN_SECTIONS]
        kept = ["\t".join(c[:5] + [repo_path(c[5])] + c[6:]) for c in (l.split("\t") for l in kept)]
    gen = adhoc_rows() + s25_rows()
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows)
        fh.write("".join(l + "\n" for l in kept))
        w.writerows(gen)
    from collections import Counter
    c = Counter(r["status"] for r in rows + gen)
    c.update(l.split("\t")[7] for l in kept)
    print(dict(c), "rows", len(rows) + len(kept) + len(gen), f"(VISION {len(rows)}, kept {len(kept)}, S19-27 + S25 generated {len(gen)})")
    for r in rows:
        if r["status"] in ("MISMATCH", "NOT FOUND"):
            print(f"{r['section']} L{r['line']} {r['status']}: {r['written']!r} source {r['source_value']} -> {r['correct']} | {r['note']}")


if __name__ == "__main__":
    main()
