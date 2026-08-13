# Ablation MVP — canonical vs ablations

Tasks: 150. Deterministic (minimal-input) run; canonical engine = mlt-stack-1.0.0rc1.

| System | n | ok | trace entries | target band | nist_rmf | registry | COA bands collapsed |
|---|---|---|---|---|---|---|---|
| canonical | 150 | 150 | {6: 150} | 150 | 150 | 150 | 0 |
| A2 | 150 | 150 | {6: 150} | 0 | 150 | 150 | 150 |
| A3 | 150 | 150 | {6: 150} | 150 | 150 | 150 | 0 |
| A4 | 150 | 150 | {5: 150} | 150 | 150 | 150 | 0 |
| A5 | 150 | 150 | {6: 150} | 150 | 150 | 150 | 0 |
| A6 | 150 | 150 | {0: 150} | 150 | 150 | 150 | 0 |
| A7 | 150 | 150 | {6: 150} | 150 | 0 | 150 | 0 |
| A1 | 150 | 150 | {1: 150} | 150 | 0 | 150 | 150 |
