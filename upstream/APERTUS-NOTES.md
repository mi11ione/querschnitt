# Apertus in a closed-choice classifier: measured behaviour

For the swiss-ai evaluation work. Measured while building Querschnitt (topic classification of Swiss parliamentary
affairs, October 2026) on Public AI's route `swiss-ai/apertus-v1.5-8b`, build
`vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840` on every classification call cited here (S9: 0 off-build rows among
its five phases of 1,357 calls each). The route name does not fix the size: on the same 250 MMLU questions the route's
model scored 211/250 against 177/250 for `apertus-8b-instruct` (v1 8B), and the working conclusion was that it serves
the 70B (`loop/learnings.md`). Read every figure below as "the model behind that route and build".

Readout throughout: the user message lists codes, the assistant turn is prefilled with the opening of a JSON answer, and
the next-token log-probabilities of the code tokens are read (`max_tokens` 1, `top_logprobs` 20, temperature 0, no system
message). Paths are relative to the hackapertus working tree; S-numbers are the spikes there.

| Behaviour | Measured | n | Source |
|---|---|---|---|
| Free naming leaves the scheme | asked to name a topic without a list, 36/40 answers fell outside both the Curia 28 and the APS label sets, and 0/40 said "no topic"; with the Curia list shown, 0/40 fell outside it | 40 | `bern/ideation/spikes/s3-accuracy/results.md` (S3, free generation) |
| Codes are single tokens; the readout needs no log-probabilities for top-1 | the generated token equalled the top-1 code on 110 of 110 calls | 110 | `bern/ideation/spikes/s1-runtime/results.md` (S1) |
| Raw probability is over-confident; isotonic recalibration per build fixes it | expected calibration error of the top-1 confidence 0.2791 → 0.0319 (chapter read back from the subtopic) and 0.2416 → 0.0574 (with labelled examples), 2-fold cross-fitted | 1,357 | `bern/querschnitt/eval/s16/results.md` (S16) |
| Position and code bias; two code orders handle it | the top-1 of identity and permuted code order agreed on 189/300 (63.0%); codes after Z were penalised. On the APS task the two orders agree on 61.0% of affairs, with precision 0.781 there and 0.458 where they differ; Querschnitt uses codes A–Y only, averages two orders, and routes disagreement to a person | 300; 1,357 | `bern/ideation/spikes/s3-accuracy/results.md` (S3 E2); `bern/ideation2/spikes/s9-aps/results.md` (S9, lanes) |
| Labelled examples help | five APS-labelled similar affairs in the prompt: top-1 +0.067 [+0.049, +0.085] over plain list prompting; reading the chapter back from the chosen subtopic adds +0.018 [+0.002, +0.034] on top of the examples | 1,357 | `bern/ideation2/spikes/s9-aps/results.md` (S9 D3); `bern/querschnitt/eval/s16/results.md` (S16 D4 − D3) |
| German and French: no measurable gap | same federal affairs scored from the German and the French text: +0.017 [−0.003, +0.036] for German; bilingual cantonal titles: +0.014 [−0.043, +0.076]. Per item the language still matters: German and French titles of the same affair get the same chapter in 70.5% | 1,357; 210 | `bern/ideation2/spikes/s14-neutrality/results.md` (S14); `bern/ideation2/spikes/s10-bilingual/score.json`, `results.md` (S10) |
| Deterministic within a build, for decisions | fresh seeded calls on near-tie cells: 20/20 bitwise-identical log-probabilities in each of four series; long generations are not bitwise stable (2 distinct 200-token texts in 20). Re-sending 20 identical S5 payloads on the same build: p within 0.001 on 16/20, top-1 equal on 19/20 | 20 per series; 20 | `spikes/live/results.md` §(e); `bern/ideation2/spikes/s9-aps/results.md` (reuse check) |
| Provider response cache | an identical request returns the identical completion id in about half a second; a distinct `seed` gives a fresh call. Repeat tests must vary the seed | — | `spikes/live/results.md` §(e) |
| The `-70b` route answers with another model when sent a system message or a prefill | a system message or an assistant prefill sent to `swiss-ai/apertus-v1.5-70b` was answered by `aisingapore/Qwen-SEA-LION-v4-32B-IT` 3/3 times; in a pre-registered battery, 127/384 system-prompt requests were not served by Apertus against 0/32 without one. Only the response `model` field shows it | 3; 384 + 32 | `spikes/live/results.md` §6; `spikes/subst/results.md` |
| The `-70b` route name is not deterministic across its backends | requests were split between two backends that disagreed on a near-tie cell (14/14 one answer on one backend, 6/6 the other answer on the other) | 20 | `spikes/live/results.md` §(e) |

## What follows for an evaluation harness

- Ask for closed choices and read the code distribution; free naming measures something else.
- Report calibration next to accuracy, and refit any probability threshold per served build.
- Average at least two code orders, and keep the order-disagreement share as a quality signal.
- Record `model` and `system_fingerprint` of every response, lock one build per result, and vary the seed in repeat tests.
- On Public AI, send prefills and system messages to the `-8b` route name only, and check the response `model` field.

The task in `eval-task/` packages the first four as a re-runnable evaluation for any Apertus build.
