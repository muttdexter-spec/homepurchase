# Ranking system v4: replacing all_in_psf

**SUPERSEDED 13 September 2026 by `../ranking-system-v5.md`. Never implemented.** Kept because
it states the case against `all_in_psf` well (section 1 stands), and because `REVIEW-2026-09-12.md`
section 1 is an argument against the rest of it and reads better beside the original.

Written 2026-09-12. Supersedes the "rank ascending on `all_in_psf`" rule in
`HANDOFF-START-HERE.md` section 2 and the value_score rule in `ranking-system.md`.
Nothing below changes the cost model. It changes only what the ranking is computed from.

---

## 1. Why $/sq ft should not be the ranking

Measured on the 37 rows in `decision-v3.2.csv`.

**It is a ranking of square footage, not of houses.** Across the set, `true_cost` spans
1.47x and `usable_sqft` spans 2.53x. Decomposing the variance of log(all_in_psf), 88% of it
comes from the size term and roughly 12% from everything the cost model actually computes.
Correlation of published rank with `1/usable_sqft` is 0.83. The four thousand PERT draws,
the photo forensics and the era priors move the ranking by about an eighth; the sq ft field
moves the rest.

**The denominator is the least reliable field in the file.** 18 of 37 rows carry
`bg_sqft_est`, so their basement area is the 70% footprint estimate, not a stated number.
The numerator is known to within a few per cent (ask is exact, day1_p80 is modelled).
So the ranking is most sensitive to the input with the widest error bars. That is backwards.

**It treats square feet as linearly fungible.** The 3,210 sq ft at Tania is not 2.25 houses
worth of the 1,430 at Aldridge, and for two people buying a first house it is not worth
2.25x anything. This is the same defect already recorded as the broken $/sq ft gate: Tania
at $418 reset the floor to $481 and nearly killed two A- listings. The gate and the ranking
share one root cause, so fixing the gate alone leaves the ranking wrong.

**It discards most of what the model produces.** `recovered_pct` ranges 23 to 67,
`sunk` ranges $30k to $127k, `monthly_carry` ranges $501 to $787, `wishlist_p80` ranges
$51k to $210k. None of them enter the rank. `recovered_pct` correlates with published rank at
-0.85, which is not because the rank uses it, but because both track size; when they diverge
the rank ignores it.

**It ignores the fact grade it sits beside.** Correlation of rank with fact grade is -0.60.
Middlesmoor, a C-, ranks 14. Pallatine, a B-, ranks 27. Two rows above Cavendish (C, rank 9)
sit A- listings. A buyer reading the table top down is not reading a quality order.

**It is a point estimate presented as an order, when the spread is already computed.**
`rank_low`/`rank_high` are in the file and are discarded in the display. Enfield's band is
3 to 17. Centennial's is 20 to 30. "Rank 3" is not a true statement about Enfield.

**It prices none of the liabilities.** Oil tank, in-ground pool, tenanted, confirmed moisture
all live in a notes column outside the number.

---

## 2. The replacement, in three layers

### Layer 0: gates, non-compensatory

Nothing below runs on a listing that fails a gate. Gates are binary and are never traded off
against a good score.

| Gate | Rule |
|---|---|
| Moisture | confirmed basement moisture is a STOP (Windermere) |
| Budget | `true_cost > buyer ceiling` |
| Cash | `cash_to_close_20pct > cash available` |
| Bedrooms | effective bedrooms (>= 60 sq ft) below requirement |
| Unpriced liability | oil tank, in-ground pool, tenanted: **HOLD, not eliminate.** Price it, then re-enter |
| Evidence | `evidence: low` cannot be ranked at all, only scheduled for a showing |

### Layer 1: five axes, absolute anchors, 0 to 100

Each axis is scored against fixed thresholds, not against the batch, so a listing scored in
September stays comparable to one scored in March. This is the property the current fact
grade already has and the $/sq ft rank does not.

**1. Cost efficiency (weight 0.30).** `true_cost / effective_sqft`, where

```
effective_sqft = min(usable, 2200) + 0.45 * max(0, usable - 2200)
```

Space past roughly 2,200 sq ft counts at 45%. It is real, it has value, it is not worth full
price to this buyer, and it is exactly the space most likely to be an estimated basement.
Score = 100 * clamp((850 - eff_psf) / (850 - 480)).

**2. Fit (0.25).** The existing fact score, **with the size component removed**. Layout,
effective bedrooms, baths, lot, parking, location. Size must come out because it already
drives axis 1; leaving it in both places counts it twice with the same sign, which is the
$/sq ft problem in a new shape.

**3. Exposure (0.20).** Money that does not come back. Half from `sunk / ask` (anchors 2% to
10%), half from `recovered_pct` (anchors 20 to 70). **This is the one axis that inherits
`arv_psf_renovated`**, which is derived from asks, not solds. It carries the lowest weight of
the three substantive axes for that reason, and it must be re-run the day sold $/sq ft arrives.

**4. Carrying cost (0.15).** `monthly_carry`, anchors $800 to $480. Independent of price: it
is driven by tax and by component age, and it is the number that is still there in year five.

**5. Project burden (0.10).** `(day1_p80 + wishlist_p80) / (ask + day1_p80 + wishlist_p80)`,
anchors 18% down to 4%. The share of total outlay that is construction rather than asset.
The current model excludes wishlist from the ranking on the grounds that it is optional in
timing. Optional in timing, not in existence: a house that needs a kitchen needs a kitchen,
and living through it is a cost even when it is deferred.

