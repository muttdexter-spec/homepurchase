# How to prompt this (v2)

Rewritten 2026-09-06 for analysis spec v2. The v1 prompts asked for grades. These ask for verdicts
and showing agendas, because that is what the evidence can actually support.

Run each in **Cowork**, in a **fresh session**, with the desktop app open on the laptop.

Four rules that belong in every prompt:

1. **Never read `listings_graded.csv` or `listings_master_graded.csv` into context.** ~40k tokens each.
2. **Opus drives, Sonnet subagents do the photo passes.** Does not happen by default.
3. **Paste both search URLs** into anything that touches the browser. Tokens live in the URLs.
4. **Condition calls come from full-resolution single photos only.** Say it explicitly every time.

---

## Phase 0: Recalibrate on Overton (do this first)

The one house where ground truth exists. Confirms v2 catches what v1 missed.

```
Read claude/photo-reno-grading-handoff.md, claude/photo-manipulation.md,
claude/testrun-overton.md and claude/search-harvest.md. Nothing else.

Re-run 2450 Overton under v2:
https://portal.onehome.com/en-CA/property/aotf~1177100090~ITSO?token=<...>&searchId=<...>

Ground truth: we walked this house. The interior needed a full gut. Kitchen,
flooring, bathrooms, all of it.

Do it properly:
1. Crawl with __intake().
2. Coverage sheets at tile width 128 until all 50 photos are seen.
3. Pass 2: full-width single photos at 760px on kitchen (2 angles), every
   bathroom, main floor, upper floor, basement, rear exterior, and every
   surface a staged object sits on. One photo per screenshot. No exceptions.
4. Run the manipulation checks from photo-manipulation.md.
5. Observation record, defect-oriented. No field may say "renovated."
6. Cost with the provision model in section 6, then the gut band if it triggers.
7. Verdict.

Tell me: does v2 return ELIMINATE with reno_planning_p80 near $400k? If it does
not, the provision model is still too soft and I want your proposed fix before
we run anything else.
```

**Success criterion is explicit and falsifiable.** If v2 does not eliminate a house the buyers
rejected in person, it is still broken.

---

## Phase 1: Batch intake

Fresh session. The long one.

```
Read claude/search-harvest.md in full, plus sections 4, 5 and 9 of
claude/photo-reno-grading-handoff.md and all of claude/photo-manipulation.md.

Search URLs:
  ITSO:  <paste>
  TRREB: <paste>

Task: intake all 25 listings in claude/listings_live_queue.csv, in the order in
Part 5 of search-harvest.md.

Per listing, one Sonnet subagent, SEQUENTIAL (one browser pane):
  - __intake() FIRST, then photos. Details before photos, always.
  - Coverage sheets at 128px until coverage.photos_seen == photos_total.
  - Then 10-14 FULL-WIDTH SINGLE PHOTOS at 760px for every condition call.
    A condition judgment made from a contact sheet is void. Redo it.
  - Run the manipulation checks. Record concealed_surfaces.
  - Return ONLY the section 5 observation record. No narration.

Remember the photo selector fix in claude/testrun-overton.md section 5. Do not
filter on naturalWidth; images are lazy-loaded and it returns undefined.

Write to claude/listings_observed.csv after EVERY listing, not at the end.

Report only: completed count, coverage failures, which came back OBSCURED,
which had no room dimensions.
```

Budget roughly 100k to 180k Sonnet tokens per listing. That is 2.5x v1 and it is the cost of not
repeating Overton.

---

## Phase 2: Cost, value, verdict

Fresh session. Opus. **No browser.** Cheap and repeatable.

