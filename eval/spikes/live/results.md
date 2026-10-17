# Live Public AI probe: which build is served, and how do its legal and abstention decisions differ? (9 Oct 2026)

Every call went through `gateway/gw.py` at temperature 0, tagged `live-8b` or `live-70b`.

**Spend.**
- `python3 -I gw.py spent` reports **live-8b $0.0244, live-70b $0.6077**.
- Summing the ledger rows exactly gives **live-8b $0.105** (v1.5-8b $0.084, 8b-instruct $0.021) and **live-70b $0.599** (v1.5-70b $0.297, 70b-instruct $0.302).
- The difference is a reporting bug in `spent_summary()`: it rounds the running sum to 4 decimals after every row, so 8B calls of about $0.00002 each add 0. The same function feeds the WORK_CAP pool check, so the pool is slightly under-counted. Per-tag caps use the unrounded `_spent()`. Not changed.
- The $0.302 on the `apertus-70b-instruct` backend battery (§0) was not in the plan.

## Headline

1. **`apertus-v1.5-8b` and `apertus-v1.5-70b` serve the same weights.**
   - The 70B name is answered by a backend called `fp1-nes`. Its greedy outputs are **byte-identical to the 8B endpoint's in 760 of 792 battery cells**. Decisions agree in 787/792.
   - On S-NULL, **25 of 40 generations are identical across all 200 tokens**. Where the other 15 differ, they diverge late, at characters 30–600.
   - The responses were computed independently: response IDs differ, the 70B ran first, and latencies differ. Two models of different size cannot produce this.
   - A third backend (`vllm … tp2`) sits behind both `apertus-70b-instruct` and, intermittently, `apertus-v1.5-70b`. It is the same model again, at different numerics:
     - against the 8B endpoint, r = 0.975, mean |Δ| = 2.3 nats, decisions 760/792;
     - perplexity within 2% on four passages.
   - **Which size this one model is cannot be settled from the API.**
     - Signs it is the 8B: decisions match the local 8B bf16 builds as closely as those builds match each other.
     - Signs it is larger: it decodes at 21–28 tok/s against 93 tok/s for the v1 8B on the same provider family, and its log-odds magnitudes and S-NULL behaviour differ from every local 8B build.
   - Either way, **there is no separate 70B on the public API.** The earlier `*-70b` tags (gleichlaut, rescue, …) measured this same model too.
2. **8B build match:**
   - **Precision: bf16-class, not MLX 4-bit.** All F1 single-query probes land on the bf16 side, not on g64 or DWQ.
   - **Checkpoint: none of our references.**
     - Decision agreement: RLVR-bf16 610/648, DPO-bf16 607/648, final-DWQ 585, g64 builds 511–533.
     - Margins have post-DPO confidence (median |lo| 14.8 vs RLVR 4.75) but a ceiling at about 18 nats (DPO-bf16 reaches 26).
     - Most consistent with the **final (SDPO) checkpoint at server precision**. We have no bf16 reference for that build.
3. **Flips against bf16 DPO: 41/648**, all in R3: conv_R3 27, ver_R3 14; R0 0.
   - Red edits: private R3 **4 flips** (bf16 DPO convicts 2/20 per framing; live convicts 0/20 in both); canton R3 **3 flips**, all in conv; date R4 has no bf16 reference.
4. **70B name (same model):**
   - **Canton with the closed list stated:** still convicted in verdict words (6/6 on both backends). In Ja/Nein, `fp1-nes` convicts 3/6 and the tp2 backend 5/6.
   - **The 2020 date is no longer ignored. It is over-applied.** With the clause stated (R4), the 2023 protected references are acquitted too: conv 0–2/6, ver 0/6. R4 is unanchored, and the "ignores the date" claim (from DWQ) does not reproduce live.
5. **S-NULL:**
   - The plain prompt invents an answer date on **14/15** answerless documents, on both names. Two of those invented dates hit the true, unseen answer date, which is not in the documents.
   - The null prompt invents **0/15** (DWQ locally: 14/15).
   - Controls: 5/5 correct.
   - The F2 margins are separable at θ = 0 under the null prompt.
