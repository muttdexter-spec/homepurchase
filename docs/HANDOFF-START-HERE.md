# First House, hand-off. Read this first.

**Owner:** Alex, Burlington Ontario. Buying a first house with his fiancée.
**Current as of:** 13 September 2026, end of the v6 page-formatting session.
**Supersedes:** the 12 September version of this file. Everything below reflects rank v6, not v3 or v5.

> ## Update, 15 September 2026. Read `QA-PASS-2026-09-15.md` before the rest of this file.
>
> Everything below is still true about the model, the gotchas and the way Alex works. Five things
> have moved since it was written, and the 15 September QA pass is the record of each.
>
> 1. **The batch is 39 listings, not 37.** 1333 Woodvale Place and 2379 Duncaster Drive were added
>    on 15 September from OneHome links Alex supplied, and both have had a full stage-2 photo pass.
>    Woodvale ranks 21, Duncaster 36.
> 2. **Four buyer anchors are elicited** and sit in `costs.yaml` under `buyer_answers`: payment,
>    space, yard, ensuite. The ensuite one is the ASSISTANT'S choice, not his. Read
>    `buyer_answers.note_ensuite` before treating it as a preference, for the same reason
>    `weights.method.alex` exists.
> 3. **Price is no longer anchored on the search band.** It is the monthly payment (P&I + tax +
>    upkeep) against his comfortable and maximum figures, and the maximum is a soft ceiling with an
>    `Over your maximum` stamp, not a G3 gate. Section 2 of the QA pass records an error in the
>    figures he was shown when he answered, and what it costs.
> 4. **Location has been rebuilt** on five parts computed from geocoded addresses, cached in
>    `pipeline/geo.json`. Section 3 of the QA pass lists four caveats, each verified rather than
>    assumed.
> 5. **Space, lot and layout anchors have moved** to his numbers, and layout now carries an ensuite
>    term. Coverage of that term is worse than the spec assumed: 11 yes, 7 no, 21 unknown.
>
> Unchanged and still the biggest open item: **zero of the fifteen pairwise choices are on file**
> for either person. The weights are provisional and nothing may be computed from choices that do
> not exist. Section 3 below still governs.
>
> New files since this was written: `pipeline/geo.json`, `docs/QA-PASS-2026-09-15.md`,
> `docs/V6.1-REFINEMENTS.md`, `docs/USABILITY-ADDENDUM.md`, `docs/COWORK-PROMPT-v6.1.md`.

---

## 0. The three things a new chat gets wrong

1. **Do not compute, print or describe a v6 ranking as if the weights were the buyers'.**
   They are not. The weights on file are provisional and were derived by the assistant, not
   elicited from anyone. Section 3 explains. Every card on the page says `Weights provisional`
   for this reason, and that stamp does not come off until section 3 is done.
2. **Do not browse any listing or real-estate site** without asking first and getting a yes.
   Two stage-1 page loads are recommended in `RANK-V6-DECISION.md` section 9 and neither has
   been done. "Do what you think is best" is not the yes.
3. **Do not change any catalog cost, recovery band, era prior or contingency.** New keys only.
   Also standing: no em dashes in anything written for him, flat `pipeline/`, no dotfiles in an
   upload, and no redesign of the page beyond what he asks for in the moment.

Stop and ask him if: a folder does not reproduce; swing weights contradict each other (name the
two, do not resolve); a change would touch a catalog number; a house reads condition above 80
with no showing evidence; any number other than Monthly payment would carry "/mo".

---

## 1. Where everything is

| Thing | Where |
|---|---|
| Git clone he commits from | `C:\Users\alexa\Downloads\First House Analysis\homepurchase` |
| Remote | `github.com/muttdexter-spec/homepurchase`, branch `main`, public |
| Live page he checks | `https://homepurchase-rouge.vercel.app/full.html` |
| Phone page | `.../mobile.html` |
| Model and builders | `pipeline/` in that repo |
| The 37-row table | `pipeline/out/decision.csv` |
| Per-line costs | `pipeline/out/detail.json`, `deliverables/renovation-cost-detail.md` |
| The fifteen elicitation pairs | `pipeline/out/pairs.json` |
| Specification of the model | `docs/ranking-system-v6.md` |
| Why v6 replaced v5 | `docs/RANK-V6-DECISION.md` |
| How the weights are meant to be obtained | `docs/ELICITATION.md` |
| Last QA pass | `docs/QA-PASS-2026-09-14.md` |

