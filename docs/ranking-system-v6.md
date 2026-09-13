# Ranking system v6: one score per house, weights from the buyers

Written 14 September 2026. Supersedes `superseded/ranking-system-v5.md` in full. The argument for
the change, and the case for two-sided condition, is in `RANK-V6-DECISION.md`; this document is the
specification of what the code does.

Nothing in v6 changes a catalog cost, a recovery band, an era prior or a contingency.

---

## 1. What replaced what

v5 ordered the list on `own_mo - 120 * fit`: cost to own per month, less an asserted $120 a month
for every point of a facts-only grade. It had four scores on one card and a page full of frontier,
overpay and best-value language that no longer described the order.

v6 has **one score per house, 0 to 100, higher is better, sorted descending**. The facts grade is
still computed and still written to `decision.csv` and `detail.json`, but **since 14 September it is
not rendered anywhere on the page**: two numbers measuring different things, side by side with no
way to tell which one the list obeys, was the confusion rather than the cure. `overpay` is still computed and still written to
`decision.csv`, but it appears in exactly one place on the page, under "Before you offer".

## 2. The gate ladder

Gates are non-compensatory and run in order. A gated listing is not ranked; it is shown at the
bottom with `-` in every column a rank would occupy, and the reason on its card.

```
G0  STOP       verdict() == STOP                                     excluded
G1  program    beds_effective < gates.min_beds_ag                    excluded
G2  budget     ask + day1_p80 > gates.max_all_in                     excluded   (null = off)
G3  cash       cash_to_close > gates.max_cash_to_close               excluded   (null = off)
G4  project    work_expected > project_share_of_ask x ask            excluded if gates.no_projects,
                                                                     else ranked with a Project stamp
H   HOLD       oil tank / in-ground pool / sitting tenant            ranked, stamped, never "See first"
```

Buyer settings on file, 14 September 2026: `min_beds_ag: 2`, `no_projects: false`,
`project_share_of_ask: 0.15`, `max_all_in: null`, `max_cash_to_close: null`, `max_monthly: null`.

## 3. The score

```
score = sum_k w_k . comp_k / sum_k w_k        x split_dock if the style is a split level
rank  = sort by score, descending
```

Eight components, each on an **absolute** 0 to 100 scale, so a house scored today is comparable to
one scored in March and none of them moves when the batch changes.

| Component | 0 | 100 | Source |
|---|---|---|---|
| space | 1,000 sq ft above grade, no basement | 2,600 sq ft plus a finished basement with exterior access | v5 space term / 25 |
| layout | 0 effective bedrooms | 4+ beds, primary 150 sq ft or more, no tiny rooms | v5 layout / 20 |
| baths | none | 3+ full plus a powder | v5 baths / 20 |
| parking | none | 2-car garage plus 2 spots | v5 parking / 8 |
| lot | 4,000 sq ft or less | 9,000 sq ft or more | v5 lot / 15 |
| location | walk plus transit 45 or less, no school within 0.5 km | walk plus transit 120, school within 0.5 km | v5 location / 12, plus `location.municipality_bonus` |
| condition | every job in this house expected | no job expected | section 4 |
| price | $84,000 a year to own, before day-one work | $54,000 a year | section 5 |

`split_dock` is 0.95, elicited 14 September. Twelve of the 37 are splits.

## 4. Condition, two-sided

```
work_expected = sum over day-one and wishlist lines of  p . PERT mean . contingency . HST
              + sum over reserve lines of  p . p_hold(age, life, H) . PERT mean . HST
work_full     = the same sums with every p at 1
condition     = 100 . (1 - work_expected / work_full)
```

`work_full` puts **every probability at 1, p_hold included**. Keeping `p_hold` in the denominator
made the age term cancel on exactly the lines it was added for, so a 1972 furnace read as fully
expected inside the hold, the same as a 2008 one. The one carve-out is a line whose life is 1: the
pool carry is an annual cost, not a component with a replacement probability, so its `H` multiplier
is a count and it stays on both sides.

`p_hold(age, life, H)` is the chance a component is replaced during the hold:

- younger than its life: original, remaining life known, `min(1, H / (life - age))`
- between one and one and a half lives: original and past due, `1.0`
- older: replaced at least once at an unknown date, uniform over the cycle, `H / life`
- confirmed original: `1.0` regardless
- life of 1 (the pool carry): `H`

