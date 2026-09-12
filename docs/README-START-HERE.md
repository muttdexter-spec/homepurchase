# First House, handoff package

**Owner:** Alex, Burlington Ontario. Buying a first house with his fiancée.
**Packaged:** 12 September 2026. **Updated the same night:** all 37 listings photo-graded, model v3.1. Read `QA-PASS-2026-09-12.md` for what changed and why.
**Read this file first. It is the only orientation you need.**

---

## 1. Where the work stands

37 listings in Burlington and Oakville (both saved searches) have been run end to end through the v3.1 model,
every one with a full-resolution photo pass. The walkthrough page now carries a card for all 37. The deliverable the buyers actually use
is a walkthrough companion page they open on a phone while standing in each house.

| Thing | Where |
|---|---|
| Walkthrough page, live and updatable | Artifact `5850ab7f-6b24-4efa-ba6d-483d4cfb924c`, titled *Walking the Shortlist* |
| Same page, offline copy | `deliverables/Walking-the-Shortlist.html` |
| Same page, printed | `deliverables/Walking-the-Shortlist.pdf` (36 pp) |
| The 37-row decision table | `v3-current/out/decision.csv` |
| Rebuild everything after an edit | `v3-current/refresh.sh` (score, detail, agent questions, tests, page) |
| Questions for each listing agent | `deliverables/agent-questions.md` |
| What the QA pass changed | `QA-PASS-2026-09-12.md` |
| Per-line renovation costs | `deliverables/renovation-cost-detail.md` and `v3-current/out/detail.json` |

To update the artifact from a new chat you must pass its URL as the `url` argument,
otherwise you create a second artifact instead of updating this one.

### Top of the table after the QA pass

See `QA-PASS-2026-09-12.md` for the full 37-row before/after. Tania (A, $411/sf) still leads on size alone; Delaney (A−, $501) is the cleanest house in the set; Enfield, Ravine, Bunton, Columbus follow. One listing is a hard STOP: the Appleby sidesplit, MLS W13756188, on confirmed basement
moisture. It is row 19 of the full table.

---

## 2. The model in one page

Costs are bucketed by **when you pay**, not by what they are.

- **day1** is anything that must happen before or at move-in: safety, insurability, and work
  that costs roughly twice as much once furniture is in the house. Flooring and ceilings sit
  here for that reason. This is the number that competes with the down payment.
- **reserve** is age-driven component replacement (roof, furnace, A/C, water heater, windows),
  annualised into a monthly figure. It is a cost of owning, not a cost of buying.
- **wishlist** is kitchens, baths, basements, decks. Buyer's choice, buyer's timing.
  **It never enters the ranking.**

`true_cost = ask + day1_p80`. Rank ascending on `all_in_psf = true_cost / usable_sqft`,
where usable = above grade + 50% of below grade, 65% if the basement walks out.

Three rules that are load-bearing and must not be quietly relaxed:

1. **Photos demote, never promote.** No photo may raise a condition call above `unverified`.
   There is no positive value for any `_verdict` field. A house with 40 immaculate photos is
   scored identically to one with no photos.
2. **p80 is taken on the sum**, by simulating 4,000 Beta-PERT draws over the line items, never
   by adding each line's p80. Adding worst cases inflates the total by 15 to 40%.
3. **The grade contains no price and no condition.** It scores size, layout, baths, lot,
   location and parking on absolute thresholds, so a listing graded today is comparable to one
   graded in March. Dividing a facts-only score by dollars does not double-count.

A job nobody can see is priced at the probability it has never been done: 70% pre-1990,
45% for 1990 to 2004, 20% for 2005 or later. Reading every tell at full resolution pulls that
toward a 15% floor. A confirmed defect pins it at 100%. One discovery contingency is applied
once, to day-one work only, by era: +25% pre-1980, +18% for 1980 to 1999, +12% after.
HST at 13% sits on top.

### v3 deleted two things from v2 on purpose

- The **gut band** (a 3-valued constant that overrode the whole cost build above a threshold).
- **Neighbourhood ceilings in the verdict.** Every ceiling in this model is a provisional guess,
  so none of them gate a decision any more. They survive only in the resale estimate.

---

## 3. How to re-run it

```bash
cd v3-current
python3 score.py observations.json out/          # writes out/decision.csv
python3 export_detail.py                         # writes out/detail.json, per-line costs
```