```
Read claude/photo-reno-grading-handoff.md sections 6, 7 and 8, plus
claude/coverage-audit.md. Do not open a browser.

Input: claude/listings_observed.csv

Build config/cost_model.yaml (every tunable number in YAML, none in code) and a
Python script producing listings_costed.csv, listings_valued.csv and
listings_verdicts.csv.

Non-negotiable:
  - Confirmed defects cost full replacement at top of range.
  - Unverified condition on a pre-2000 house is priced as probably-not-done,
    using p_not_done by era. Full-resolution observation may REDUCE a provision,
    never zero it.
  - Era-conditioned not_shown risk. Do not charge a panel upgrade on a 1987 house.
  - 13% HST, 15% cascade, contingency 25/20/15 by era, forgotten items.
  - Gut band overrides line-item sums above 22% of list.
  - reno_planning_p80 = expected x 1.25. Rank on it.
  - Ceilings are provisional. Label them.
  - condition_status may never be "good."

Then in plain prose: which listings are ELIMINATE and what killed each, which
are SEE IT FIRST and what single question would resolve them, and which
one-full-bath homes have a cheap fix with real headroom.
```

---

## Phase 3: Showing prep

Same session as Phase 2.

```
From listings_observed.csv and listings_verdicts.csv produce:

  claude/showing_checklists.md — per SEE IT listing, what to physically verify,
  built from that listing's not_shown fields, concealed_surfaces and red flags.
  Specific to the house. "Lift the throw off the tub. Check whether the kitchen
  sink is undermount or topmount. Look for a soffit above the upper cabinets.
  Utility room: photograph the panel and the furnace label."

  claude/agent_questions.md — 3-5 per listing, plus these two on EVERY listing:
    - How old are the roof, furnace and air conditioner?
    - Are any photos virtually staged or digitally enhanced, and when were
      they taken?
```

Those two standing questions are the highest-value lines in the whole process. On Overton the
mechanical answer alone moved $58k.

---

## Phase 4: Ongoing, one new listing

```
Intake this listing: <URL with board token>

Follow claude/search-harvest.md, then the Pass 1 / Pass 2 protocol in section 4
of the analysis spec. Full coverage, then full-resolution single photos for
every condition call. Run the manipulation checks.

Append to listings_observed.csv, re-run the cost and value scripts, give me the
verdict and the one question that would most change it. One paragraph.
```

---

## Phase 5: Weekly sweep

```
Search URLs: ITSO <paste> / TRREB <paste>

Re-harvest both saved searches per Part 1 of claude/search-harvest.md and diff
against claude/listings_live_queue.csv.
  - NEW: intake fully.
  - GONE: mark removed and give me the address so I can get the sold price.
  - Price or badge changed: update and re-rank.
Do not re-intake anything already in listings_observed.csv.
```

---

## After every showing

Two minutes, and it is what makes the model improve.

```
Add to listings/<slug>/notes.md:

visited: <date>
model verdict: <> | my verdict: <>
model reno_planning_p80: $<> | my gut: $<>
what the photos hid entirely:
what the model got right:
walk-away reason:
would buy at:
```

Track one number across showings: **your gut estimate divided by the model's p80.** If it is
consistently above 1.0, the provisions are still too soft. That is the direct, measurable test of
whether v2 fixed the problem, and it is the only one that matters.

---

## What you need to supply

| For | You need |
|---|---|
| Phase 0 | Nothing. Ground truth is already recorded. |
| Phase 1 onward | Both search URLs in every browser-touching prompt |
| Anytime | Sold prices for 2150 Hunt, 3148 Bentworth, 1228 Pallatine, 2293 Oakhaven |
| Before valuing | Intended holding period: 3-5 years or 7-10 |

---

## What changed from v1, in one table

| | v1 | v2 |
|---|---|---|
| Condition source | contact sheets | full-resolution single photos only |
| Photos can | promote or demote | **demote only** |
| Best condition score | "renovated" | **UNVERIFIED** |
| Unverified condition | free | **priced as probably-not-done** |
| Staging | neutral | adversarial; concealed surfaces are not_shown |
| Output | a letter grade | verdict plus showing agenda |
| Cost per listing | ~40-80k tokens | ~100-180k tokens |
| Overton result | B, $187k p80 | **ELIMINATE, ~$418k p80** |
