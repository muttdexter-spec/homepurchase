# PROPOSAL, NOT A SPEC: ranking v4

Drafted by Claude (Opus 5) on 2026-09-12 at the owner's request, before this review.
It is included so you do not re-derive what is already derived, and so you have something
concrete to attack. Nothing here is implemented. The live system is still the one-line
$/sq ft sort described in the review brief. Treat every weight and anchor below as asserted
rather than fitted, because that is what they are.

---

## 1. Measurements behind the complaint

All computed on the 37 rows of `pipeline/out/decision.csv`.

- `true_cost` spans 1.47x across the set; `usable_sqft` spans 2.53x.
- Decomposing var(log all_in_psf): about 88% sits in the size term.
- corr(published rank, 1/usable_sqft) = 0.83.
- corr(published rank, fact grade) = -0.60.
- corr(published rank, recovered_pct) = -0.85, incidentally, not causally: both track size.
- 18 of 37 rows carry `bg_sqft_est`, so the ranking denominator is modelled in half the set
  while the numerator is known to a few per cent.
- `rank_low`/`rank_high` are computed and then discarded in the display. Enfield's band is
  3 to 17. Centennial's is 20 to 30.

One nuance that cuts against the simplest reading: size enters the fact grade as above-grade
sq ft capped at 2,600, and enters the ranking as uncapped usable area including basement.
Overlapping, not identical.

## 2. Proposed structure

### Layer 0: gates, non-compensatory

Confirmed moisture (STOP). `true_cost` above the buyer ceiling. `cash_to_close_20pct` above
cash available. Effective bedrooms below requirement. Unpriced liability (oil tank, in-ground
pool, tenanted) is HOLD, not eliminate: price it, then re-enter. `evidence: low` cannot be
ranked, only scheduled for a showing.

### Layer 1: five axes, absolute anchors, 0 to 100

**1. Cost efficiency (w 0.30).** `true_cost / effective_sqft`, where

```
effective_sqft = min(usable, 2200) + 0.45 * max(0, usable - 2200)
```

Space past ~2,200 sq ft counts at 45%: real, valuable, not worth full price to this buyer, and
disproportionately the estimated-basement space. Score = 100 * clamp((850 - eff_psf)/(850-480)).

**2. Fit (w 0.25).** The existing fact score with the size component removed: layout, effective
bedrooms, baths, lot, parking, location. Size comes out because axis 1 already carries it.
(Open question for the reviewer: the grade's size term is capped at 2,600 and axis 1's is not,
so an alternative is to keep size in Fit and uncap nothing.)

**3. Exposure (w 0.20).** Money that does not come back. Half from `sunk / ask` (anchors 2% to
10%), half from `recovered_pct` (anchors 20 to 70). This is the only axis that inherits
`arv_psf_renovated`, which is derived from asks, not solds. Lowest weight of the three
substantive axes for that reason.

**4. Carrying cost (w 0.15).** `monthly_carry`, anchors $800 to $480. Driven by tax and
component age, independent of price, still there in year five.

**5. Project burden (w 0.10).** `(day1_p80 + wishlist_p80) / (ask + day1_p80 + wishlist_p80)`,
anchors 18% to 4%. The share of total outlay that is construction rather than asset. This is
the axis that reintroduces wishlist, on the argument that optional-in-timing is not
optional-in-existence.

**Combination: weighted geometric mean**, `exp(sum_k w_k * ln(max(axis_k, 5)))`. A weighted sum
lets one strong axis buy off a collapsed one, which is how a C− reaches rank 14 on floor area.

**Then shrink for evidence.** Confidence factor from tells seen, photo count, the evidence
label, year source and `bg_sqft_est`, mapped to [0.70, 1.00]; pull the score toward the batch
median by (1 - confidence).

### Layer 2: rank the distribution

