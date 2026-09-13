# Changelog

## 15 September 2026: v6.1, the buyer anchors, location rebuilt, two new listings

**Four anchors that were the assistant's are now the buyer's**, recorded verbatim in `costs.yaml`
under `buyer_answers` before anything was computed. Payment: comfortable $6,000 a month, maximum
$7,000. Space: cramped below 1,300 sq ft, enough at 1,700. Yard: matters, small 3,000, plenty
7,000. Ensuite: he answered "unsure, do what you think is best", so `layout.ensuite_matters: true`
is the ASSISTANT'S choice and `buyer_answers.note_ensuite` says so in those words. Do not restate
it as elicited, for the same reason `weights.method.alex` exists.

**Price is anchored on the monthly payment, not the search band.** `price_component()` scores 100
at or under the comfortable payment and falls linearly to 0 at the maximum. `monthly_payment()` is
the single source of the "/mo" figure (P&I + tax + upkeep at the `costs.yaml` financing defaults),
so the component, the page calculator and the ceiling agree by construction. The old
`hold.price_anchor_per_year` path is still there and fires only if the `price:` block is removed.

**The payment maximum is a soft ceiling, not a gate.** `price.gate_at_max: false`. A house above it
scores 0 on price, stays in the rank, and carries an `Over your maximum` stamp naming the payment
and the overage. Set it true to restore the G3 exclusion. The consequence is recorded in
`costs.yaml`: price clamps at 0, so every house above the maximum ties there and the other seven
components order them. The alternatives were rejected because they make price relative to the
batch, and the eight absolute anchors exist so a house scored today compares to one scored in March.

**Location rebuilt on five parts** (`location.version: v61`): commute 30 to the nearest of five GO
stations, quiet 20 on the nearest of the QEW, 403, 407 and the rail corridor with a cul-de-sac
bonus and an arterial cap, walk and transit 25 unchanged, school 15, green and water 10. All of it
from geocoded addresses cached in `pipeline/geo.json`, which also records the geocoder, the
Overpass queries and the caveats. 39 of 39 geocoded to an exact house number. Spread widens from
50-100 to 41-96. The assigned-school lookup has NOT been done: the rating half sits at its midpoint
under `location.assigned_school_done: false`.

**Space, lot and layout on the buyer's numbers.** Space floor 1,000 to 1,300 and knee 1,800 to
1,700. Lot moves out of `fact_weights` into its own block at 3,000 and 7,000, which takes houses
scoring zero on lot from 10 of 37 to 3 of 39. Layout becomes bedrooms 0-80, primary over 150 sq ft
+10, ensuite +10, so a 4-bed with no ensuite no longer scores 100. `ensuite_with_basis()` reads the
room table where there is one and falls back to the bath count where there is not, and the card
says which decided it. Coverage is 11 yes, 7 no, 21 unknown.

**Two listings added, both with a full stage-2 photo pass.** 1333 Woodvale Place (rank 21) and 2379
Duncaster Drive (rank 36). The batch is 39.

**Fixed:** `mobile.html` scrolled horizontally at 360 px because `.sr-ctl` used a -16px negative
margin against an 11px parent padding. Both pages now render clean at 1280 and 360.

**Unchanged:** no catalog cost, recovery band, era prior or contingency moved. No CSS variable and
no card section order changed. The letter grade is still computed, still in `decision.csv` and
`detail.json`, and still rendered nowhere.

**Still open:** zero of the fifteen pairwise choices are on file for either person, so the weights
remain provisional. See `docs/QA-PASS-2026-09-15.md` section 7.

## 14 September 2026: rank v6, page v6

**Ranking, v5 to v6.** One score per house, 0 to 100, higher is better. Eight components, each on
an absolute 0 to 100 scale (space, layout, baths, parking, lot, location, condition, price),
combined with weights that come from the buyers and never from the batch. `own_mo - 120 * fit` is
gone, and with it `dollars_per_fit_point_mo`, `rank_value`, `fit_dollars_mo`, the dominance
frontier as an ordering rule, the needs-work score, the frontier chart and four scores on one card.
`overpay` is still computed and still in `decision.csv`; its one use on the page is a line under
"Before you offer". Specification in `docs/ranking-system-v6.md`.

**Condition is now two-sided**, and it is the cost model's own arithmetic rather than a new table
of asserted points: the cost-weighted share of this house's work that is not expected. A clean
full-resolution read can lower a finish line toward a floor of 15%, never to zero, never a
structural, envelope or mechanical line, and never far enough to reach the top of the range.
Photographs alone cap out around 77; nothing in the batch exceeds 80 without a showing, and
`test_model.py` fails if one ever does. `condition.photos_may_lower_p: false` restores the
demote-only rule of v5.