**Combination is a weighted geometric mean, not a sum.**

```
score = exp( sum_k w_k * ln(max(axis_k, 5)) )
```

A weighted sum lets one strong axis buy off a collapsed one. That is how a C- reaches rank 14
on floor area. A geometric mean cannot: the score falls hard when any axis approaches zero,
which is the correct behaviour for a house you have to live in.

**Then shrink for evidence.** Compute a confidence factor from `tells_seen_of_15`, photo count,
`evidence`, `year_src` and `bg_sqft_est` (range 0.70 to 1.00) and pull the score toward the
batch median by 1 - confidence. A listing whose numbers are half estimated should not outrank
a fully observed one on the strength of the estimates. This also gives the photo pass a
mechanical payoff: doing it moves the score toward its true value in either direction.

### Layer 2: rank the distribution, not the point

The p80 simulation already exists. Recompute the five axes and the composite **inside each of
the 4,000 draws**, and in the same draw perturb the estimated inputs: basement area
(sigma 12% where `bg_sqft_est`, 4% otherwise), day-one cost (sigma 25%), recovered_pct
(sigma 8 points). Report median rank, the 10th to 90th percentile band, and P(top 8).

Sort on **P(top 8)**, not on the point score. It answers the question actually being asked,
which is "which houses are worth a Saturday", and it degrades honestly: a house with a wide
band shows a low probability instead of a false position.

---

## 3. What it does to the current 37

Computed with the letter grades as a stand-in for the fact score (the real implementation
should use the raw score; the letters compress the Fit axis and this table will shift a little).

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

Rank stability over 3,000 draws:

| Listing | Median | p10 to p90 | P(top 8) |
|---|---|---|---|
| Barberry | 1 | 1 to 5 | 98% |
| Seton | 4 | 2 to 8 | 93% |
| Ravine | 5 | 3 to 9 | 89% |
| Pinemeadow | 3 | 1 to 10 | 86% |
| Tania | 6 | 3 to 10 | 78% |
| Clinton | 6 | 2 to 10 | 78% |
| Columbus | 7 | 3 to 11 | 70% |
| Hazelwood | 6 | 1 to 13 | 67% |
| Delaney | 8 | 5 to 10 | 60% |
| Bunton | 8 | 4 to 12 | 50% |
| Bonnie | 10 | 6 to 13 | 29% |

**The three disagreements worth arguing about:**

- **Tania, 1 to 7.** It stays excellent on cost and facts. It loses on carry ($705/mo), on
  burden ($185k of work on a $1.27M ask), and to the evidence shrink (virtual staging, estimated
  year). Its top spot was 3,210 sq ft, and 1,010 of those feet are now counted at 45%.
- **Enfield, 3 to 17.** The largest move in the table and the one most likely to be wrong.
  Enfield has the best raw cost efficiency in the set ($89/100 on that axis) and scores zero on
  burden: $294k of work on an $825k house, plus an oil tank of unknown status. The old rank of 3
  came from counting only day-one cost. Whether 17 or 3 is right is a question about the buyer,
  not about the model: it is the only genuine sweat-equity play in the batch. If that is wanted,
  drop the burden weight and it climbs back.
- **Barberry to 1.** Nothing about it is remarkable. It has no weak axis, which is precisely
  what the geometric mean rewards and what a $/sq ft sort cannot see.

A dominance check across the five axes leaves 19 of 37 non-dominated, so Pareto analysis is too
weak to rank with at five dimensions. Use it only as a sanity filter on the bottom half.

---

## 4. What to change in the code

1. `score.py`: add `effective_sqft()`, the five axis functions with the anchor constants in
   `costs.yaml`, the geometric composite and the confidence shrink.
2. Remove the size component from the fact score, or add a `fact_score_ex_size` field. Do not
   leave size in both places.
3. Move the composite inside the existing 4,000-draw loop and emit `p_top8`, `rank_med`,
   `rank_p10`, `rank_p90` to `decision.csv`. Delete `all_in_psf` from the sort; keep the column.
4. Replace the broken 15%-above-best $/sq ft gate with the Layer 0 gate list. It is not needed
   once the ranking is not a $/sq ft sort.
5. Every anchor above is a tunable and belongs in `costs.yaml` with a source note. The weights
   are the buyer's, not the model's: expose them and re-run.

## 5. What this still does not fix

The exposure axis is built on `arv_psf_renovated`, which is derived from asking prices. Sold
$/sq ft per pocket remains the highest-value missing input, and it moves axis 3 and nothing
else. The other four axes are ceiling-free by construction, which is the point: 80% of the
new ranking survives the ceilings being wrong, where `net_position` ranking did not.

---

## What v5 did instead, in three lines

Section 1 of this document was accepted in full. Sections 2 and 3 were not built, because three
of the five axes measure size or price (cost and exposure correlate at 0.78) and because five
weights cannot be fitted on 37 asking prices. v5 keeps the gates, drops the composite, and ranks
on overpay against a two-axis dominance frontier: cost to own over the hold on one axis, the
facts-only fit score on the other. See `../ranking-system-v5.md` and `../REVIEW-2026-09-12.md`
section 1.