`score.py` needs `pyyaml`. Nothing else.

### Adding a new listing

**Stage 1, data only, every listing, about 800 tokens.**

1. Navigate to the OneHome URL. Wait 6 seconds.
2. Paste `crawl_fixed.js` into the browser JS tool, then run
   `JSON.stringify(await window.__data())`.
3. Append the record to `observations.json`.
4. Re-run `score.py`.

**The gate.** Stop and report without touching photos if the listing is grade C− or D, or if
`true_cost` is above the buyer's ceiling. Roughly one in three survives.

The published gate also stops anything more than 15% above the batch's best `$/sq ft`.
**That rule is broken and was deliberately overridden in the second batch.** Tania at $418/sf
reset the floor to $481, which would have killed two A− listings on nothing but the presence of
one unusually large house. Fix it before reusing it: exempt grade A and A− from the $/sq ft
gate, or band the comparison by size. It is currently the only known defect in the process spec.

**Stage 2, photos, survivors only, about 7k tokens.** Follow `v3-current/stage2_brief.md`
exactly. It contains the corrected loader and the locate-then-read protocol.

---

## 4. Gotchas that cost real time to discover

**Do not read these into context.** `listings_graded.csv` and `listings_master_graded.csv`
in the project are roughly 40k tokens each. Query them with a script, never with Read.

**Never click accordion headers on ITSO listings.** It triggers an "Unlock The Full Experience"
account gate and the session is done. Only "Read More" is safe to click.

**Never paste photo URLs into output.** They are signed JWTs and they are long.

**Photo discovery matches `GetMedia.ashx`,** not the host name. Matching on `matrixmedia`
works on ITSO and silently returns nothing on TRREB.

**Size:3 links cannot be minted.** The `t=` query parameter is a signature-verified JWT
carrying `Size` and `Number` claims. Editing the payload gives a 403. Full-resolution images
only materialise in the DOM after the gallery opens.

**The gallery trigger is the "View All N Photos" button,** not the hero image. Clicking the
hero only expands a thumbnail strip and no Size:3 image is ever requested. `__photos_load`
in `stage2_brief.md` has the corrected selector with the image click as a fallback.

**Take the photo count from `window.__P.length`,** not from a counter in the page text. The
regex read the wrong element on TRREB and returned 21 on a 40-photo listing.

**Locate before you magnify.** At 78px on a contact sheet you cannot tell where in a frame the
sink is, so crop coordinates guessed off the sheet come back uninformative. Do a fit-zoom pass
first at `zoom = 240 / natural_w`, about 0.23 for a 1024px source.

**Count the tiles in the first row of the contact sheet** before converting grid positions to
indices. It wraps at `floor(viewport_width / (tile_width + 1))`. Assuming 8 when it was 9 put
every single crop in the wrong room.

**Past about 3x you are magnifying pixels, not resolving detail.** The source is about 1024px
wide. If 3x does not settle a field, it is `not_shown`.

**The device bridge drops.** It went down for about 11 hours mid-batch once. Do all
browser-independent work meanwhile and write partial state to the project so nothing is lost.

---

## 5. Bugs already fixed, so you do not refix them

| Bug | Fix | Where |
|---|---|---|
| `"$5,411"` parsed as `5`, `"1,205 sqft"` as `1` | strip thousands separators before the number regex | `crawl_fixed.js` FIX 1 |
| Field names differ between TRREB and ITSO | accept a candidate list per field | FIX 2 |
| Lot arrives as `"40 x 110"` in one field | parse `Lot Size Dimensions` when Frontage/Depth are absent | FIX 3 |
| Beds arrive as `"3+1"` | prefer the explicit above/below split, fall back to parsing | FIX 4 |
| Absent garage field read as zero | look for "Garage" in the features string | FIX 5 |
| `h1` is not the address on these pages | regex the body text for `..., Burlington, ON L7x xXx` | FIX 6 |
| TRREB age bands ("16-30", no year) priced at the pre-1990 prior | `eff_year()` in `score.py` v3.1: year_built, else `year_built_est`, else the band's older end. (The earlier claim that this was fixed was wrong; it was patched into one record by hand.) | `score.py` |
| `usable()` counted zero basement when MLS gave no area while `cost()` charged 45% of above-grade to finish it | both use `below_grade()`: 70% of footprint, flagged `bg_sqft_est` in decision.csv | `score.py` v3.1 |
| The walkthrough calculator double-counted property tax | `monthly_carry` in `decision.csv` is **tax/12 + reserve**. The calculator was adding tax again on top. Reserve-only figures are $192 / $176 / $147 by era | fixed in artifact v3 |

