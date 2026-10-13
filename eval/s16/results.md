# S16 — read-back combined with examples (n = 1357, build …dd237840)

| Design | top-1 [95%] | top-3 |
|---|---|---|
| D1 | 0.7038 [0.679, 0.727] | 0.843 |
| D3 | 0.7222 [0.698, 0.745] | 0.8747 |
| D4 | 0.7406 [0.717, 0.763] | 0.8836 |
| D4S | 0.7487 [0.725, 0.771] | 0.8563 |

- D4-D3: +0.0184 [+0.0022, +0.0339]
- D4-D1: +0.0368 [+0.0214, +0.0531]
- D4S-D3: +0.0265 [+0.0118, +0.0413]
- D4S-D1: +0.045 [+0.0265, +0.0626]
- D3-D1: +0.0184 [-0.0007, +0.0376]
- Decision: D4 shipped for federal affairs (pre-registered rule: D4 if its top-1 ≥ D3's)
- New subtopic calls: 1935
- Calibration aps: ECE 0.2791 → 0.0319 (2-fold cross-fitted, n 1357, acc 0.7038)
- Calibration aps-fed: ECE 0.2416 → 0.0574 (2-fold cross-fitted, n 1357, acc 0.7487)