**`p_hold(age, life, H)`** replaces the flat reserve annuity in both condition and the hold cost. A
confirmed-original window now reaches the money over the hold instead of being spread over thirty
years. Its consequence is worth seeing: a 1999 to 2008 house scores worse on mechanicals than a
1960s house, because its furnace and A/C are original and at end of life.

**The band** is rank under every weight set on file, at 3, 5 and 10 years, at the low, point and
high end of the house's own day-one uncertainty. Nine rankings with one weight set, eighteen with
two.

**The weights are elicited by pairwise choice, not by swing weighting.** Swing weighting was run on
13 September and produced nothing usable; `docs/ELICITATION.md` records exactly what happened. From
14 September each buyer answers fifteen forced choices between real houses on the page, the pairs
chosen by greedy D-optimality on the difference vectors, and the weights are fitted by a
paired-comparison logit ridged toward the prior. New files: `pipeline/build_pairs.py`,
`pipeline/fit_choices.py`, `pipeline/out/pairs.json`.

**Other model changes.** The five `_seen` fields (`roof_seen`, `furnace_seen`, `ac_seen`,
`water_heater_seen`, `panel_seen`) with the vocabulary `original` / `replaced_<year>` / `new`, wired
to the four year boxes in the showing record. `reserve.pool_carry_annual` wired in as a real reserve
line. The G4 project gate. `hold.cost_of_capital` derived from `hold.mortgage_rate` and
`hold.opportunity_rate` rather than asserted. Gated rows write `-` rather than a rank above 90. No
catalog cost, recovery band, era prior or contingency changed.

**Buyer settings, elicited 14 September.** `min_beds_ag` 3 to 2, which returns Kent and Middlesmoor
to the rank. `no_projects: false`. `split_dock` 0.94 to 0.95. No municipality term.
`hold.years_default` 5.

**Page, v6.** One vocabulary, seven terms, and exactly one number carrying "/mo": Monthly payment,
computed by one `monthlyPayment()` and read by the rail, the money block, the table and the
calculator. Global settings in the control bar. One score panel with eight bars in weight order.
Every section below the money block collapsed by default, with a sticky mini-header. Per-person
showing record with a `who` selector. Compare view, Saturday plan with a Google Maps route and a
print sheet, calibration panel, per-person picks, the changes line, and an offline manifest and
service worker. Specification in `docs/USABILITY-SPEC.md`.

**Docs.** `ranking-system-v5.md` moved to `docs/superseded/` with a note that its section 8 was
stale on the day it shipped. The `- ]` checklist bug in `QA-PASS-2026-09-13.md` is fixed.

## 13 September 2026: model v3.4, rank v5, page v5

**Model, v3.2 to v3.4.** Six bug fixes from `docs/REVIEW-2026-09-12.md` section 5. No catalog
cost, recovery band, era prior or contingency changed; two new keys were added to `costs.yaml`.

- `"inish" in basement` matched "Unfinished", so unfinished basements were counted as finished
  and given an estimated area. Grand loses 400 usable sq ft, Crosby 281.
- "Partially Finished" was estimated as a full finished basement. New key
  `below_grade_estimate_factor_partial: 0.35`.
- `"alk" in basement` matched "Walk-Up", so three listings got the walk-out weight of 0.65 on
  below-grade area. Only a genuine walk-out earns it now.
- A clean floor read that the same record describes as concealed by a rug, mat or runner now
  counts as half a read, not a full one. New key `concealed_floor_read: 0.5`.
- Unknown build year skipped the pre-1970 electrical block. Caplan and Aldridge now carry panel
  and partial rewire lines, as they already did everywhere else worst case applies.
- Enfield was charged for a furnace twice, once in `oil_to_gas` and once in the reserve.

`out/decision.csv` on the fixed model is md5 `3442cb238e38a914ef43dee76036c5cb` before the v5
columns are added.

**Ranking, v5.** `all_in_psf` is no longer the sort. Gates first, then two numbers per house:
cost to own over the hold in dollars per month, and a facts-only score out of 100. The order is
`own_mo - 120 * fit`, lower first, so the grade leads and cost to own breaks ties between houses
that score the same. The $120 is `rank.dollars_per_fit_point_mo`, the only preference in the
ranking; it was elicited from the buyer on 13 September by showing the list under four settings.
Overpay against the dominance frontier is still computed and shown on every card, as the argument
for paying less rather than as the order. Specification in `docs/ranking-system-v5.md`.

- Space saturates at a knee of 1,800 sq ft above grade; below-grade area leaves the fit score
  and becomes a discrete amenity from MLS text. The 70% estimate stays in the costing.