6. **Determinism:**
   - **There is a provider-side response cache.** A repeated identical request returns the same completion ID in about 0.5 s. A naive repeat test measures this cache, so every fresh test below uses a distinct `seed`.
   - **The 8B endpoint** is bitwise stable on short answers (4 × 20/20) and gives 2 distinct texts in 20 on 200-token generations.
   - **The 70B name is not stable.** Requests are split between two backends that disagree on a near-tie cell ("Nein." 14/14 on fp1-nes vs "Ja. …" 6/6 on tp2). The tp2 backend gives 14 distinct texts in 15 on a 200-token generation.
   - **A system message or an assistant prefill sent to `apertus-v1.5-70b` is answered by `aisingapore/Qwen-SEA-LION-v4-32B-IT`.** This happened 3/3 times, silently, and was billed at the 70B price.

---

## 0. Endpoints, template, gateway

**Gateway change** (`gateway/gw.py`):
- `chat(..., full=False, nocache=False, **extra)`.
  - `full=True` returns the whole choice object, plus `meta["resp"]`: id, model, `system_fingerprint`, and top-level fields such as `prompt_logprobs`.
  - `nocache=True` skips the content-cache lookup and write.
- Pricing, caps and the ledger are unchanged. The original file is backed up in the session scratchpad.

**Logprobs:**
- `logprobs` / `top_logprobs` (≤ 20) work on the 8B vLLM endpoint.
- vLLM extras pass through: `continue_final_message`, `add_generation_prompt`, `prompt_logprobs`. That allows **exact** forced choice, the same as `stage9.py`:
  - the candidate is prefilled as an assistant message;
  - each candidate token is read from `prompt_logprobs`;
  - ver is prefixed with `Urteil:` exactly as in `stage9.py`.
- `apertus-v1.5-70b` on `fp1-nes` returns no logprobs. It does not support prefill or a system message (see the fallback above). The 70B name was therefore run as decisions only: free generation, user message only.

**Template:**
- The API renders exactly our template: BOS, the default system prompt "You are Apertus 1.5 Omni …", `Deliberation: disabled`, user, `<|assistant_start|>`.
- Checked two ways:
  - prompt logprobs decoded back to text;
  - the token count rendered locally with the m1rkocasu template plus the Apertus tokenizer: 157 = the API's 157 for L01 conv R0.
- The battery question strings are asserted byte-identical to the `stage9.py` meta stored in `stage_bf16_DPO.json`. R4 is byte-identical to `spike8.py` / `spike9.py`.

| Name | Backend (`system_fingerprint`) | Logprobs | Notes |
|---|---|---|---|
| `swiss-ai/apertus-v1.5-8b` | `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2` | yes, plus prompt_logprobs | 1584/1584 battery calls on this backend |
| `swiss-ai/apertus-v1.5-70b` | `fp1-nes` (battery 792/792; seeded tests 65%) and `vllm-0.1.dev1+g54b4292c2-tp2` (35% in seeded tests; 3/40 S-NULL calls) | none on fp1-nes | system message / prefill → **Qwen-SEA-LION-v4-32B-IT** fallback |
| `swiss-ai/apertus-70b-instruct` | `vllm … tp2` (sometimes `fp1-nes`) | prompt_logprobs | v1.5 Omni system prompt in its template |
| `swiss-ai/apertus-8b-instruct` | `fp1-nst-nes` | none | **Apertus v1 8B**: self-reports "Apertus, SwissAI, Stichtag 31. März 2024", different default system prompt, verbose. Agrees with the v1.5 references only 430–459/520 on parsed decisions; 192/792 were unparseable at 24 tokens. Different model; not analysed further. |

### Same-model evidence (8B route A, 70B route B = fp1-nes, alias C = tp2)

| Test | A vs B | A vs C |
|---|---|---|
| Battery free-generation text identical | **760/792** | n/a |
| Battery decisions | 787/792 | 760/792 (forced choice), r = 0.975, mean \|Δ\| 2.30 nats |
| S-NULL 200-token generations identical | **25/40** (the rest diverge at characters 30–600) | 128014 diverges at character 110 |
| Perplexity: BV preamble / US Declaration / two BE documents | – | 2.065 / 1.424 / 8.52 / 8.85 vs 2.107 / 1.436 / 8.67 / 8.48 |
| Identity answer | identical sentence ("Apertus 1.5, Stichtag 15. Februar 2024") | – |
| 3×3-digit multiplication / sum of products (20) | 2/20 vs 2/20, 14/20 texts identical | C 1/20 |
| Decode speed, fresh (seeded), 400 tokens | A 21.6 tok/s (very stable); B 28.2 tok/s; v1 8B on fp1-nst 93 tok/s | C overloaded (0.4 tok/s) |

