# Elicitation: the fifteen minutes that set the ranking

Run this in Cowork with Alex, then again with his partner, separately and without showing either
the other's answers until both are recorded. Record answers verbatim into
`pipeline/costs.yaml: weights` in the format at the end. Do not compute or show a v6 ranking to
either person before their answers are recorded; the point is to elicit what they want, not what
the list would look like.

The method is swing weighting (SMART/SWING). It works because it asks about concrete ranges in the
actual batch, not about abstract importance. Use the houses named below so every swing is
something they have looked at.

## Part A. The eight swings, in this order

Say: "Imagine a house on the market right now that is the *worst* in the batch on all eight of
these. I can fix exactly one of them to the *best* in the batch. Which one do you want fixed?"

| Component | Worst in the batch | Best in the batch |
|---|---|---|
| Space | 1,012 sq ft bungalow, 568 Weir (basement with separate entrance) | 2,597 sq ft two-storey + finished basement, 3205 Tania |
| Layout | 2 bedrooms above grade, 275 Kent | 4 bedrooms, primary over 150 sq ft, 470 Delaney |
| Baths | 1 full + 1 powder, 493 Crosby | 3 full + 1 powder, 1273 Barberry |
| Parking | no garage, 4 spots, 2120 Cavendish | 2-car garage + 4 to 6 spots, 470 Delaney |
| Lot | 24 × 95 ft (2,269 sq ft), 1319 Bonnie | 59 × 155 ft (9,154 sq ft), 522 Enfield |
| Location | walk 30 / transit 30, 1218 Oxlow | walk 70 / transit 50, school within 500 m, 493 Crosby |
| Condition | $211k of expected work, 522 Enfield (kitchen and both baths original, oil, 1954) | $43k of expected work, 1218 Oxlow (every finish reads clean at full resolution, heat pump 2024) |
| Price | $7,000 a month to own before any work, 659 Cherrywood | $4,500 a month, 522 Enfield |

Then: "That one is fixed and gets 100. Of the seven left, which next?" Repeat until all eight are
ordered. Write the order down.

Then, for each in that order from the second onward: "The first swing you picked was worth 100.
On the same scale, how much is this one worth?" Accept any number 0 to 100. Ties are fine. Zero
is fine and means the component leaves the ranking for this person.

Record the eight raw numbers. Normalise to sum 100 for the yaml.

**Sanity check before moving on.** Read the normalised weights back: "So space is 18, condition
22, price 11, …" and ask if that sounds like them. If they flinch at one, adjust it and note that
it was adjusted. Do not argue.

## Part B. Gates and switches, one question each

1. "Minimum bedrooms above grade: two, or three?" (Kent and Middlesmoor are 2 + basement. A yes to
   two puts them in the rank.) → `gates.min_beds_ag`
2. "Would you take on a house that needs more than about 15% of its price in work, if the price
   were right? Enfield is the case: $825k asking, $211k of work." yes / no → `gates.no_projects`
3. "Do split-levels bother you enough to mark them down 6%? Twelve of the 37 are splits." yes / no
   → `split_dock` 0.94 / 1.0
4. "Between Burlington and Oakville, does one matter to you on its own, beyond what the score
   already measures? If so, how much on a 0 to 100 location scale, for the one you prefer?"
   → `location.municipality_bonus: {Oakville: 0..100 or Burlington: 0..100}`, added to the
   location component and capped at 100. Zero is the expected answer; ask anyway, because the
   asks say the market thinks Oakville is worth 11.5% and the score has no term for it.
5. "How long do you expect to stay? Three to five years, or seven to ten?" → `hold.years_default`
   3, 5 or 10.
6. "If you have the numbers: cash available for closing, and a monthly ceiling." → `gates.
   max_cash_to_close`, `gates.max_monthly` (null if not given; the page calculator can set them
   later).

## Part C. The cross-check, after both are recorded

