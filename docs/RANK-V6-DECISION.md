# Rank v6: one score per house, weights from you, not from the model

Written 2026-09-13 after reading the shipped `homepurchase-upload_4.zip` (reproduces: decision.csv
`55236aef…`, full.html `e4ca7f5a…`, mobile.html `927d2570…`, tests PASS). Supersedes the ranking
rule in `ranking-system-v5.md` §5. Nothing below changes a catalog cost.

Companion files: `reference/rank_v6.py` (runs against the shipped `score.py` unchanged),
`reference/decision_v6_prototype.csv` (placeholder weights, for shape only),
`reference/weight-sensitivity.md`, `ELICITATION.md` (the script that produces the real weights).

---

## 1. What is wrong with v5 as shipped

Three things, and the first two are mine.

1. **The frontier formulation ranks on price.** `overpay` is a distance in dollars from the
   cheapest house that is about as much house. It contains no grade term, so the top of the list
   was every cheap C+ in the batch. Opus's fix (`own_mo − 120 × fit`) was the right emergency
   move, but it leaves the page and the docs full of frontier, overpay and best-value language
   that no longer describes the order, and the $120 was picked from four options in five minutes.
2. **Fit is facts-only and condition can only subtract**, so a 2026 full renovation (Seton, every
   tell clean at full resolution) and a house with every tell `not_shown` get the same grade. The
   cost side tells them apart, but weakly: day-one work is $274 a month on average against
   $5,097 of capital cost. A ranking that cannot prefer a renovated house to a dated one at the
   same price is not a ranking of houses. Tania at #1 (virtually staged, stipple ceilings,
   drop-tile basement, original second bath, $152k of expected work) is the symptom.
3. **Four scores on one card.** Composite rank value, facts grade, needs-work score, room-driven
   score. A reader cannot tell which one the page is sorted on.

## 2. The formulation

A gate ladder, then **one score, 0 to 100, higher is better, sorted descending.** The score is a
weighted sum of eight components, each on an absolute 0 to 100 scale, with weights elicited from
the two buyers by the swing-weight method (`ELICITATION.md`). Nothing about the batch sets a
weight or an anchor.

```
G0  STOP       verdict() == STOP                           excluded
G1  program    beds_effective < min_beds_ag                excluded   (buyer, default 3; ask)
G2  budget     ask + day1_p80 > max_all_in                 excluded   (buyer, null = off)
G3  cash       cash_to_close > max_cash_to_close           excluded   (buyer, null = off)
G4  project    work_expected > project_share × ask         excluded if buyer says no projects,
                                                            else ranked with a Project stamp (0.15)
H   HOLD       oil tank / pool / tenanted                  ranked, stamped, never "See first"

score = Σ_k w_k · comp_k / Σ_k w_k            × 0.94 if split-level and the buyer keeps the dock
rank  = sort by score, descending
```

| Component | 0 | 100 | Source |
|---|---|---|---|
| space | 1,000 sq ft AG, no basement | 2,600 sq ft AG + finished basement + exterior access | v5 space term / 25 |
| layout | 0 effective bedrooms | 4+ beds, primary ≥ 150 sq ft, no tiny rooms | v5 layout / 20 |
| baths | none | 3+ full + powder | v5 baths / 20 |
| parking | none | 2-car garage + 2 spots | v5 parking / 8 |
| lot | ≤ 4,000 sq ft | ≥ 9,000 sq ft | v5 lot / 15 |
| location | walk+transit ≤ 45, no school in 0.5 km | walk+transit 120, school in 0.5 km | v5 location / 12 |
| **condition** | every job in this house expected | no job expected | **new, §3** |
| **price** | $7,000 /mo to own ex day-one | $4,500 /mo | **new, §4** |

Six of the eight are the fit components you already have, rescaled. The letter grade on the facts
stays exactly as it is and keeps its absolute meaning. The composite is shown as a number and a
rank, not a second letter scale: a letter on a weighted composite would need thresholds with no
meaning outside this batch.

**Why a weighted sum now, when the review rejected v4's composite.** v4 failed on two counts that
do not apply here. Its five axes were three copies of size (correlation 0.78 between cost and
exposure, two eigenvalues carrying 67% of the variance), so its weights did not mean what they
said; these eight are the facts components, which are close to independent, plus condition and
price, which are independent of each other and of size once the space term saturates. And v4's
weights were asserted from the batch; these come from the buyers, by a method built for exactly
this (SMART/swing, Edwards and Barron 1994), in fifteen minutes each. The geometric mean is not
used: a house that is excellent on six things and poor on two is a legitimate answer, and the
gates carry the must-haves.

**Why not keep `own_mo − λ·fit`.** It is the same family as this (a weighted sum with one
elicited weight and seven asserted ones). v6 elicits all eight and puts condition on both sides.

## 3. Condition, two-sided, from the cost model

```
work_expected = Σ over day-one and wishlist lines of  p · PERT mean · contingency · HST
              + Σ over reserve lines of  p · p_hold(age, life, H) · PERT mean · HST
work_full     = the same sums with every p = 1
condition     = 100 · (1 − work_expected / work_full)
```