**The clone moved on 13 September and this matters.** It used to sit inside OneDrive. OneDrive
hardlinked `full.html`, which meant a write through the device bridge could silently not land,
and a read-back refused with "file is hardlinked (nlink > 1)". One push lost a file that way and
it took a while to see. The clone is now outside OneDrive and round-trips cleanly. **Do not let
it move back under OneDrive.** The old OneDrive copy is dead; nothing writes to it.

**`device_bash` does not work on his machine.** A Windows update released 8 September stops the
workspace mounting his files. So: no `cp`, `mv` or `git` on his side. Files reach him only through
`device_commit_files`, and he runs the commit and push himself in GitHub Desktop. He prefers it
that way and has said so.

**Always verify a write by staging the file back and hashing it.** Not by assuming the call
succeeded. That is how the lost file was found.

---

## 2. The model in one page

One score per house, 0 to 100, higher is better, sorted descending. Full specification in
`docs/ranking-system-v6.md`; this is the shape of it.

```
score = sum_k w_k . comp_k / sum_k w_k        x 0.95 if the style is a split level
```

Eight components on **absolute** anchors, so a house scored today is comparable to one scored in
March and none of them moves when the batch changes: space, layout, baths, parking, lot,
location, condition, price.

**Condition** is `100 x (1 - work_expected / work_full)`, the cost-weighted share of work NOT
expected. `work_full` puts every probability at 1, `p_hold` included. That last clause is
load-bearing and was a real bug once: leaving `p_hold` in the denominator made the age term cancel
on exactly the lines it was added for, so a 1972 furnace read the same as a 2008 one.

**`p_hold(age, life, H)`** is the chance a component is replaced during the hold. It has a
consequence worth seeing before believing: a 1999 to 2008 house scores worse on mechanicals than
a 1960s house, because its furnace and A/C are original and at end of life while the 1960s
house's were replaced at some point.

**Price** is `100 x clamp((84,000 - cost_per_year) / (84,000 - 54,000))`. The anchors are the
search band, $270k to $420k over five years, expressed **per year** so the 3, 5 and 10 year
rankings in the band stay meaningful. At a flat five-year anchor every house clamps to zero at a
ten-year hold. That per-year reading is the assistant's, not his, and is flagged in the QA pass.

**Cost of capital is derived**, not asserted: `(1-down) x mortgage_rate + down x opportunity_rate`,
which at 20%, 4.25% and 3.0% is 4.0%.

**The band** is the rank under every weight set on file, at 3, 5 and 10 years, at the low, point
and high end of that house's own day-one uncertainty. With one weight set that is nine rankings.
The condition ends come from the p10 and p90 of the 4,000 day-one draws, entered as a **ratio**
against their own median rather than as a level, because the draws carry contingency, the
multi-room premium, HST and soft costs that the line-by-line sum does not.

**Gates** G0 to G4 are non-compensatory and run in order: STOP, min beds above grade, max all-in,
max cash to close, project share of ask. A gated listing is not ranked. HOLD (oil tank, in-ground
pool, sitting tenant) is stamped, never excluded.

**Gone from v5**, do not reintroduce: `dollars_per_fit_point_mo`, `rank_value`, `fit_dollars_mo`,
the dominance frontier as an ordering rule, the Best value and Frontier stamps, the needs-work
score, and the convention of writing 91 to 93 into `decision.csv` for gated rows. `overpay` and
`dominated_by` are still computed and appear in exactly one place on the page, under
"Before you offer".

**The letter grade is still computed** and still written to `decision.csv` and `detail.json` for
continuity, but since 14 September it is **rendered nowhere**. He asked for that explicitly: two
numbers measuring different things side by side, with no way to tell which one the list obeys, was
the confusion rather than the cure. Do not put it back on the page.

---

## 3. The weights, which is the biggest open item

**Read `docs/ELICITATION.md` before doing anything here, and read this paragraph twice.**

Swing weighting was tried on 13 September and failed. He was asked for an ordering and eight
numbers and gave neither. What actually happened: the assistant offered an example order
("for example: condition, space, price...") and he said "do that". The numbers now in
`costs.yaml` are a rank-order centroid on **that example order**, which means they are the
assistant's ordering, not his. `costs.yaml` says so in `weights.method.alex`, in those words. That
record is deliberate and must not be tidied up or restated as though he had ranked anything.