---

## 6. The numbers most likely to be wrong

Ranked by how much they move the answer.

1. **`arv_psf_renovated`: $720/sq ft Burlington, $790 Oakville.** Both derived from *asking*
   prices, because no sold data exists in this model. Everything downstream moves with them.
   A $60 error changes several resale figures by six digits. On the largest houses the flat
   rate overshoots what the pocket actually pays, so headroom there is an upper bound.
   **Getting sold $/sq ft per pocket from the agent is the single highest-value next action.**
   A hedonic fit on the 28-listing ask corpus returned R²=0.26 with an implausible size
   coefficient; the corpus is price-filtered so it cannot be fit on. Do not retry that.
2. **`observed_floor = 0.15`.** The probability floor a job reaches when every tell reads clean.
   It is anchored on one worked example from the v2 spec and is otherwise unsupported.
3. **Unsourced catalog lines.** Kitchen and bath figures come from published Ontario contractor
   ranges. Everything marked `UNSOURCED` in `costs.yaml` is a working estimate: rewire, oil to
   gas, waterproofing, panel, asbestos, furnace, A/C, water heater. Replace with quotes.
4. **The 70% basement-area estimate** (`below_grade_estimate_factor`) drives 17 of 37 rows' usable area. Calibrated on 20 stated areas; replace with stated areas from the agent where it matters (Enfield, Columbus, Hazelwood, Pinemeadow).

---

## 7. The finding that matters most

**Not one of the 37 listings contains a photograph of an electrical panel, and only four show any mechanical equipment.** Across houses built between 1954 and 1999, that is the largest single gap in
all of this work. Every house therefore carries the full component reserve. Two questions to
the listing agent close most of it:

1. How old are the roof, furnace and air conditioner?
2. Are any of the photos virtually staged or digitally enhanced, and when were they taken?

---

## 8. What is in this package

```
README-START-HERE.md          this file

deliverables/
  Walking-the-Shortlist.html            standalone, works offline, calculator live
  Walking-the-Shortlist.pdf             all 37 cards expanded, for showings
  walking-the-shortlist.artifact-src.html   body-only source the Artifact tool publishes
  renovation-cost-detail.md             per-line costs for all 37, markdown (build_cost_detail.py)
  (rooms.js / costs.js removed: the page now renders from v3-current/out/ via build_walkthrough.py)

v3-current/                   THE LIVE MODEL. Start here for any new work.
  SKILL.md                    the two-stage process spec
  costs.yaml                  every tunable number, each with a source note
  score.py                    costing, value, verdict, grade (v3.2)
  test_model.py               invariants; refresh.sh runs it
  build_agent_questions.py    per-listing agent questions from the records
  build_walkthrough.py        regenerates the walkthrough page from out/ (all cards)
  build_cost_detail.py        regenerates deliverables/renovation-cost-detail.md from out/
  walkthrough_template.html   the v3.0 hand-built page, kept as style/JS template
  crawl_v3b.js                Stage 1 crawler with remarks + room table (use this)
  stage1/, stage2/            per-listing records from the 12 Sept pass
  live_2026-09-12.json        the 33 listings on the saved searches that night, with URL template
  export_detail.py            emits per-line costs to out/detail.json
  crawl_fixed.js              earlier Stage 1 crawler (superseded by crawl_v3b.js)
  crawl.js                    superseded, kept so the fixes are diffable
  stage2_brief.md             photo forensics protocol, corrected
  observations.json           37 records, the model's only input
  report_data.json            flattened view used to build the walkthrough page
  out/decision.csv            the 24-row decision table
  out/detail.json             per-line costs, value math, grade breakdown

v2-superseded/                the earlier model. Reference only.
  cost_model.yaml, run_model.py, intake_brief.md, gen_showing.py
  obs/observations.json, out/*.csv, out/*.md
  tests/overton.json          the calibration fixture v2 had to reproduce exactly

project-docs/                 copies of the "First House" project doc set
```

