# First House scoring system: review package

Packaged 2026-09-12 for an independent model review. Everything needed to reproduce, critique
and rewrite the scoring is in this folder. No network access is required.

**Owner:** Alex, Burlington Ontario, buying a first house with his fiancée in Burlington and
Oakville. Budget behaviour: asks run $825k to $1.30M, all-in after day-one work runs $909k to
$1.34M. Intended hold is undecided between 3 to 5 years and 7 to 10, and the system currently
does not use a holding period at all.

**What I want from you:** a review and redesign of how listings are **graded, scored and
ranked**. The cost model underneath is reasonably well tested and is not the primary target,
though defects found there are welcome. Specific questions are in section 6.

---

## 1. What the system is

A two-stage pipeline over MLS listings from two saved searches (OneHome, boards ITSO and TRREB).

**Stage 1, every listing.** A browser script scrapes the listing page into a flat record:
price, taxes, above-grade and below-grade area, beds, baths, lot, parking, year built, room
table, remarks, photo count.

**Stage 2, survivors only.** A human-plus-model pass reads listing photos at full resolution
and fills 15 condition "tells" (sink mount, counter edge, soffit, door profile, tub type, tile
scale, vanity top, floor condition, main ceiling, window frame, electrical panel type, basement
ceiling, basement walls, basement moisture, driveway). Each tell is `not_shown` or a value.

Both stages write into `pipeline/observations.json`, which is the model's only input.
37 listings are in it, all photo-graded.

The design principle the whole thing is built around: **photos demote, never promote.** A house
with 40 immaculate photos is scored identically to a house with no photos. This exists because
the previous version of the system graded a listing (2450 Overton) an A and called it
"genuinely renovated"; the buyers walked it and it needed a full gut. Any redesign must keep
this property or argue explicitly for replacing it.

## 2. How the numbers are produced

`pipeline/score.py` (450 lines) does all of it. Run `sh pipeline/refresh.sh` (needs python3 and
pyyaml) to regenerate everything. Every tunable is in `pipeline/costs.yaml` with a source note.

**Costing.** Each unobserved job is priced at the probability it has never been done: 0.70
pre-1990, 0.45 for 1990 to 2004, 0.20 for 2005 or later. Reading the tells at full resolution
pulls that toward a 0.15 floor; a confirmed defect pins it at 1.00. Costs are bucketed by
**when you pay**:

- `day1` is anything required before or at move-in: safety, insurability, and work that costs
  roughly twice as much once furniture is in (flooring, ceilings sit here for that reason).
- `reserve` is age-driven component replacement (roof, furnace, A/C, water heater, windows),
  annualised into a monthly figure.
- `wishlist` is kitchens, baths, basements, decks. **Currently excluded from the ranking.**

An era contingency (+25% pre-1980, +18% 1980 to 1999, +12% after) is applied once to day-one
work, then 13% HST. The p80 is taken on the **sum** via 4,000 Beta-PERT draws, seeded per
listing, never by adding per-line worst cases.

**The fact grade** (`facts()`, score.py line 272; weights in `costs.yaml: fact_weights`).
Absolute thresholds, no price, no condition, so a listing graded today is comparable to one
graded in March:

| Component | Points | Basis |
|---|---|---|
| size | 25 | above-grade sq ft, linear from 1,000 to **2,600, then capped** |
| layout | 20 | effective bedrooms (a bedroom under 60 sq ft does not count), primary bedroom size |
| baths | 20 | full baths, plus 2 for a powder room |
| lot | 15 | frontage x depth, linear 4,000 to 9,000 sq ft |
| location | 12 | walk score + transit score, plus school proximity |
| parking | 8 | garage spaces x 3 + surface spots |

Sidesplits and backsplits take a 0.94 multiplier. Bands: A 78, A− 72, B+ 66, B 60, B− 54,
C+ 48, C 42, C− 36.