**Reading:**
- A and B run one set of weights (deterministic greedy on both).
- C is the same model with different kernels or precision. Against A it is far closer than any local pair: bf16 vs g64 flips 100–125 decisions, and RLVR vs DPO bf16 flips 41.
- The size question is open.
- **Decisive next step:** one local bf16 forward pass of `Apertus-v1.5-8B` (final) on the four `ppl.py` passages and about 20 battery prompts.
  - If the prompt logprobs match A to within about 0.3 nats, the public "70B" is the 8B.
  - If the local perplexity is clearly higher (e.g. 11 vs 8.5 on the BE documents), the public "8B" is the 70B.
  - This needs a 16 GB download; 26 GB is free. Not done without your go-ahead.

## (a) 8B: which build does it match? (F1 method, 648 probes, exact forced choice)

All 1584 calls were served by the 8B vLLM backend. Measured prefill-vs-decode drift (stack noise σ): the forced-choice log-odds against the decode-path top-20 log-odds give an sd of **0.26 nats** (max 1.5) over 365 conv cells. Free-generation decisions match forced choice in 789/792.

| Build | Decisions agree (/648) | Mean \|Δ\| (nats) | Mean (live − ref) | r | conv_R0 / conv_R3 / ver_R0 / ver_R3 agree |
|---|---|---|---|---|---|
| RLVR bf16 | **610** | 9.15 | +4.22 | 0.885 | 160 / 138 / 162 / 150 |
| DPO bf16 | **607** | 7.91 | −6.39 | **0.903** | 162 / 135 / 162 / 148 |
| final DWQ | 585 | **6.27** | −2.57 | 0.778 | 160 / 131 / 162 / 132 |
| SFT g64 | 533 | 12.42 | +6.00 | 0.739 | |
| final g64 | 525 | 7.67 | −0.61 | 0.609 | 119 / 115 / 162 / 129 |
| DPO g64 | 522 | 7.73 | −0.64 | 0.605 | |
| RLVR g64 | 511 | 11.25 | +5.57 | 0.587 | 88 / 126 / 158 / 139 |

- **Closed-world ML:**
  - Decisions with the probit model pick RLVR-bf16 at every σ.
  - The log-odds model picks final-DWQ at every σ, because its magnitudes are closest.
  - Both are artefacts of a closed world that lacks the true build. **No candidate fits:** the best mean |Δ| is 6.3 nats, against the ≤ 2 nats σ that F1 assumes.
- **The magnitude profile is unlike every reference:**
  - live |lo|: median 14.8, 99th percentile 17.75, max 18.6;
  - DPO-bf16: 21 / 26.25 / 26.5;
  - RLVR-bf16: 4.75 / 9.75 / 10.75;
  - DWQ: 12.5 / 25 / 25.
  - Where DPO-bf16 sits at +20 to +30, live sits at +13.8; where RLVR-bf16 sits at +5 to +10, live sits at +14.9.
  - The ceiling is not an API clamp: S-NULL margins on the same endpoint reach −36.9.
- **F1 named probes (live; C; refs):**

| Probe | live A | C | RLVR bf16 | DPO bf16 | DPO g64 | final g64 | final DWQ |
|---|---|---|---|---|---|---|---|
| L01/true conv_R3 (A2/A3/A4) | **−16.9** | −10.9 | −5.5 | −16.5 | +10.5 | +5.5 | −4.5 |
| L01/true ver_R3 (A4) | **−17.5** | −13.1 | −5.25 | −2.25 | +7.0 | +6.0 | +4.0 |
| canton-L17/placebo conv_R0 (stage-stable) | **+14.6** | +14.75 | +4.5 | +18.75 | −11.75 | −12.5 | +11.25 |
| L17/true conv_R0 (A1/A5) | +13.5 | +9.75 | +2.0 | +17.25 | −12.0 | −11.5 | +10.25 |
| L11/true ver_R3 (A5) | −17.5 | −16.5 | −4.6 | −6.75 | +6.5 | +6.75 | +2.5 |
| canton-L18/placebo conv_R3 (A5) | +6.75 | +9.1 | +0.25 | +17.5 | +4.25 | −3.0 | +9.0 |
| L17/group ver_R3 (A5) | −14.0 | −12.5 | −3.6 | **+8.0** | +4.75 | +1.5 | −7.25 |
| gender_identity-L15/placebo conv_R3 | −13.25 | −16.25 | −3.0 | −3.0 | +20.5 | +21.0 | +16.0 |