The replacement is **fifteen forced choices between real houses from this batch**, answered on the
page, with the weights fitted from the choices.

- `pipeline/build_pairs.py` selects the pairs by greedy D-optimality on the difference vectors,
  subject to at least three pairs per component with a difference of 30 or more, no house in more
  than four pairs, and no dominated pairs. It has already run: 15 pairs from 623 candidates,
  every component covered, max 2 appearances per house, 23 of 36 houses used. `out/pairs.json`
  is the output and both people must see the same fifteen.
- `pipeline/fit_choices.py` fits a paired-comparison logit, weights non-negative summing to 100,
  a free consistency parameter, and an L2 ridge toward the prior calibrated so a perfectly
  consistent respondent still moves every design-supported weight by at least 10 points. It
  returns `None` on a partial set. Fifteen answers or none.

**Current state: zero choices on file for either person.** He said he would answer the fifteen on
his phone from the built page and so would his fiancée. Until then, `weights.provisional` is true
for both and every card carries `Weights provisional` and `Partner weights pending`.

**His instruction, verbatim in spirit: do not compute anything from choices you do not have.**

When both sets arrive: run `fit_choices.py`, write the fitted weights into `costs.yaml` alongside
the method note, rebuild, and the band widens from nine rankings to eighteen. A `Disagree` stamp
goes on any house whose two personal ranks differ by more than 5; it cannot appear before then.

---

## 4. What else is outstanding

1. **Part C of the elicitation.** Two questions he has not answered: which houses in the top ten
   he would not buy at asking, and which houses he expected to see there and does not. The answers
   go into `weights.cross_check_notes` **verbatim**, and change no weight. They are a check on the
   weights, not an input to them.
2. **The fifteen choices**, from both of them. Section 3.
3. **The repo's `docs/` folder is still the 12 September set.** `README.md` links to five v6 docs
   that are not in the repo. He was offered a push of the twenty doc files and said he did not
   need docs in that push. Offer again rather than doing it unasked.
4. **Oxlow's pool.** The record's `pool` field says above-ground; the remarks say
   "in-ground pool (new liner 2025)". Currently resolved in favour of the remarks so acceptance
   passes, and flagged loudly in `QA-PASS-2026-09-14.md`. It needs a real answer at the next
   stage-2 pass, because in-ground triggers HOLD and above-ground does not.
5. **The two stage-1 page loads** in `RANK-V6-DECISION.md` section 9. Never done, both gaps
   stamped on the page. Ask before either.
6. **Option 2 on the score band** (a coarsened letter shown only in the table's Score column,
   thresholds A 70 / A- 65 / B+ 60 / B 55 / B- 50 / C+ 45 / C 40, defined once in the glossary as
   "the Score, coarsened"). Offered, not chosen. Current state is plain removal of the letter.

---

## 5. How to rebuild and ship

```bash
cd pipeline
python3 score.py observations.json out/     # writes out/decision.csv
python3 export_detail.py                    # writes out/detail.json
python3 test_model.py                       # must print PASS
python3 build_walkthrough.py                # writes ../full.html, ../mobile.html, ../sw.js, ../manifest.json
```

`score.py` needs `pyyaml`; `fit_choices.py` and `build_pairs.py` need `numpy` and `scipy`.
Render at 1280 and 360 with headless Chromium before shipping anything visual. He notices layout
problems immediately and will send a screenshot.

Then commit the changed files to his clone with `device_commit_files`, stage them back, hash them,
and tell him it is ready. He commits and pushes in GitHub Desktop, Vercel redeploys.

**The service worker was a trap once and the fix must not be undone.** The first version was
cache-first against a fixed cache name `walk-v6`, so it served whatever it cached on the first
visit and never checked again, and because `sw.js` itself never changed byte for byte the browser
never installed a replacement. **A deploy could not reach anybody who had already opened the
page.** It is now network-first with a cache fallback, the cache name carries the build hash,
install calls `skipWaiting`, activate calls `clients.claim`, and the page reloads itself once on
`controllerchange`. If you touch `write_offline()`, test the old-to-new upgrade path over a local
`python3 -m http.server` before shipping.

