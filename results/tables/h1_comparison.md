# H1 comparison summary

Summary across all 30 paired seeds for each Li & Lim instance. `D proxy` is the current evaluator's route-stop proxy, not a measured travel distance.

| Instance | Paired seeds | Requests | Served (off/on) | Service rate (off/on) | D proxy, freeze off | D proxy, freeze on | Δ D proxy (on − off) |
|---|---:|---:|---:|---:|---:|---:|---:|
| lc101 | 30 | 53 | 53 / 53 | 100% / 100% | 662.5 | 662.5 | 0.0 |
| lc201 | 30 | 51 | 51 / 51 | 100% / 100% | 637.5 | 637.5 | 0.0 |
| lr101 | 30 | 53 | 53 / 53 | 100% / 100% | 662.5 | 662.5 | 0.0 |
| lr201 | 30 | 51 | 51 / 51 | 100% / 100% | 637.5 | 637.5 | 0.0 |
| lrc101 | 30 | 53 | 53 / 53 | 100% / 100% | 662.5 | 662.5 | 0.0 |
| lrc201 | 30 | 51 | 51 / 51 | 100% / 100% | 637.5 | 637.5 | 0.0 |

**Interpretation:** Every trial reports zero frozen commitments. The current DES does not simulate vehicle movement, and `GreedyInsertion` does not apply the freeze constraint. Therefore the two conditions are effectively identical; this table is a readability summary of prototype output, not a valid test of H1.

Raw per-seed data: [`../raw/h1_raw.csv`](../raw/h1_raw.csv).