Compute the v6 ranking under each person's weights and under the joint mean. Show each person
*their own* top ten only and ask one question: "Is there a house here you would not buy at its
asking price, and is there a house you like that is missing?" Each named house is a missing
term or a wrong weight; record what they say about it. Then show both the joint top ten and the
houses where their personal ranks differ by more than five, and let them talk. Record nothing
from that conversation except explicit changes to a weight.

## Output format

```yaml
weights:                                  # ELICITED 2026-09-13 by swing weighting. Raw 0..100, normalised in code.
  alex:    {space: 0, layout: 0, baths: 0, parking: 0, lot: 0, location: 0, condition: 0, price: 0}
  partner: {space: 0, layout: 0, baths: 0, parking: 0, lot: 0, location: 0, condition: 0, price: 0}
  joint:   mean                           # or an explicit dict if they agreed a different blend
  swing_order:
    alex:    [condition, space, ...]
    partner: [...]
  adjusted_after_readback: []             # e.g. ["alex: price 8 -> 14, said 8 felt too low"]
  cross_check_notes: []                   # e.g. ["partner: would not buy Tania at ask, 'it feels like a project'"]
gates:
  min_beds_ag: 3
  no_projects: false
  project_share_of_ask: 0.15
  max_cash_to_close: null
  max_monthly: null
split_dock: 0.94
location:
  municipality_bonus: {}
hold:
  years_default: 5
```

Time: about fifteen minutes each for Part A and B, ten for Part C.

---

# Recorded, 14 September 2026

**This section is the record of what actually happened. The script above was not completed and its
method is no longer the one in use.**

## What was asked, and what came back

Part A was put to Alex as written: the eight swings, the batch houses at each extreme, one question
at a time. He answered "Just do what you think is best." Told that the weights are the one input
the assistant is not allowed to supply, he was offered two routes: the full script, or a single
line giving the order of the eight, from which rank-order centroid weights would be derived and
recorded as order-derived rather than stated. The assistant wrote an example ordering into that
offer. He replied "do that", and then, to the read-back, "What are the recommended weights? Do
that."

So the numbers that went on file are **rank-order centroid applied to the assistant's own example
sentence**. They are not elicited weights and they are not recorded as such. `costs.yaml` says so,
in `weights.method.alex`, and the page stamps every card `Weights provisional`.

Part B was answered directly and those answers are real:

| Question | Answer | Where it went |
|---|---|---|
| Minimum bedrooms above grade | 2 | `gates.min_beds_ag: 2`. Kent and Middlesmoor return to the rank. |
| A house needing more than 15% of its price in work | Yes | `gates.no_projects: false`. Enfield is ranked with a Project stamp. |
| Split-level dock | "Mark to 5%" | `split_dock: 0.95`. He was offered 0.94 or 1.0 and gave a third number, so the third number was recorded. |
| Burlington or Oakville on its own | "Both are fine" | `location.municipality_bonus: {}`. No municipality term. |
| How long you expect to stay | "3 to 7 years" | `hold.years_default: 5`. The answer straddles the script's 3 and 5; the straddle is recorded here. |
| Cash and monthly ceilings | "Ignore this constraint" | `gates.max_cash_to_close: null`, `gates.max_monthly: null`. |

His partner was not available. `weights.partner: pending`.

Part C was run: the top ten under the provisional weights was shown, and the one question asked. He
deferred both answers to a review with his fiancee. `weights.cross_check_notes` is empty and no
weight has been changed on account of it.

## What replaced the swing-weight script

Swing weighting asks a person to invent eight numbers on a scale they have never used. That is what
failed here, and it is a known failure mode of the method rather than anything particular to this
buyer.

From 14 September the elicitation is **fifteen forced choices between two real houses from this
batch**, answered on the page, one set per person, with the weights fitted from the choices. There
are no numbers to give. The design and the fit are specified in `ranking-system-v6.md` section 7;
the pairs are in `pipeline/out/pairs.json` and the fit is `pipeline/fit_choices.py`.

Both buyers answer on their own phones, from the built page, and paste the exported
`preferences_patch` block back. Until both have answered, the page carries `Weights provisional` on
every card and in the mast, the joint column is whoever has answered, and no `Disagree` stamp can
appear.