Recompute the five axes and the composite inside each of the 4,000 existing PERT draws, and in
the same draw perturb the estimated inputs: basement area (sigma 12% where `bg_sqft_est`, 4%
otherwise), day-one cost (sigma 25%), recovered_pct (sigma 8 points). Sort on **P(top 8)**,
display median rank and the p10 to p90 band.

## 3. Effect on the current 37

Computed with letter grades standing in for the raw fact score, so Fit is compressed and the
table will shift somewhat under a real implementation.

| New | Old | Listing | Gr | Score | Cost | Fit | Exp | Carry | Burden | Conf |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 16 | Barberry | B | 67.0 | 62 | 55 | 84 | 78 | 72 | 0.99 |
| 2 | 8 | Pinemeadow | A- | 64.7 | 72 | 79 | 83 | 40 | 66 | 0.82 |
| 3 | 10 | Seton | B- | 64.3 | 73 | 39 | 88 | 62 | 85 | 0.99 |
| 4 | 11 | Hazelwood | A- | 63.5 | 69 | 79 | 70 | 52 | 42 | 0.91 |
| 5 | 4 | Ravine | B- | 63.3 | 87 | 39 | 83 | 55 | 70 | 0.93 |
| 6 | 15 | Clinton | B | 62.9 | 63 | 55 | 83 | 53 | 69 | 0.97 |
| 7 | 1 | Tania | A | 62.9 | 96 | 92 | 67 | 30 | 38 | 0.79 |
| 8 | 6 | Columbus | B | 62.5 | 78 | 55 | 91 | 32 | 71 | 0.91 |
| 9 | 2 | Delaney | A- | 61.4 | 83 | 79 | 74 | 15 | 74 | 0.99 |
| 10 | 5 | Bunton | B- | 61.4 | 87 | 39 | 86 | 52 | 55 | 0.91 |
| 11 | 7 | Bonnie | C+ | 59.7 | 85 | 26 | 85 | 93 | 52 | 0.91 |
| 12 | 18 | Pondview | B- | 54.7 | 57 | 39 | 88 | 38 | 83 | 0.91 |
| 17 | 3 | Enfield | B | 48.0 | 89 | 55 | 42 | 63 | 0 | 0.85 |

Stability over 3,000 draws: Barberry median 1 [1-5], P(top 8) 98%; Seton 4 [2-8] 93%; Ravine
5 [3-9] 89%; Pinemeadow 3 [1-10] 86%; Tania 6 [3-10] 78%; Clinton 6 [2-10] 78%; Columbus
7 [3-11] 70%; Hazelwood 6 [1-13] 67%; Delaney 8 [5-10] 60%; Bunton 8 [4-12] 50%; Bonnie
10 [6-13] 29%.

Three moves worth arguing about:

- **Tania, 1 to 7.** Still excellent on cost and facts. Loses on carry ($705/mo), on burden
  ($185k of work on a $1.27M ask), and to the evidence shrink (virtual staging, estimated year).
  Its old top spot was 3,210 sq ft, 1,010 of which now count at 45%.
- **Enfield, 3 to 17.** The largest move and the likeliest to be wrong. Best raw cost
  efficiency in the set, zero on burden: $294k of work on an $825k house plus an oil tank of
  unknown status. This is a question about the buyer, not the model.
- **Barberry to 1.** Nothing remarkable about it; it simply has no weak axis, which is what a
  geometric mean rewards and a $/sq ft sort cannot see.

A dominance check across the five axes leaves 19 of 37 non-dominated, so Pareto analysis is too
weak to rank with at five dimensions.

## 4. Known weaknesses of this proposal

- Every weight and every anchor is asserted. None is fitted, and with 37 price-filtered rows
  and no revealed preference from the buyer, it is not obvious any of them can be.
- The geometric mean is a strong choice that penalises specialists. A house that is outstanding
  on three axes and poor on one may be exactly the right house.
- The evidence shrink toward the batch median makes scores depend on the batch, which partly
  breaks the cross-time comparability the fact grade was built to have.
- Axis 3 still rests on ask-derived resale values.
- P(top 8) hard-codes the number 8.