- Condition subtracts up to 12 points, era-scaled, and only on a line the cost model puts at
  p >= 0.95. It can never add.
- `sensitivity()`'s five batch-wide input flips are replaced by a rank band from the model's own
  day-one draws, 1,000 re-rankings, p10 to p90. `rank_low` and `rank_high` are gone from
  `decision.csv`; `rank_p10` and `rank_p90` replace them.
- `costs.yaml` gains `hold`, `gates`, `fit_weights` and `rank`, including
  `rank.dollars_per_fit_point_mo: 120`, the elicited exchange rate that sets the order. Every new key has a reason or an
  `UNSOURCED` note. The four preference parameters are marked as defaults to replace after the
  elicitation in `docs/REVIEW-2026-09-12.md` section 2.9.
- `test_model.py` gains the six invariants from review section 5.13 and 19 rank invariants,
  among them that the file is ordered on `own_mo - lambda * fit` and that the two new columns
  `rank_value` and `fit_dollars_mo` agree with it,
  including that every listing's rank lies inside its own band and every frontier house has
  overpay zero.
- `rank_v5.py` was integrated into `score.py` and deleted, so the numbers come from one place.

**Page.** Both builds regenerated from the model; no CSS variable, font size, colour or card
section order changed, and the three `<style>` blocks are byte-identical to the previous build.

- Rail: overpay per month is the headline, own /mo and the rank band sit under it, and the rank
  number stays a number on every ranked house including the best-value five. `$/sq ft` moves to
  the cost breakdown, labelled "for reference, not the rank".
- A `why` line under the address names the house that dominates this one, with its grade and ask.
- Score panel gains a seventh row, Condition, always shown, with the subtraction spelled out.
- Money panel hero moves from day-one cash to own /mo. Day-one cash keeps its slot.
- A cost bullet bar under the money panel draws own /mo as a length, with a tick at the
  dominating house and the overpay as the gap.
- Table: `Own/mo` and `Over/mo` replace `$/sq ft`; one ranked block with the sort rule stated
  above it and the three gated listings in a group at the end; the band cell carries the 3-year
  and 10-year ranks as a tooltip.
- A hold toggle (3 / 5 / 10 years, default 5) rewrites the rail, the hero, the bullet bar and
  the table cells. It does not re-sort: the order is the 5-year rank and the masthead says so.
- A frontier chart, one inline SVG, in the table's section head.
- The ask-derived resale block (peer benchmark, worth after the work, recovered %, break-even)
  is no longer rendered on the card. It is still in `out/detail.json`. Only `sunk` is shown,
  because it is sourced and ask-free.
- The phone build's mini table was previously frozen in the page template with September 12
  data. It is now generated, and its jump links point at the card ids that exist
  (`#sr-lot-<house>`) rather than at `#h-<house>`, which never matched anything.

**Wording.** The page calls the frontier the **best-value houses** and overpay **extra per
month, for no more house**; `frontier` and `overpay` stay as the technical names in the glossary
and the docs. The howto block is a four-step explainer of gates, cost to own, how much house, and
the order. The score panel is headed "how much house" and says what its rows are before it says
what the colours mean. The three table group headers are sentences.

**Two fixes found by looking at the built page.** The showing-record runtime reorders the card
stack, the strip and the jump list by the `rank` field in `SHOW_DATA`, so the gated houses, which
were given rank 0, were appearing first in all three; they now sort last and read "not ranked".
The same runtime still described the old model in two strings, `$620/sf · model rank 16` and
"cheapest per usable foot first"; both now read cost to own per month.

**Build.** `build_walkthrough.py` now writes `full.html` and `mobile.html` at the repo root from
two templates, `pipeline/page_full.tpl.html` and `pipeline/page_mobile.tpl.html`, which hold the
page chrome with every model-produced region replaced by a placeholder.
`pipeline/make_page_templates.py` regenerates those templates from the built pages and is not
part of `refresh.sh`.

**Docs.** `docs/ranking-system-v5.md` added. `docs/HANDOFF-START-HERE.md` section 2 rewritten
(the file was `docs/README-START-HERE.md`). `docs/QA-PASS-2026-09-13.md` added.
`docs/REVIEW-2026-09-12.md`, `docs/DISPLAY-SPEC.md` and `docs/BACKLOG-optimizations.md` copied in
verbatim. `docs/ranking-system-v4.md` moved to `docs/superseded/`.

## 12 September 2026: model v3.2

All 37 listings photo-graded at full resolution, 13 listings added from the second saved search,
evidence grade, rank band, cash to close, HDR and tiny-bedroom rules, duplicate check. See
`docs/QA-PASS-2026-09-12.md`.
