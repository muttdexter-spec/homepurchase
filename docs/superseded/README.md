# Superseded ranking documents

Kept so the lineage is readable. None of these describe what the code does now.

| File | Written | Superseded by | Status |
|---|---|---|---|
| `ranking-system-v4.md` | 12 Sep 2026 | `../ranking-system-v5.md` | Never implemented. Section 1, the case against `all_in_psf`, was accepted; the five-axis composite was not. |
| `claude-ranking-v4-proposal.md` | 12 Sep 2026 | `../ranking-system-v5.md` | The shorter proposal the v4 document was written from. Also never implemented. |
| `ranking-system-v5.md` | 13 Sep 2026 | `../ranking-system-v6.md` | Implemented and shipped. Section 8 was **stale on the day it shipped**: it describes the pre-lambda order (Enfield "13 to 1", Tania "1 to 11", Clinton "14 to 4", Crosby "37 to 25") and contradicts its own section 6 table (Enfield 15, Tania 1, Clinton 6, Crosby 33). Read section 6, never section 8. |

The v3-era `ranking-system.md` (9 Sep 2026, `value_score` = fact score per $100k all-in) was
superseded by the `all_in_psf` rule before this repo existed and is not carried here.

v5's whole family of ideas (a dominance frontier, overpay, and an exchange rate between grade points
and dollars) was retired on 14 September. `overpay` survives as one line in the showing record and
is still written to `decision.csv`; nothing else from that family is on the page or in the order.