**The verdict** (`verdict()`, line 297) is STOP / SEE FIRST / SEE. Hard stops are confirmed
basement moisture, unresolved buried oil tank, confirmed knob-and-tube. Warnings (oil tank,
in-ground pool, tenanted, virtual staging, day-one cash above 6% of list) block SEE FIRST but
change nothing numeric.

**The evidence stamp** (`evidence()`, line 315) is high / medium / low from tells seen out of 15,
photo count, and whether year built and basement area were estimated rather than stated. It is
displayed and **does not enter any score.**

**The ranking. This is the part under review.** One line, score.py line 379:

```python
rows.sort(key=lambda r: (r["ppsf"]))
# ppsf = (list_price + day1_p80) / usable_sqft
# usable = above grade + 50% of below grade, 65% if the basement walks out
```

That is the entire ranking. Rank 1 to 37 in `pipeline/out/decision.csv` is an ascending sort on
all-in dollars per usable square foot. Nothing else in the file influences position.

## 3. How it is surfaced

`pipeline/build_walkthrough.py` renders `out/decision.csv` and `out/detail.json` into a
single self-contained page, built in two variants. The buyers open it on a phone while standing
in a house.

- `site/index.html` routes by screen size to `full.html` or `mobile.html` (`?v=full` /
  `?v=mobile` overrides, remembered in localStorage).
- `site/full.html`, `site/mobile.html`: the 2026-09-12 builds, 37 cards. These are large
  (~830KB) because the data is inlined.
- Live at https://muttdexter-spec.github.io/homepurchase/ (public repo, GitHub Pages).

Each card leads with rank, the fact grade, the verdict, and **`$X per usable sq ft` as the
headline number** (`card()`, build_walkthrough.py line 210, and the sortable whole-table at
line 281). Below that: what is known, what to check in the house, questions for the agent, the
room table, the renovation list with a cost each, per-line cost detail, and a live cash-to-close
and monthly-carry calculator. `showing.py` / `showing2.py` add a per-showing checklist mode.

So the ranking is not a back-office number. It is the first thing on every card and the default
sort of the table, and it is what decides which houses get visited on a Saturday.

## 4. Known defects, already found

Do not spend review time rediscovering these, but do tell me if a fix I describe is wrong.

1. **The $/sq ft gate is broken and was overridden by hand.** The process spec stops any listing
   more than 15% above the batch's best $/sq ft. One unusually large cheap house (Tania,
   3,210 sq ft at $410/sf) reset the floor to $481 and would have killed two A− listings.
2. **`arv_psf_renovated` is $720/sq ft Burlington, $790 Oakville, both derived from asking
   prices.** No sold data exists in the model. Every resale, recovery and sunk figure inherits
   this. A hedonic fit on the 28-listing ask corpus returned R²=0.26 with an implausible size
   coefficient; the corpus is price-filtered, so it cannot be fit on. Sold $/sq ft per pocket is
   the highest-value missing input.
3. **`observed_floor = 0.15`** is anchored on one worked example and is otherwise unsupported.
4. **18 of 37 rows have an estimated basement area** (70% of footprint, flagged `bg_sqft_est`),
   which feeds `usable_sqft`, which is the ranking denominator.
5. **Unsourced catalog lines** (rewire, oil to gas, waterproofing, panel, asbestos, furnace,
   A/C, water heater) are marked `UNSOURCED` in costs.yaml and are working estimates.
6. **Not one of the 37 listings photographs an electrical panel**, and only four show any
   mechanical equipment, across houses built 1954 to 1999. Every house therefore carries the
   full component reserve.

## 5. The complaint that prompted this review

Ranking on $/sq ft is mostly a size sort. Measured on the 37 rows: `true_cost` spans 1.47x while
`usable_sqft` spans 2.53x, decomposing the variance of log(all_in_psf) puts about 88% of it in
the size term, and the correlation of published rank with `1/usable_sqft` is 0.83. Meanwhile
`recovered_pct` (23 to 67), `sunk` ($30k to $127k), `monthly_carry` ($501 to $787),
`wishlist_p80` ($51k to $210k), the evidence stamp, the liability warnings and the already
computed `rank_low`/`rank_high` sensitivity band all sit in the output and influence nothing.
Correlation of rank with the fact grade is −0.60, so a C− sits at rank 14 and a B− at rank 27.