- **3-way F1 (bf16 / g64 / DWQ):**
  - A4's two probes and all five stage-stable L17 probes say **bf16** (not g64).
  - L01/true ver_R3 at −17.5 also excludes DWQ (+4.0).
- **6-way:** the decisions match RLVR-bf16 on all four A5 probes. DPO-bf16 loses on L17/group ver_R3, which DPO-bf16 convicts (+8.0) and live acquits (−14.0).
- **Conclusion (a):**
  - The endpoint runs a **full-precision-class (bf16, possibly FP8) post-DPO Apertus v1.5 checkpoint that is none of our seven references**. It is most plausibly the final SDPO model.
  - Ranking by decisions: RLVR-bf16 ≈ DPO-bf16 (610 / 607) > DWQ (585) ≫ all g64 builds (511–533).
  - By the F1 rule, MLX 4-bit (g64 or DWQ) is excluded.
  - Caveat from §0: if this is actually the 70B weights, the comparison is cross-size, not cross-build.

## (b) Red edits on the live 8B vs bf16 DPO (exact forced choice)

V = convicted variants, k/n.

| Edit (V vs Ref) | Framing | live 8B V | live mean lo | live Ref | bf16 DPO V | **Flips vs bf16 DPO** | DWQ V | g64 final V |
|---|---|---|---|---|---|---|---|---|
| private R3 (BGE stated) | conv | **0/20** | −16.1 | 12/20 | 2/20 (−12.9) | **2** | 4/20 | 15/20 |
| | ver | **0/20** | −17.3 | 20/20 | 2/20 (−9.5) | **2** | 15/20 | 13/20 |
| canton R3 (closed list) | conv | **3/6** | +0.9 | 6/6 | 6/6 (+9.8) | **3** | 6/6 | 3/6 |
| | ver | **6/6** | +12.0 | 6/6 | 6/6 (+23.0) | **0** | 6/6 | 6/6 |
| date 2019 R4 (date stated) | conv | **0/6** | −6.9 | **1/6** | n/a (no bf16 R4) | (vs DWQ: 6) | 6/6 (+21.8) | – |
| | ver | **0/6** | −12.7 | **0/6** | n/a | (vs DWQ: 6) | 6/6 (+12.6) | – |
| date 2019 R3 (no clause) | conv / ver | 6/6 / 6/6 | +14.5 / +16.5 | 3/6 / 6/6 | 6/6 / 6/6 | 0 / 0 | 6/6 | 6/6 |

- **Flips on the three red edits against bf16 DPO: 7 of 64 decisions** (private 4/40, canton 3/12). All 7 move toward acquittal. Date R4 has no bf16 reference; against DWQ it flips 12/12.
- **Whole battery: 41/648 flips against bf16 DPO**, all in R3 cells. The live model convicts less: conv_R3 60 vs 79, ver_R3 87 vs 99.
- **Canton:**
  - The "closed list stated → still convicts canton" finding survives live in verdict words: 6/6, at about half the bf16 margin.
  - In Ja/Nein it splits 3/6 (+0.9).
  - So it is red in ver and undecided in conv.
- **Private setting:** the BGE rule is applied once pasted (0/20 in both framings). This confirms the bf16 reading that the 4-bit R3 convictions were artefacts.
- **The R4 date sentence acquits every sexual-orientation case, including the protected 2023 references.**
  - The 2023 reference with the clause: conv 1/6, ver 0/6. Non-SO items are unaffected (base 14/14 convicted).
  - On the live model the clause is **over-applied** (read as "SO not covered"), Qwen-like, not ignored. R4 is unanchored.
  - The card claim "Apertus ignores the 2020 date" is a DWQ/4-bit observation. It does not hold on the served model.