`p` is the cost model's own probability for each line: era prior for a job nobody has looked at,
pulled toward 0.15 by a clean full-resolution read, pinned at 1.0 by a confirmed defect, and
overridden by the showing record. So condition is **the cost-weighted share of this house's work
that is not expected**, and it needs no new table of asserted points. On the 34 ranked rows it
runs 25 (Enfield, $211k of $280k expected) to 77 (Oxlow, $43k of $191k).

`p_hold` is new and fixes review items 5.7 and brief item 6 at once: the probability a component
is replaced *during the hold*, from house age and component life. Younger than the component's
life: original, remaining life known, `min(1, H/(life − age))`. Between one and one and a half
lives: original and past due, 1.0. Older: replaced at least once at an unknown date, uniform over
the cycle, `H/life`. A confirmed-original component (Wyandotte's windows) is 1.0 regardless. The
same `p_hold` replaces the flat annuity in `own_cost`'s reserve term. It has a consequence worth
seeing before believing: a 1999 to 2008 house scores *worse* on mechanicals than a 1960s house,
because its furnace and A/C are original and at end of life while the 1960s house's were replaced
at some point. Columbus (2008, "furnace 2026" in the remarks) is that prediction coming true.
The 18 seller-stated component years and the four `_seen` toggles (bug list, §7) are how a house
gets out of it.

**This changes "photos demote, never promote", and here is the argument.** The principle was
written after Overton, where a *contact-sheet* impression called a cheap reface "genuinely
renovated". What caught it was the full-resolution tells (topmount sink, rolled laminate edge),
and the review showed (§2.7) that the cost model already lets those same tells lower a line's
probability, by a median $13k per house. Condition in v6 uses that channel deliberately, with four
bounds that the old principle got by fiat:

1. Only full-resolution tells move a line, and only toward the 0.15 floor, never to zero.
2. Structure, envelope and mechanical lines never move on photographs; they move on age, on a
   confirmed defect, or on a showing.
3. A concealed surface (rug, mat, curtain) counts as half a read; `hdr_blowout: severe` voids all
   reads. Both already in the code.
4. **Photographs alone cannot put a house in the top of the condition range.** With the 0.15
   floor and `p_hold` on the mechanicals, the highest condition any house reaches on photos is
   about 77 of 100. The last 23 points need a showing record.

So the fact grade still cannot be raised by a photograph, and no house can be called renovated
without someone standing in it. What changes is that a house whose kitchen, baths, floors and
windows read clean at full resolution now scores above one whose tells are unseen, instead of
tying it. If you want the old rule back, set `condition.photos_may_lower_p: false` and condition
becomes demote-only again; the rest of v6 is unaffected.

## 4. Price, one component among eight

`price = 100 · clamp((420,000 − cost5) / (420,000 − 270,000))`, where `cost5` is the **5-year
cost** ex day-one: financing and opportunity cost at the derived cost of capital, exit commission,
land transfer tax and closing, tax and upkeep, over the hold (day-one lives in condition, so it is
not counted twice). Anchors are the search band, fixed, so a house scored in October is comparable
to one scored today. Its weight is the buyers' and is elicited with the other seven. There is no
separate λ. The 5-year cost is displayed as a total, never per month: `USABILITY-SPEC.md` §0 and
§1 explain why the page's two "/mo" numbers could never agree and which one survives.

## 5. Uncertainty and the band

The band is no longer day-one draws. It is **rank under Alex's weights, under his partner's, and
under the joint mean, at 3, 5 and 10 years**: nine rankings, min to max. That is the uncertainty
that actually exists in this decision, and it reads as a sentence: "3 (2 to 7): 5th for you,
2nd for her, moves to 7th on a 10-year hold". A `Disagree` stamp goes on any house whose two
personal ranks differ by more than 5.

The day-one simulation still sets `day1_p80` for cash-to-close and the offer; it does not need to
be re-ranked.

## 6. What the elicitation decides, and what it does not

`reference/weight-sensitivity.md` runs the prototype under five weight sets (placeholder,
grade-first, condition-first, price-heavy, equal). Position ranges:

- **Stable under any weights.** Barberry 3 to 7, Clinton 5 to 9, Delaney 1 to 10, Pinemeadow 1
  to 15 (top under everything but price-heavy). Bottom twelve (Weir, Osborne, Wyandotte,
  Yarmouth, Crosby, Christina, Oxlow, Samford, Pondview, Lark, Wood, Centennial) never above 16.
- **The elicitation decides these.** Enfield 1 to 17, Tania 3 to 21, Hazelwood 4 to 17,
  Cavendish 5 to 27, Grand 17 to 33, Bonnie 2 to 14, Caplan 3 to 16, Seton 4 to 18, Columbus 8
  to 23, Cherrywood 7 to 24.

That is the honest shape: about a third of the batch is ranked by the facts, a third by the
buyers' weights, a third is at the bottom regardless. Under the placeholder weights the order is
Delaney, Pinemeadow, Barberry, Clinton, Enfield, Hazelwood, Caplan, Tania, Bonnie, Ravine;
**do not read anything into that order**, the weights are mine and exist only to show the machine
runs. The order that goes on the page is the one produced after `ELICITATION.md` has been run
with both of you, and the prompt forbids computing it before then.

## 7. Bugs and leftovers for this pass

From Opus's QA and from reading the shipped package.

| # | Item | Where | Fix |
|---|---|---|---|
| 1 | `ranking-system-v5.md` §8 describes the pre-λ order (Enfield "13 to 1", Tania "1 to 11", Clinton "14 to 4", Crosby "37 to 25") and contradicts its own §6 table (Enfield 15, Tania 1, Clinton 6, Crosby 33). | docs | Superseded by `ranking-system-v6.md`; move v5 to `superseded/` with a note that §8 was stale when it shipped. |
| 2 | Windows confirmed original still annualised over 30 years (review 5.7). | `own_cost` | `p_hold` (§3) in the reserve term of `own_cost`. |
| 3 | No `furnace_seen` / `roof_seen` / `ac_seen` / `water_heater_seen` / `panel_seen` promotion (review 5.10, backlog 10). | `cost()`, showing record | Values `original` / `replaced_<year>` / `new`; `replaced` sets that line's age from the year, `new` sets `p_hold` = `H/life`. Show the 18 seller claims as pre-filled "claimed: verify" items. |
| 4 | `reserve.pool_carry_annual` added and not wired (backlog 11). | `cost()` | Add a reserve line when POOL is detected, `p = 1`, life 1 (annual carry). |
| 5 | Four scores on the card (§1.3). | page | One score panel, eight bars ordered by weight; the needs-work bar is removed (its content is the condition bar); the room-driven score stays inside the rooms disclosure. |
| 6 | Frontier / overpay / best value on the rail, table, stamps, glossary. | page, docs | Rail headline becomes the score; `overpay` stays computed in `detail.json` and appears as one line in the money section: "Cheapest house within 3 points: Clinton, $150 /mo less". No stamp, no group header. |
| 7 | Hold toggle does not re-sort; under v6 the score depends on H, so an unsorted list with changing scores is wrong. | page | Re-sort on toggle (the runtime already reorders the stack on load by rank). Precompute the three orders. |
| 8 | Gated houses carry `rank > 90` so they sort last. | `score.py`, runtime | Fine; document it in the code and stop writing 91 to 93 into `decision.csv` (write `-`). |
| 9 | QA acceptance checklist renders as `- ]`. | `QA-PASS-2026-09-13.md` | `- [x]`. |
| 10 | `mobile.html` 4 px overflow at 360 px. | phone CSS | Pre-existing. Leave, as Opus did. |
| 11 | Middlesmoor gated on a 41 sq ft "bedroom"; 12 listings have no room table (backlog 1, 2). | data | Stage-1 page loads, no photos. **Authorise before the pass**, see §9. |
| 12 | `min_beds_ag: 3` gates Kent (2 + 1 lower). Whether a 2+1 bungalow is acceptable is a buyer setting, not a model default. | gates | Asked in the elicitation. |
| 13 | Split dock 0.94 asserted. | score | Asked in the elicitation. |
| 14 | Two different numbers both labelled "/mo": the card's economic cost of the hold ($6,920 for Yarmouth) and the calculator's payment ($6,210). | page, `costs.yaml` | One vocabulary (`USABILITY-SPEC.md` §1): Monthly payment is the only "/mo"; the hold cost is shown as a 5-year total. `hold.cost_of_capital` derived from `hold.mortgage_rate` and `hold.opportunity_rate` so the rank and the calculator share one rate. |
| 15 | "+$1,710 /mo extra, for no more house" on the rail, with a sentence that calls a house 14 points higher "about the same". | page | Overpay removed from the card. Its one legitimate use survives as a line under "Before you offer" in the showing record (`USABILITY-SPEC.md` §4.3). |
| 16 | The 18 `mech_ages_stated` claims and the four `*_year` inputs Opus added to the showing record are not connected to `cost()`. | `cost()` | `USABILITY-SPEC.md` §4.4; same fix as item 3, using the field names the page already has. |

## 8. Display

Specified in `USABILITY-SPEC.md` §6, which supersedes the earlier sketch here. The short form:
rail is rank · Score · Grade · Monthly payment · Band; the score panel is eight `.sp` bars in
weight order with the weight as the right-hand figure; the money block is Monthly payment,
Day-one work, Wish list, 5-year cost, Cash on closing day; overpay, `$/sq ft`, `Best value`,
`Frontier` and the needs-work bar are gone from the page.

## 9. Browsing

None for v6 itself. The elicitation is a conversation. Two stage-1 page loads are recommended
before the pass and were recommended last time: Middlesmoor's second bedroom (decides a gate) and
room tables for the 12 listings without one (makes the layout component consistent across the
batch; today the 12 cannot lose a bedroom to the tiny-room rule and the other 25 can). No photo
pass. If you say no, v6 ships with those two gaps named on the page.
