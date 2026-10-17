# Prüfstand task — build `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`

Served model(s): swiss-ai/apertus-v1.5-8b · calls stored: 7156 · log-probabilities: True

## APS chapter vs APS editors, split `s9` (n = 1357 of 1357)

| Design | n | top-1 [95%] | top-3 | ECE raw | ECE isotonic (2-fold) |
|---|---|---|---|---|---|
| D0 | 1357 | 0.6551 [0.6294, 0.68] | 0.8393 | 0.2623 | 0.0351 |
| D1 | 1357 | 0.7037 [0.6789, 0.7275] | 0.843 | 0.2791 | 0.0319 |
| D3 | 1357 | 0.7221 [0.6977, 0.7454] | 0.8747 | 0.2212 | 0.0167 |
| D4 | 1357 | 0.7406 [0.7166, 0.7633] | 0.8835 | 0.2462 | 0.0211 |
| D4E | 1357 | 0.7376 [0.7136, 0.7604] | 0.8835 | 0.2475 | 0.0332 |
| D4S | 1357 | 0.7487 [0.7249, 0.7711] | 0.8563 | 0.2416 | 0.0573 |

- D1-D0: +0.0486 [+0.0324, +0.0649] (paired bootstrap, n 1357)
- D3-D0: +0.067 [+0.0486, +0.0863] (paired bootstrap, n 1357)
- D4-D0: +0.0854 [+0.0663, +0.1054] (paired bootstrap, n 1357)
- D4-D3: +0.0184 [+0.0022, +0.0339] (paired bootstrap, n 1357)
- D4-D1: +0.0368 [+0.0213, +0.0524] (paired bootstrap, n 1357)
- D4E-D4: -0.0029 [-0.0059, -0.0007] (paired bootstrap, n 1357)
- D4S-D0: +0.0935 [+0.0729, +0.1143] (paired bootstrap, n 1357)
- D4S-D3: +0.0265 [+0.011, +0.0413] (paired bootstrap, n 1357)
- D4S-D1: +0.0449 [+0.0265, +0.0627] (paired bootstrap, n 1357)
- Majority-chapter baseline: 0.0795
- D0: the two code orders agree on 0.6101 of items; precision there 0.7814, elsewhere 0.4574
- D4: the two code orders agree on 0.6418 of items; precision there 0.8266, elsewhere 0.5864
- D4E: the two code orders agree on 0.6418 of items; precision there 0.8254, elsewhere 0.5802

## DVS "Digitalisierung" recall (n = 30 of 30)

- found 27 / 30 = 0.9 [0.7437, 0.9655]
- misses: 161610 (CHE, p 0.0), 297879 (BL, p 0.0), 337826 (BE, p 0.0)
