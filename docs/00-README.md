# First House: document index

Start here. Updated 2026-09-06 for analysis spec v2.

---

## The one-line summary

A pipeline that crawls OneHome listings, reviews every photo, prices renovation pessimistically, and
returns a **verdict and a showing agenda** rather than a grade. It exists because v1 graded 2450
Overton a B and called it "genuinely renovated." The buyers walked it and it needed a full gut.

---

## Read in this order

| # | Doc | What it is | Who reads it |
|---|---|---|---|
| 1 | **`prompts.md`** | Copy-paste prompts for every phase | **You.** Start here. |
| 2 | **`photo-reno-grading-handoff.md`** | Analysis spec v2. The evidence hierarchy, photo protocol, observation schema, cost and provision model, verdict rules | Every analysis session |
| 3 | **`search-harvest.md`** | The crawler. Tested extractors for the saved searches and listing details | Every intake session |
| 4 | **`photo-manipulation.md`** | Virtual staging and AI tells, and why detection is the second line of defence | Every intake session |
| 5 | **`testrun-overton.md`** | The end-to-end reference run, and three spec bugs it found | Every intake session (carries the photo selector fix) |
| 6 | **`operating-manual.md`** | Workflow around the analysis: folders, cadence, automation, feedback loop | Setup, then occasionally |
| 7 | **`coverage-audit.md`** | Proof the pipeline reproduces 82 of the old sheet's 85 columns | Reference |

---

## Data files

| File | What it is | Status |
|---|---|---|
| `listings_live_queue.csv` | All 25 live listings with board, MLS, price, badge, prior grade | **Current.** The work queue. |
| `listings_master.csv` | Original 28-listing crawl from the PDF pipeline | Historical |
| `listings_graded.csv` | v1 grades. **Do not read into context** (~40k tokens) | Superseded |

---

## The four things that matter most

**1. Photos demote, never promote.** No listing's condition may rise above `UNVERIFIED` on
photographic evidence. Defects seen in photos are trustworthy because nobody stages a house to look
worse. Anything suggesting the house is good is marketing output. This is the whole design.

**2. Condition calls come from full-resolution single photos only.** Contact sheets are for inventory
and room-typing. Every feature that distinguishes a real renovation from paint and hardware — sink
mounting, counter edge, door profile, grout condition — is sub-pixel at contact-sheet size.

**3. Unverified condition costs money.** On a pre-1990 house you cannot confirm has been renovated,
the base rate says it has not been, so provisions run at 75% of full replacement. A full-resolution
look can reduce a provision, never zero it. This is the fix that catches Overton.

**4. Decisions are made on p80, never on a point estimate.**

---

## Open items

- **Phase 0 recalibration has not been run.** v2 must return ELIMINATE on Overton at roughly $400k
  p80. Nothing else should run until it does.
- **Holding period undecided.** Three to five years makes renovation recovery dominant; ten years
  makes it near noise. The two answers rank listings differently.
- **No sold comps.** Every neighbourhood ceiling is provisional. Highest-value input available:
  sold prices for 2150 Hunt, 3148 Bentworth, 1228 Pallatine and 2293 Oakhaven, all of which have
  disappeared from the searches and three of which were graded A or A-.
- **Two listings are Back on Market** — 2105 Maplewood and 4831 Columbus, both graded A-. A firm deal
  collapsed on each. Ask the listing agents why before spending analysis on them.
- **1379 Christina Court** has never been analysed at all.

---

## Two questions to put on every listing

Add these to `agent_questions.md` as standing items. On Overton the first one alone moved $58k.

1. How old are the roof, furnace and air conditioner?
2. Are any photos virtually staged or digitally enhanced, and when were they taken?
