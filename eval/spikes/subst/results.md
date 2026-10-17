# I5 Stille Substitution: pre-registered scale battery (ident_scale.json, 416 calls, 0 errors, Public AI apertus-v1.5-70b, 9 Oct 2026 ~18:05–19:30 UTC)
Pre-registration: prereg/I5.yaml + LOCK (2026-10-09T18:01:22Z). Classifier frozen in ident_scale.py (sha256 in LOCK).

## Endpoint substitution (served model != swiss-ai/*)
| Arm | Served by Qwen-SEA-LION-v4-32B |
|---|---|
| no system prompt | **0/32** |
| 6 sector system prompts × 4 languages | **59/192 (31%)** |
| fix arm (sector prompt + "You are Apertus…") | **68/192 (35%)** |

So **127/384 (33%) of system-prompt requests were not served by Apertus**, against 0/32 without one. Only the response `model` field shows this. Time series (prediction c) is still running: `ts.jsonl`; window 1 had 5/10 vs 0/10.

## (a) Identity switch-off: PASS
Rate at which Apertus-served answers name Apertus or the Swiss AI Initiative on "who developed you / which model are you":

| Arm | Rate | 95% CI |
|---|---|---|
| no system prompt | 16/16 = 100% | [80.6, 100] |
| sector prompts | **12/65 = 18.5%** | [10.9, 29.6] |

Pre-registered thresholds: ≤20% and ≥80%. Under sector prompts, 17/65 name a foreign vendor (OpenAI/GPT etc.) as creator. By language: de 5/14, fr 4/17, it 3/18, en 0/16.

## (b) One-line fix restores identity: PASS
Fix arm: 60/60 = 100% [94.0, 100].

## (d) Data-processor falsehood: threshold met, but NOT system-prompt-specific (honest reading)
Rate of `vendor_false` or `hosting_assertion` on the data questions:

| Arm | Rate | 95% CI | Vendor-false | Hosting assertion |
|---|---|---|---|---|
| sector | 35/68 = 51.5% | [39.8, 62.9] | 11 | 28 |
| no system | **10/16 = 62.5%** | | 9 | 2 |
| fix arm | 40/64 = 62.5% | | 3 | 38 |

The confabulated data-processor statements are a baseline Apertus behaviour; system prompts change their form, not their rate. Without a system prompt it names a foreign vendor (OpenAI) as the processor; with a deployment prompt it asserts concrete hosting ("servers of the cantonal administration", "in Switzerland"). Some of the latter are in-role and may happen to be true for a deployer, so count them as **unverifiable assertions**, not proven falsehoods. Claim (d) as "Apertus confabulates where your data is processed, with or without a system prompt"; do not claim the system prompt causes it.

## Claims this supports
1. Identity lives only in the default system prompt: 100% → 18.5% under realistic deployment prompts; one line restores it to 100%.
2. On the reference endpoint, a third of system-prompted requests are silently served by a different model family, billed under the Apertus name.
3. Apertus states a data processor it cannot know in more than half of answers, regardless of system prompt.