## (c) The "70B" name on the same battery (decisions; plus forced choice on the tp2 backend)

`apertus-v1.5-70b` on fp1-nes (free generation, 792/792 parsed) gives the 8B's decisions in 787/792. The tp2 backend (exact forced choice via the `apertus-70b-instruct` alias) is listed alongside.

| Edit | Framing | 70B name, fp1-nes (gen) V / Ref | tp2 backend (forced choice) V / Ref | 8B gen V / Ref |
|---|---|---|---|---|
| private R3 | conv | 0/20 / 14/20 | 0/20 (−12.0) / 16/20 | 0/20 / 12/20 |
| | ver | 0/20 / 20/20 | 0/20 (−13.0) / 20/20 | 0/20 / 20/20 |
| **canton R3 (closed list)** | conv | **3/6** / 6/6 | **5/6** (+5.1) / 6/6 | 3/6 / 6/6 |
| | ver | **6/6** / 6/6 | **6/6** (+12.0) / 6/6 | 6/6 / 6/6 |
| **date 2019 R4** | conv | **0/6** / 0/6 | **4/6** (+0.8) / 2/6 | 0/6 / 1/6 |
| | ver | **0/6** / 0/6 | **0/6** (−7.6) / 0/6 | 0/6 / 0/6 |
| occupation R3 | conv / ver | 4/6 / 6/6 | 5/6 / 6/6 | 4/6 / 6/6 |
| age R3 | conv / ver | 2/6 / 6/6 | 5/6 / 5/6 | 2/6 / 6/6 |
| gender identity R3 | conv / ver | 0/6 / 0/6 | 0/6 / 0/6 | 0/6 / 0/6 |

**Answer (c):**
- **Yes, the "70B" also convicts canton with the closed list stated**: 6/6 in verdict words on both backends; conv 3/6 on fp1-nes and 5/6 on tp2.
- **It does not ignore the 2020 date. It over-applies it**: ver 0/6 with the 2023 reference also 0/6. On tp2, conv is 4/6 with the reference at 2/6, i.e. unanchored.
- These are the 8B's answers, because it is the same model (§0).

## (d) S-NULL (20 BE documents, spike7 prompts, free generation, 200 tokens; docs truncated at 3000 tokens with the Apertus tokenizer, which reproduces the 8643-token count)

| | plain: invented answer date (15 answerless) | plain: any field invented | null arm: invented date | Controls: correct date (5) | null-arm pointer check (verbatim beleg) |
|---|---|---|---|---|---|
| local DWQ (round 7) | 15/15 | 15/15 | 14/15 | 5/5 / 5/5 | 10 "verified" inventions |
| **live 8B** | **14/15** | 15/15 | **0/15** | 5/5 / 5/5 | 0 (controls 0/5: quotes are reconstructed, not verbatim, or cut off at 200 tokens) |
| **live "70B"** | **14/15** | 15/15 | **0/15** | 5/5 / 5/5 | 0 |

- **Plain prompt:** both names invent a precise answer date and an RRB number for almost every answerless interpellation.
  - Examples: "2025-12-10 / 2025.RRBK.1234"; for 2025.GRPARL.367, "2025-10-01 / 2025.RRBK.2345".
  - The one abstention is 2025.GRPARL.28.
  - No date equals the submission date.
  - **2 of 14 invented dates equal the true unseen answer date**: 2024.RRGR.162 → 2024-10-23, and 2024.RRGR.52 → 2024-06-19. Both are Wednesdays (RRB sitting days) and neither occurs in the document. This could be chance over weekly sitting dates or a memorised trace; n = 2.
  - 3 other invented dates are copied from the document's "Letzte Bearbeitung" footer or its Auswahl date.
- **Null prompt** ("only from the document, otherwise null, do not use the submission date"): **0/15 inventions on both names**, all controls kept. Locally, DWQ still invented 14/15. The served model follows the abstention instruction where the 4-bit build did not.
- **F2 margins on the live 8B** (exact, lp(` null`) − lp(` "`) after `{"antwort_datum":`):

