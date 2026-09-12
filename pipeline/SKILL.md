---
name: first-house
description: Evaluate a Halton/GTA MLS listing from a OneHome URL. Two-stage gate — data-only scoring first, photo forensics only on survivors. Use whenever the user pastes a OneHome/MLS property URL or asks to score, rank, or compare houses.
---

# First House

Drop a URL. Get one line in the decision table.

**Hard rule: photos demote, never promote.** No photo can raise a condition call above
`unverified`. There is no positive value for any `_verdict` field.

**Hard rule: never open the gallery in Stage 1.** Clicking it destroys the DOM and costs
~20k tokens. Most listings die at the gate and never need photos.

---

## Stage 1 — data (every listing, ~800 tokens)

1. `navigate` to the URL. Wait 6s.
2. Paste `crawl.js` into `javascript_tool`, then run `JSON.stringify(await window.__data())`.
   Never click accordion headers — it triggers an account gate. Only "Read More" is safe.
3. Append the record to `observations.json`.
4. `python3 score.py observations.json out/`

**The gate.** Stop here and report if any of these:

| Condition | Action |
|---|---|
| `true_cost` above the buyer's ceiling | STOP. Report one line. No photos. |
| grade C− or D | STOP unless the buyer asks. No photos. |
| `all_in_psf` more than 15% above the best listing **in the same size band** (usable sqft <1,500 / 1,500–2,200 / >2,200), and grade below A− | STOP. No photos. |

Grade A and A− listings are exempt from the $/sq ft gate: one unusually large house must not reset
the floor for everything else (fixed 2026-09-12; the unbanded rule killed two A− listings on
Tania's $418/sf). Everything else goes to Stage 2. Expect roughly 1 in 3 to survive.

**Buyer override (2026-09-12):** when the buyer asks for every listing to be photo-graded, skip the
gate entirely. Stage 2 costs about 6 tool calls and 4 screenshots per listing with the 8-frame
protocol in `stage2_brief.md`, so a full pass over 30 listings is an evening, not a week.

---

## Stage 2 — photos (survivors only, ~7k tokens)

0. Once per session: `resize_window` to **800×1300**. The pane then returns a full-viewport
   800×1300 screenshot at 1:1 (verified 2026-09-12; at 1000 wide it downscales to 0.8, at 400
   wide it captures only a quadrant).
1. `await window.__photos_load()` → returns `{total, natural_w}`.
2. `window.__sheet(98)` → one screenshot. 8 tiles per row. Inventory only —
   a condition call from a contact sheet is void.
3. `window.__fit([8 indices])` → one screenshot of EIGHT 394×316 frames (2×4). This is the
   locate pass and, at 0.38× of a 1024 source, already room-types and spots staging.
4. `window.__read([[i,x,y,z,label] × 8])` → one screenshot of eight magnified crops at z ≈ 2.2
   (2.5x effective). Two read calls settle all 15 tells on most listings.

```js
window.__tell([[8, 40, 72, 2.5, 'sink rim'], [8, 15, 40, 2.5, 'soffit'],
               [19, 55, 60, 2.5, 'tub type'], [19, 30, 80, 3, 'vanity top']])
```

**The tells, and where to aim.** These are the ones a cheap refresh cannot fake:

| Field | Aim at | Defect reading |
|---|---|---|
| `kitchen_sink_mount` | sink rim, 2.5x | visible raised rim = laminate. Highest-signal tell available. |
| `kitchen_counter_edge` | counter in profile | rolled / bullnose / post-form = laminate |
| `kitchen_soffit` | top of upper cabinets | bulkhead present = boxes never replaced |
| `kitchen_door_profile` | door corner, 3x | soft rounded raised panel = old doors painted |
| `bath_tub_type` | tub surround | corner/drop-in on a tiled platform = 1980s–90s original |
| `bath_tile_scale` | grout line, 3x | 4x4 or 12x12 with wide grout = old |
| `bath_vanity_top` | sink/counter junction | integrated moulded = old; undermount on stone = new |
| `window_frame` | frame corner, 3x | aluminum/wood original, or fogging between panes |
| `panel_type` | panel door | fuses vs breakers, and amperage |
| `basement_moisture` | bottom 18" of wall | efflorescence, staining, fresh paint low only |
| `ceiling_main` | ceiling, raking light | stipple survives every refresh and dates the house |

**Staging is adversarial.** Every surface a staged object sits on or covers is `not_shown`
and goes in `concealed_surfaces`. A throw over a tub, a rug over a floor, a cutting board
over a counter seam.

**`hdr_blowout: severe` forces every finish field to `not_shown`.** Clipped whites and no
wear anywhere in a 40-year-old house means you saw nothing.

4. Emit the record. **Only the ~24 fields `score.py` reads.** Anything else is a token you
   paid for and never used. Then re-run `score.py`.

---

## Output

One table. Rank on `all_in_psf` ascending. Grade is facts only and is cohort-independent —
a listing scored today is comparable to one scored in March.

```
#  GR  HOUSE              ASK        DAY-1 CASH   TRUE COST   $/SF   RES/mo   WISH LIST   VERDICT
```

- **DAY-1 CASH** — p80. Safety, insurability, and work that costs 2x once furniture is in.
  This is the number that competes with the down payment.
- **TRUE COST** = ask + day-1. Not ask + everything.
- **RES/mo** — roof, furnace, A/C, water heater, windows, annualised. A monthly line, not
  a purchase cost.
- **WISH LIST** — kitchen, baths, basement, deck. Buyer's choice, buyer's timing.
  **Never in the ranking.**

Verdicts: `STOP` (confirmed moisture, K&T, unresolved buried oil tank) · `SEE FIRST`
(grade B or better, no warnings) · `SEE`.

---

## What this cannot tell you

- **That a house is good.** Screening-out tool and showing-agenda generator only.
- **What anything is worth.** There are no sold comps in it. Nothing here is an offer price.
- **Whether you want to live there.** Street, light, noise, the walk to the car in February.
  All of it outranks the model.

## After each showing

Divide your own gut renovation estimate by the model's p80. Consistently above 1.0 means the
provisions are too soft. That ratio is the only real test of the model.