It has a consequence worth seeing before believing: a 1999 to 2008 house scores **worse** on
mechanicals than a 1960s house, because its furnace and A/C are original and at end of life while
the 1960s house's were replaced at some point. Columbus (2008, "furnace 2026" in the remarks) is
that prediction coming true, and it is the one house of the six checked whose condition did not
move when the denominator was corrected, because its `p_hold` was already 1.0.

On the 36 ranked rows condition runs **16 (Grand) to 76 (Cherrywood)**.

### Photographs, and the four bounds

v5's rule was "photos demote, never promote". v6 lets a clean full-resolution read lower a line's
probability, which is a channel the cost model already had, under four bounds:

1. Only full-resolution tells move a line, and only toward the 0.15 floor, never to zero.
2. Structure, envelope and mechanical lines never move on photographs. They move on age, on a
   confirmed defect, or on a showing.
3. A concealed surface counts as half a read; `hdr_blowout: severe` voids all reads.
4. **Photographs alone cannot put a house at the top of the condition range.** With the floor and
   `p_hold` on the mechanicals, nothing in this batch exceeds 80 without showing evidence, and
   `test_model.py` fails if one ever does.

`condition.photos_may_lower_p: false` restores the demote-only rule. With it off, Seton falls from
70.1 to 50.8 against 51.2 for a synthetic Seton with every tell `not_shown`; the residue is the
confirmed defects, which are meant to survive.

## 5. Price

```
price = 100 . clamp((84,000 - cost_per_year) / (84,000 - 54,000))
```

`cost_per_year` is the cost of the hold excluding day-one work, per year: financing and opportunity
cost at the derived cost of capital, exit commission, land transfer tax and closing, tax and
upkeep. Day-one work lives in condition, so it is not counted twice.

The anchors are the search band, fixed: $270,000 to $420,000 over five years, expressed per year so
the 3, 5 and 10 year rankings in the band stay meaningful. At a flat five-year anchor every house
clamps to zero at a ten-year hold and the band stops measuring anything.

`hold.cost_of_capital` is no longer a key. It is derived as
`(1 - down_payment) . mortgage_rate + down_payment . opportunity_rate`, which at 20%, 4.25% and 3.0%
is 4.0%, the number v5 asserted. The ranking's price component and the page's monthly payment now
come from one rate by construction.

## 6. The band

Rank under **every weight set on file, at 3, 5 and 10 years, at the low, point and high end of the
house's own day-one uncertainty**, min to max. The condition ends come from the p10 and p90 of the
4,000 day-one draws `cost()` already makes; the draws carry contingency, the multi-room premium,
HST and soft costs that the line-by-line sum does not, so they enter as a ratio against their own
median rather than as a level.

With one weight set on file that is nine rankings. With both it is eighteen.

A `Disagree` stamp goes on any house whose two personal ranks differ by more than 5. It cannot
appear until both people have weights.

The day-one simulation still sets `day1_p80` for cash to close and the offer.

## 7. The weights

**These come from the buyers and never from the batch or the model.** See `ELICITATION.md`.

Swing weighting was attempted on 13 September and failed: asked for an ordering and eight numbers,
the buyer gave neither. It was replaced on 14 September by **fifteen forced choices between real
houses from this batch**, answered on the page, with the weights fitted from the choices
(`fit_choices.py`). Until fifteen choices exist for a person, that person's weights are whatever is
in `costs.yaml` and the page stamps every card **Weights provisional**.

- Pair selection (`build_pairs.py`): greedy D-optimality on the difference vectors, which is the
  standard construction for a paired-comparison design, subject to at least three pairs per
  component with a difference of 30 or more, no house in more than four pairs, and no pair where
  one house is at least as good as the other on all eight.
- Fit (`fit_choices.py`): paired-comparison logit, weights non-negative and summing to 100, a free
  consistency parameter, and an L2 ridge toward the prior whose strength is calibrated so a
  perfectly consistent respondent still moves every design-supported weight by at least 10 points.

`joint` is the mean of the two once both exist, and whoever is on file until then.

## 8. What is gone

`dollars_per_fit_point_mo`, `rank_value`, `fit_dollars_mo`, the dominance frontier as an ordering
rule, the `Best value` and `Frontier` stamps, the needs-work score, the frontier chart, the three
table group headers, and the convention of writing 91 to 93 into `decision.csv` for gated rows.

`overpay` and `dominated_by` are still computed and still in `decision.csv`. Their one use on the
page is the first line under "Before you offer" in the showing record.