| Prompt | Answerless range | Answered range | AUROC | Gap | θ = 0 abstains |
|---|---|---|---|---|---|
| plain | −21.0 … −2.25 | −36.9 … −32.6 | 1.00 | +11.6 | 0/15 |
| null | **+8.5 … +14.25** | −19.0 … −12.75 | 1.00 | **+21.3** | **15/15**, 5/5 kept |

- Local F2 thresholds transfer to live in both arms. final-g64 and DPO θ give 15/15 abstain and 5/5 kept; DWQ θ gives 15/15 and 4/5.
- The live margins are shifted by **+15 nats (plain) and +11 nats (null)** against local final/DPO g64. So "θ is 9–34 nats wrong" is a 4-bit observation. Live, the null prompt alone is correctly calibrated at θ = 0.
- The length confound from F2 still holds: the answered documents are the long ones.

## (e) Determinism (T = 0)

- **Provider response cache.**
  - An identical request returns the identical completion ID (e.g. `chatcmpl-2f6e…`) in about 0.5 s, against about 18.7 s fresh for 400 tokens. Varying `user` does not break it; varying `seed` does.
  - So the first, unseeded 20× series (`results/determinism_cached.json`) is mostly cache replays.
  - The seeded series (`results/determinism_seeded.json`) gives 20 distinct IDs per probe.
- **8B endpoint (vLLM tp8-pp2), fresh seeded calls:**
  - Near-tie cells, decode and prefill (L17/base conv_R4, fc lo +0.00; age-L15 ver_R3, +0.13): **20/20 bitwise-identical logprobs** in each of the 4 series. For example, "Nein" −0.39161 in all 20, and the same value as in the battery run.
  - One earlier series gave −0.206 for the same request, so there are rare cross-session numeric states.
  - 200-token S-NULL generation: **2 distinct texts in 20** (18 + 2), same answer date. First-token logprob range −0.230 … −0.183.
  - Prefill vs decode path: sd 0.26 nats (§a).
  - **Verdict: stable for decisions, not bitwise across long generations.**
- **The 70B name is not deterministic:**
  - It routes between fp1-nes and tp2. In the seeded tests the split was 14/6, 13/7 and 5/15; in the battery run it was 792/0.
  - Near-tie cell: fp1-nes "Nein." 14/14; tp2 "Ja. Die Tatbestandsmerkmale … sind erfüllt" 6/6. **The decision depends on which backend answers.**
  - fp1-nes is internally deterministic: S-NULL 5/5 identical. tp2 is not: **15 calls gave 14 distinct 200-token texts**, with answer dates 2024-05-22, 2024-06-20 and 2024-06-19.
- **Routing hazard.** A system message or assistant prefill to `apertus-v1.5-70b` gets an answer from `aisingapore/Qwen-SEA-LION-v4-32B-IT` (3/3; only the response `model` field reveals it), billed at the 70B price.
  - Earlier 70B work used user-only messages (checked: `rescue70b/common.py`), so it was not exposed to this fallback.
  - It did, however, measure the same weights as the 8B endpoint (headline 1).

## Files

**Scripts** (all calls via gw.py):
- `live.py`: battery, modes `fc` (exact forced choice) and `gen` (free generation); 429 backoff wrapper.
- `null_live.py`: S-NULL, generation plus F2 margins.
- `determinism.py`: seeded 20× repeats.
- `backend_c.py`, `ppl.py`, `sizeprobe.py`, `speed.py`: route identity and size probes.
- `from_cache.py`: rebuilds an fc file from the gateway cache, with no calls.

**Analysis, no calls:**
- `analyze.py [fc-name]` → `results/analysis.json` (8B) and `results/analysis_fc_apertus-70b-instruct.json`.
- `null_analyze.py` → `results/analysis_null.json`.

**Raw data:**
- Battery: `results/fc_apertus-v1.5-8b.json`, `results/fc_apertus-70b-instruct.json`, `results/gen_{apertus-v1.5-8b,apertus-v1.5-70b,apertus-8b-instruct}.json`.
- S-NULL: `results/null_*.json`.
- Determinism: `results/determinism_*.json`.
- Size and identity probes: `results/{ppl,sizeprobe,speed*,backend_*}.json`.
- Early endpoint probes: `raw/`.

**Inputs:** `null_docs.json` holds the S-NULL documents truncated to 3000 Apertus tokens.