The `project-docs/` copies are here so this package stands alone. If the new chat is attached
to the **First House** project, prefer the project's own copies, since those are what the user
sees across Claude and are the ones that stay current.

---

## 9. Suggested next moves

1. Ask the agent for sold $/sq ft in Headon, Shoreacres, Orchard, Palmer, Roseland, Freeman,
   Brant Hills and LaSalle. Replace `arv_psf_renovated`. This is worth more than any other
   single input.
2. Ask for roof, furnace and A/C ages on the five SEE FIRST listings. Each date collapses a
   reserve line.
3. Done 12 Sept: gate fixed, every listing photo-graded, page generator written.
4. Ask Oxlow's agent why the remarks say in-ground pool; ask Tania's which photos are virtually staged.
5. After each showing, divide the buyer's own gut renovation estimate by the model's p80.
   Consistently above 1.0 means the provisions are too soft. That ratio is the only real test
   of this model.

### Renovations-needed list (added 12 Sept, evening)
Every card, the whole-table, `decision.csv` (`renovations_needed`, `reno_if_all_done`) and
`renovation-cost-detail.md` now carry a plain list of jobs with a cost each, e.g. "kitchen $73k; main bath $26k".
The cost is what the job costs IF DONE (PERT mean, era contingency and HST in, rounded to $1k), not the
probability-weighted figure in the line-by-line table. A job appears when p >= 0.5; "(unseen)" or "?" marks a
job priced at the era base rate because the photos never showed it; jobs at 0.2 <= p < 0.5 are listed as
"possible". Reserve items (roof, furnace, A/C, water heater, windows) are excluded: they stay in the monthly figure.
Code: `reno_list()` / `reno_text()` in score.py. The simulation is now seeded per listing, so decision.csv,
detail.json and the page always show the same day-one figure.

---

## 7. The showing record (added 12 September 2026, after the QA pass)

The walkthrough page is no longer read-only. Every card carries a **Showing record** that asks, per
listing, exactly the fields `score.py` is still guessing at, using the model's own enum values:

- **Settle what the photos couldn't.** For each of the 15 `TELLS` (plus `secondary_bath_original`)
  that is null or `not_shown` on that listing, the card renders the real options as chips
  (`undermount` / `topmount`, `flat_painted` / `stipple_popcorn`, …) with a hint of what the line is
  worth and the probability it currently carries. Answering is a model input, not a tick.
- **Dates off the equipment labels** — roof, furnace, A/C, water heater, panel amps, rented
  equipment. Captured as `mech_confirmed`. **`score.py` does not consume these yet**: reserve is
  still charged at p=1.0 for every house. Wiring an age-aware reserve is the single biggest
  remaining lever (the reserve is $147/mo on almost every listing) and is the next model change.
- **Two check lists.** The listing-specific concealed surfaces and red flags, plus fourteen generic
  checks asked of every house (pressure, basement smell, windows, floor slope, sump, grading, panel
  amperage, supply line material, attic, garage fit, noise, cell signal, bath fans, door latching).
  Each is fine / problem with a note.
- **A verdict and a gut score each**, plus free notes.

**Storage.** The page declares the `db` capability, so records are written server-side and shared
across every device signed into the owning account; the standalone HTML falls back to
`localStorage`. Two consequences: a db artifact is organization-internal and cannot be shared
publicly, and a second person needs to be a member of the same org (or use the same signed-in
device) to write into the same record.

**The loop.** *Export notes* on the control bar emits
`{observations_patch: {<slug>: {<field>: <value>, mech_confirmed: {...}, showing_flags: [...],
showing_verdict: ...}}, showings: {...}}`. Merge `observations_patch` into `observations.json`,
run `refresh.sh`, and the ranking rebuilds on what was actually seen rather than on the era prior.
A future session can also read the records directly out of the artifact's store rather than waiting
for an export.

**Filters.** All / Not walked / Walked / Shortlist, with a summary strip that re-sorts the filtered
set by `$/usable sq ft`. The page deliberately does **not** re-price live: p80 needs the 4,000-draw
simulation, so the authoritative re-rank stays in `score.py`.

Code: `v3-current/showing.py` (questions, markup, CSS), `v3-current/showing.js` (runtime),
wired into `build_walkthrough.py`. Rebuild with `refresh.sh` as before.