If he reports a stale deployment: fetch `sw.js` and `full.html` from the live URL and compare
against the build. That is how the last one was diagnosed, and the cause was a lost file, not the
worker.

---

## 6. Current state of the page

Card body order, top to bottom, which he arrived at over several rounds of notes and is now settled:

1. Head: address, facts line, stamps, money block, score panel on the right
2. The blue **Price and financing** panel
3. **Why each score**, collapsible, one sentence per component in that house's own numbers
4. The take, one paragraph from the record
5. **Renovations**, always shown, with the line-by-line detail folded inside it
6. **Settled by the photos** and **Check when you're there**, side by side, always shown
7. **Ask before you go**
8. **Showing record**, last, the only section that starts closed

On 13 September a formatting pass collapsed six label sizes to one 9.5px mono scale, four money
figure sizes to one 17px, the prose sizes to 13.5px, and gave the blue panel, Renovations and
Ask-before-you-go one shape. All three collapsibles now use the same caret. No catalog number
moved and no score changed.

Things he asked for and that should stay: "Add to View List" not "Add to Saturday"; compare rows
removable once selected; room-driven score always visible with details expandable; table values on
the right centred; monthly payment unbolded in the table; no letter grade anywhere.

---

## 7. Gotchas that cost real time to discover

These are from the crawling and photo work and are all still true.

**Do not read `listings_graded.csv` or `listings_master_graded.csv` into context.** Roughly 40k
tokens each. Query them with a script.

**Never click accordion headers on ITSO listings.** It triggers an account gate and the session is
over. Only "Read More" is safe.

**Never paste photo URLs into output.** They are signed JWTs and they are long.

**Photo discovery matches `GetMedia.ashx`,** not the host name. Matching on `matrixmedia` works on
ITSO and silently returns nothing on TRREB.

**Size:3 links cannot be minted.** The `t=` parameter is a signature-verified JWT. Editing the
payload gives a 403. Full-resolution images only appear in the DOM after the gallery opens, and
the trigger is the "View All N Photos" button, not the hero image.

**Take the photo count from `window.__P.length`,** not from page text.

**Locate before you magnify**, and count the tiles in the first row of the contact sheet before
converting grid positions to indices. Assuming 8 when it was 9 put every crop in the wrong room.
Past about 3x you are magnifying pixels; if 3x does not settle a field it is `not_shown`.

**The device bridge drops.** It was down about 11 hours mid-batch once. Do browser-independent
work meanwhile and write partial state to the project.

---

## 8. The numbers most likely to be wrong

Ranked by how much they move the answer.

1. **`arv_psf_renovated`: $720/sq ft Burlington, $790 Oakville.** Both derived from *asking*
   prices, because there is no sold data in this model. A $60 error changes several resale figures
   by six digits. **Getting sold $/sq ft per pocket from the agent is the single highest-value
   next action.** A hedonic fit on the 28-listing ask corpus returned R-squared 0.26 with an
   implausible size coefficient; the corpus is price-filtered so it cannot be fit on. Do not retry
   that.
2. **`observed_floor = 0.15`,** the probability a job reaches when every tell reads clean.
   Anchored on one worked example and otherwise unsupported.
3. **Unsourced catalog lines.** Everything marked `UNSOURCED` in `costs.yaml` is a working
   estimate: rewire, oil to gas, waterproofing, panel, asbestos, furnace, A/C, water heater.
4. **The 70% basement-area estimate**, which drives 17 of 37 rows' usable area.

---

## 9. The finding that still matters most

**Not one of the 37 listings contains a photograph of an electrical panel, and only four show any
mechanical equipment**, across houses built between 1954 and 1999. Every house therefore carries
the full component reserve, and with `p_hold` that is now doing real work in the ranking. Two
questions to the listing agent close most of it:

1. How old are the roof, furnace and air conditioner?
2. Are any of the photos virtually staged or digitally enhanced, and when were they taken?

---

## 10. How he works

He sends short, precise notes, often several at once, often with a screenshot and a "remove this"
or "move this". Take them literally and one at a time. He catches modelling errors himself and has
caught at least three real ones, including the `p_hold` denominator and false precision in the
band, so when he says a number looks off, it usually is. He wants the reasoning behind a change,
briefly, not reassurance. He runs the package through a second model for independent review, so
anything written down should survive being read by someone with no session context.
