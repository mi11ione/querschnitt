# Prüfstand task — build `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`

Served model(s): swiss-ai/apertus-v1.5-8b · calls stored: 3673 · log-probabilities: False

## APS chapter vs APS editors, split `heldout_s25` (n = 927 of 927)

| Design | n | top-1 [95%] | top-3 | ECE raw | ECE isotonic (2-fold) |
|---|---|---|---|---|---|
| D0 | 918 | 0.6546 [0.6233, 0.6848] | 0.8082 | 0.2556 | 0.047 |
| D1 | 369 | 0.7371 [0.6899, 0.7795] | 0.8563 | 0.2549 | 0.049 |
| D3 | 918 | 0.6819 [0.651, 0.7113] | 0.8431 | 0.2555 | 0.0622 |
| D4 | 918 | 0.7037 [0.6733, 0.7324] | 0.8398 | 0.2783 | 0.0287 |
| D4E | 927 | 0.6968 [0.6665, 0.7256] | 0.8392 | 0.2823 | 0.0443 |
| D4S | 346 | 0.6387 [0.5868, 0.6876] | 0.8092 | 0.3417 | 0.0839 |

- D1-D0: -0.0054 [-0.038, +0.0272] (paired bootstrap, n 369)
- D3-D0: +0.0272 [+0.0054, +0.048] (paired bootstrap, n 918)
- D4-D0: +0.049 [+0.025, +0.0741] (paired bootstrap, n 918)
- D4-D3: +0.0217 [+0.0, +0.0458] (paired bootstrap, n 918)
- D4-D1: -0.0027 [-0.0082, +0.0] (paired bootstrap, n 369)
- D4E-D4: -0.0076 [-0.0142, -0.0021] (paired bootstrap, n 918)
- D4S-D0: +0.0404 [-0.0029, +0.0839] (paired bootstrap, n 346)
- D4S-D3: +0.0289 [-0.0145, +0.0694] (paired bootstrap, n 346)
- D4S-D1: +0.0 [-0.0215, +0.0215] (paired bootstrap, n 140)
- Majority-chapter baseline: 0.1165
- D0: the two code orders agree on 0.6285 of items; precision there 0.766, elsewhere 0.4662
- D4: the two code orders agree on 0.6481 of items; precision there 0.7932, elsewhere 0.5386
- D4E: the two code orders agree on 0.6515 of items; precision there 0.7864, elsewhere 0.5294

## DVS "Digitalisierung" recall (n = 0 of 0)

- found 0 / 0 = None [None, None]
- misses: —