Note one subtlety before concluding it is a simple double count: size enters the fact grade as
**above-grade** sq ft **capped at 2,600**, while the ranking denominator is **uncapped usable**
area including the basement. They overlap, they are not the same variable.

`proposals/claude-ranking-v4-proposal.md` is a replacement I have already drafted: gates, five
absolutely-anchored axes combined by weighted geometric mean, an evidence shrink, and ranking on
P(top 8) from the existing simulation. **It is a proposal, not a decision.** Disagree with it
freely; if it is wrong I would rather know now.

## 6. What I want reviewed

1. **Is the multi-axis composite the right shape at all**, or is there a better formulation for
   a single buyer with one decision to make (for example a utility function over money, or
   explicit stochastic dominance, or a simple lexicographic gate ladder)?
2. **Weights and anchors.** All of mine are asserted. Is there a defensible way to set them from
   this data, given 37 rows and no sold comps and no revealed preference from the buyer yet?
3. **The size question.** How should marginal square footage be valued for a first house held
   3 to 10 years, when 18 of 37 basement areas are estimated?
4. **Wishlist.** Currently excluded from the ranking as "buyer's choice, buyer's timing".
   Right or wrong?
5. **Uncertainty.** The p80 machinery exists but the output is a point rank. Is ranking on
   P(top 8) the right answer, or is there something better that stays legible on a phone?
6. **Evidence.** Should confidence shrink the score, gate the rank, or just be displayed?
7. **Anything in the cost model or the code that is plainly wrong.** `pipeline/test_model.py`
   holds 8 invariants per listing and currently passes, which is weak evidence of much.
8. **The presentation.** Whatever replaces $/sq ft has to fit on a phone card as one headline
   number plus a reason. If the better system cannot be surfaced that way, say so.

## 7. What is in this package

```
README-REVIEW-BRIEF.md          this file
proposals/
  claude-ranking-v4-proposal.md a drafted replacement, for critique, not a spec
pipeline/                       the live model, self-contained
  score.py                      costing, facts, grade, verdict, ranking (v3.2)
  costs.yaml                    every tunable, with source notes
  observations.json             37 listing records, the only input
  test_model.py                 8 invariants per listing
  refresh.sh                    score, detail, questions, tests, page build
  build_walkthrough.py          renders the site from out/
  build_agent_questions.py, build_cost_detail.py, export_detail.py
  showing.py, showing2.py, showing.js, showing2.js   per-showing checklist mode
  inject_showing.py, walkthrough_template.html
  crawl_v3b.js, crawl_fixed.js, crawl.js             Stage 1 scrapers
  SKILL.md, stage2_brief.md     the two-stage process spec and photo protocol
  report_data.json, rooms_legacy.json, live_2026-09-12.json
  out/decision.csv              the 37-row decision table
  out/detail.json               per-line costs, value math, grade breakdown
  out/score_report.txt, out/agent_questions.md
site/
  index.html, full.html, mobile.html, site-README.md
docs/
  README-START-HERE.md          the full handoff, deeper than this brief
  QA-PASS-2026-09-12.md         what the last QA pass changed and why
  photo-reno-grading-handoff.md the evidence hierarchy and observation schema
  photo-manipulation.md         virtual staging and AI tells
  testrun-overton.md            the reference run and the three spec bugs it found
  operating-manual.md, prompts.md, search-harvest.md, search-harvest-updated.md
  coverage-audit.md, renovation-cost-detail.md, agent-questions.md
  00-README.md, listings_live_queue.csv
```

Addresses, asking prices and condition grades for real listings are in here. It is public MLS
data, but it is assembled, so treat the package as private.
