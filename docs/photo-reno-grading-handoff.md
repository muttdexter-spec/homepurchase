# First House: analysis spec v2

Rewritten 2026-09-06 after the 2450 Overton failure. v1 graded a gut job a B and called it "genuinely
renovated." The buyers walked it and it needed everything. This version is built so that failure
cannot recur.

Companions: `claude/search-harvest.md` (crawler), `claude/photo-manipulation.md` (manipulation
tells), `claude/testrun-overton.md` (the evidence), `claude/operating-manual.md` (workflow).

---

## 1. Why v1 failed, in one paragraph

At contact-sheet resolution the Overton kitchen read as "painted shaker, stone counter, stainless,
mosaic backsplash" and scored as a 2010s renovation. At full resolution it is a **topmount sink in a
post-form laminate counter with a rolled edge, painted-over raised-panel doors, and the original
soffit still above the uppers**. The "renovated" main bathroom is an original 1987 corner garden tub
with a throw blanket draped over the basin. Furniture in the living room has no contact shadows and
its perspective does not agree with the room. Every interior is blown out to near-white, which
removes the wear, staining and colour variation that would have given it away.

Three failures compounded:

1. **Resolution.** Every discriminating feature is sub-pixel at 128-190px tiles.
2. **The marker table detected era, not quality.** White cabinets, grey counters, mosaic tile and
   stainless are the vocabulary a fifteen-thousand-dollar refresh uses precisely because it is the
   vocabulary of a hundred-thousand-dollar renovation.
3. **Photos were allowed to promote a listing.** They were treated as evidence that a house was good.

The cost model was fine. 7A faithfully inflated a wrong input. **No multiplier tuning fixes an
observation failure**, which is why this rewrite changes what gets observed and what observation is
allowed to conclude.

---

## 2. The governing principle: an evidence hierarchy

Everything in v2 follows from this.

**Tier A — Hard facts. Trusted.** From the crawler: square footage, lot, beds, baths, room
dimensions and levels, taxes, year built, zoning, basement type, days on market, price, brokerage.
MLS-entered, structured, and not worth faking.

**Tier B — Defect observations. Trusted.** Things visible in photos that are *bad*. A garden tub, a
soffit above the uppers, a topmount sink, a drop ceiling, efflorescence, a fuse panel, patchy stain.
**These are trustworthy precisely because nobody stages a house to look worse than it is.** A defect
that survives professional photography, staging and HDR is real.

**Tier C — Anything suggesting the house is good. Never trusted.** Photos, remarks, "fully
renovated", staging, finish that looks new. This is marketing output produced by someone paid to sell
the house, and it may be staged, processed, virtually furnished, or years out of date.

### The asymmetry rule

**Photos may demote a listing. Photos may never promote one.**

No listing's condition may rise above `UNVERIFIED` on photographic evidence alone. A house that looks
immaculate across fifty photos scores identically to a house with no interior photos at all: unknown,
pending eyes on it. This holds whether the concealment is AI, a wide lens, aggressive exposure, or a
throw blanket.

The consequence: **the photo pass is a screening-out tool and a showing-agenda generator. It is not a
shortlisting tool.** It cannot tell you a house is good. Overton is the proof.

---

## 3. What the analysis produces

Not a letter grade. v1's single grade implied condition knowledge that does not exist.

For every listing:

```
fact_score           0-100, Tier A only. Size, layout, lot, baths, location, carrying cost.
                     "Is this the right shape of house at the right price, ignoring condition."
condition_status     DEFECTS_FOUND | UNVERIFIED | OBSCURED       (never "good")
defect_findings      [specific defect, evidence photo index, cost]
reno_floor           confirmed defects only. A floor, not an estimate.
reno_planning_p80    the budget number. Floor plus unverified-condition provisions. See section 6.
verdict              ELIMINATE | SEE IT | SEE IT FIRST
showing_agenda       what to physically check, in order
agent_questions      3-5 to send before anyone drives anywhere
```

The headline is `verdict` plus `reno_planning_p80`. A listing is described as **"B on the facts,
condition unverified, budget $180k"** — never as "a B."

---

## 4. The photo protocol

**Contact sheets are for inventory only.** They establish photo count, room coverage, which index is
which room, and what is missing. They may **never** be used for a condition judgment. This is the
single most important change in v2.

Per listing:

**Pass 1, coverage.** Tile width **128**, roughly 21 photos per screenshot, until every photo is
seen. `coverage.photos_seen` must equal `coverage.photos_total`. Three sheets for a 50-photo listing.
Output: photo inventory, room index map, gaps, staging method, and the list of indices for Pass 2.

**Pass 2, condition.** **Single photos at full pane width (760px), one per screenshot.** Mandatory
targets, roughly 10 to 14 per listing:

- Kitchen, at least two angles
- Every bathroom shown
- Main floor flooring
- Upper floor flooring
- Basement walls and ceiling
- Rear exterior
- Any mechanical photo that exists
- **Every surface that a staged object sits on or covers**
- Any floor plan, if present

There is no adaptive budget on Pass 2. A condition call made from a contact sheet is void.

### What to look for at full resolution

These are **discriminating tells**, chosen because a cheap refresh cannot fake them. The v1 marker
table is deleted; it detected era.

**Kitchen**
- **Sink mounting.** Undermount means real stone. **Topmount with a visible rim means laminate.**
  Binary, and the highest-signal tell available.
- **Counter edge.** Rolled, bullnose or post-form means laminate. Square, eased or mitred means stone.
- **Soffit above the uppers.** Present means the cabinets were never replaced.
- **Door profile.** Crisp square shaker with sharp corners is new. Soft, rounded, puffy raised panel
  is thermofoil or old doors painted over.
- New hardware on old door profiles is a reface.
- Do cabinet boxes reach the ceiling, or stop at an original bulkhead?
- Appliance ages mismatched across the room means piecemeal replacement.

**Bathrooms**
- **A corner or drop-in garden tub on a tiled platform is a 1980s-90s original.** Near definitive.
- Tile: 4x4 or 12x12 with wide grout is old. Large format with thin grout is new.
- Grout colour and discolouration.
- Vanity: integrated cultured-marble top is old. Undermount on quartz is new.
- One-piece acrylic tub surround is a flip tell.

**Floors**
- Uneven stain tone, lap marks and patch-ins mean a bad refinish.
- Gaps and rough caulk at baseboards mean fast work.
- Does the floor change between rooms in a way that implies partial work?

**General**
- Wall waviness visible in the paint sheen.
- Trim quality, paint cut lines, crooked door tracks.
- Ceiling texture: stipple survives everything and dates the house.

### Manipulation checks

Run these every listing. Full detail in `claude/photo-manipulation.md`.

- **Cross-angle consistency.** Does furniture appear in one shot of a room and vanish in another?
  Do counters, backsplashes, cabinet counts and flooring match across angles?
- **Contact shadows.** Inserted furniture floats and does not compress carpet pile.
- **Reflections.** Mirrors and stainless are where insertion fails.
- **Perspective agreement** between furniture and the room's vanishing point.
- **HDR blowout.** Clipped whites, no wear anywhere in a house over twenty years old.

**No forensic analysis is possible.** CORS blocks byte access, so there is no EXIF, no error-level
analysis, no detection model. This is visual judgment only.

---

## 5. Observation schema

Defect-oriented. Fields record what is **wrong or unknown**, not what is nice.

```
coverage:              {photos_seen, photos_total}          # must be equal
photo_inventory:       {total, exterior, kitchen, bath, bed, living, basement, mech, yard, aerial, floorplan}
staging:               professionally_staged | virtually_staged | lived_in | vacant | mixed
virtual_staging_tells: [no_contact_shadow, perspective_mismatch, furniture_inconsistent_across_shots,
                        reflection_failure, clean_rug_edge, none_observed]
hdr_blowout:           none | moderate | severe             # severe forces finish fields to not_shown
cross_angle_check:     consistent | minor_variance | inconsistent | single_angle_only
manipulation_risk:     low | medium | high
concealed_surfaces:    [every surface a staged object covers]

kitchen_sink_mount:    undermount | topmount | not_shown
kitchen_counter_edge:  square_eased | mitred | rolled_bullnose | not_shown
kitchen_soffit:        present | removed | not_shown
kitchen_door_profile:  crisp_shaker | soft_raised_panel | slab | not_shown
kitchen_verdict:       defect_confirmed | unverified                # never "renovated"

bath_tub_type:         corner_garden_platform | alcove_tiled | one_piece_insert | freestanding | not_shown
bath_tile_scale:       small_4x4 | 12x12_wide_grout | large_format | not_shown
bath_vanity_top:       integrated_cultured_marble | undermount_stone | not_shown
bath_verdict:          defect_confirmed | unverified

floor_condition:       uneven_stain | patch_visible | gaps_at_base | no_defect_seen | not_shown
ceiling_main:          stipple_popcorn | flat_painted | drop_tile | not_shown
window_frame:          aluminum_original | wood_original | vinyl | not_shown
panel_type:            fuse | breaker_60 | breaker_100 | breaker_200 | not_shown
basement_ceiling:      drop_tile | drywall | exposed | none | not_shown
basement_walls:        bare_block | painted_block | panelling | drywall | not_shown
basement_moisture:     efflorescence | staining | fresh_paint_low_only | sump | none_visible | not_shown
roof_visual:           granule_loss | curling | patched | no_defect_seen | not_assessable
driveway:              cracked | sound | not_shown

evidence_completeness: {tier1_observed, tier1_total}
defect_findings:       [{defect, photo_index, confidence}]
red_flags:             [max 5]
```

Note the `_verdict` fields have no positive value. The best a kitchen can score is `unverified`.

---

## 6. Costing: the provision model

This is the fix that would have caught Overton.

**Confirmed defects are costed at full replacement, top of range.** A topmount sink in a laminate
counter with an intact soffit is a kitchen that has not been done. Cost a kitchen.

**Unverified condition costs money.** This is new and it is the heart of v2. For a pre-2000 house
where you cannot confirm the kitchen, baths, floors, roof or mechanicals have been done, the base
rate says they have not been. Roughly a quarter to a third of 1980s Halton homes in this price band
have had genuine work. So unverified is far closer to "not done" than to "done."

```
provision_i = full_replacement_cost_i × p_not_done(era)
p_not_done  = 0.75  for pre-1990 builds
              0.50  for 1990-2004
              0.25  for 2005+
```

A confirmed full-resolution observation may **reduce** a provision, but **never to zero**, and only
from a single-photo full-width look. Vinyl window frames confirmed at full resolution drop the window
provision from $28k to about $5k, allowing for a few originals. Nothing gets zeroed on photographic
evidence, ever.

**Era-conditioned risk.** A `not_shown` electrical panel in a 1987 house is near-zero risk because
breakers are certain; in a 1962 house it is real. Apply the not-shown penalty only where era makes
the risk real. Panel and knob-and-tube risk applies to pre-1970. Roof, furnace and AC risk applies to
anything over fifteen years old regardless.

Then the v1 inflation rules, which were correct and are retained in full:

- Top of every range, never the midpoint
- **13% HST** — contractor quotes exclude it
- **15% cascade** on any multi-room project
- **Contingency: 25% pre-1980, 20% 1980-1999, 15% post-2000** (the 1980s gap in v1 is fixed)
- Forgotten items: disposal, temporary kitchen, appliances, window coverings, repainting adjacent
  rooms, permits and drawings, moving and storage
- **`reno_planning_p80` = expected × 1.25. All decisions are made on p80.**

**Gut band override.** When `reno_expected >= 22% of list price`, stop summing line items and use the
bands, because line-item sums understate full guts: cosmetic gut $110k to $180k, structural gut $200k
to $320k on a 1,200 to 1,800 sqft home, plus $15k to $27k alternate housing for four to six months on
top of carrying the mortgage, plus permits, plus contingency.

### Worked check against Overton

Confirmed defects at full resolution: kitchen not done ($70k), main bath not done ($28k), powder and
basement baths dated ($30k), original main floor and patchy upper stain ($25k), stipple ceilings
($8k), basement drop ceiling and panel walls ($25k), deck ($6k), driveway ($8k). Provisions: roof
$14k, HVAC $14k, windows reduced to $5k on confirmed vinyl. Base $233k, which exceeds 22% of list, so
the gut band applies: cosmetic gut top $180k → **p80 $418,365, all-in $1.57M against a Brant Hills
ceiling near $1.30M.**

v1 scored this at $186,958 p80 and a B. **v2 lands at $418k and ELIMINATE.** That is the correct
answer and it matches what the buyers found in person.

---

## 7. Value

Unchanged from v1 and still correct.

- `ceiling` — 90th percentile sold price for the type in that neighbourhood. **Provisional until
  `sold.csv` accumulates.** Dollars spent past it return zero.
- `conformity` — bringing a home up to neighbourhood norm returns 1.2 to 1.4x base recovery; pushing
  past norm returns 0.4 to 0.6x.
- Recovery rates: paint 90-110%, flooring 70-90%, kitchen 70-80%, bath 60-70%, basement 50-70%, roof
  55-65%, windows 50-60%, electrical and waterproofing 40-50%. **Invisible work is the expensive
  kind.**
- Highest-return interventions: a second full bath in a one-bath home (90-130%), a legal second suite
  where zoning permits (100-150%).
- `net_position_p80 = arv − (list_price + reno_planning_p80)`. Negative means paying to renovate
  someone else's house.

Five listings in the pool have one full bathroom — 343 Duncombe, 3453 Hannibal, 1486 Barker,
495 Tipperton, 1432 Dewbourne — and each carries a heavy penalty that is unusually cheap to remove.
Distinguish *bad house, expensive, no headroom* from *penalised house, cheap fix, headroom exists*.

---

## 8. Verdict rules

```
ELIMINATE      net_position_p80 < 0 by more than 10% of list
               OR gut_required with no headroom to the ceiling
               OR basement moisture confirmed
               OR manipulation_risk high AND price at the top of the band

SEE IT FIRST   fact_score strong AND reno_planning_p80 affordable AND
               a specific verifiable question would resolve most of the uncertainty

SEE IT         everything else that is not eliminated
```

`condition_status = OBSCURED` when `hdr_blowout: severe`, `manipulation_risk: high`, or
`cross_angle_check: inconsistent`. Obscured listings are **not eliminated and not promoted** — they
go straight to a showing with a full agenda, because the photos cannot settle it either way.

`evidence_completeness < 0.5` forces `UNVERIFIED` and a showing.

---

## 9. Efficiency, honestly

v2 costs roughly **2.5x v1 per listing**: about 3 coverage screenshots plus 10 to 14 full-resolution
single photos, so 13 to 17 total, roughly **100k to 180k Sonnet tokens per listing**, paid once per
listing ever.

That is the price of the mandate not to underestimate, and the Overton run is what it buys. The
savings come only from the parts that do not touch condition:

1. One listing per Sonnet subagent, sequential, returning only the observation record. Screenshots
   never enter the driver's context. Worth more than everything else combined.
2. Never re-intake a listing. Observations are permanent; costing and grading are free to re-run.
3. Aerials and lifestyle shots count toward coverage but never earn a full-resolution look.
4. Never read `listings_graded.csv` into context. Never paste photo URLs anywhere.
5. Elimination is cheap. A listing that fails on Tier A facts alone never reaches Pass 2.

---

## 10. Deliverables

1. `claude/listings_observed.csv` — raw crawl plus defect observations. Append-only.
2. `claude/listings_costed.csv` — reno_floor, provisions, reno_expected, reno_planning_p80,
   gut_required, gut_band.
3. `claude/listings_valued.csv` — ceiling (flagged provisional), value_add, arv, net_position_p80.
4. `claude/listings_verdicts.csv` — fact_score, condition_status, verdict, the findings driving it.
5. `claude/showing_checklists.md` — per listing, what to physically verify, built from that listing's
   `not_shown` fields, `concealed_surfaces` and red flags.
6. `claude/agent_questions.md` — per listing, plus two standing questions on **every** listing:
   *how old are the roof, furnace and air conditioner?* and *are any photos virtually staged or
   digitally enhanced, and when were they taken?*

---

## 11. Standing mandates

- Every agent-filtered listing gets full photo coverage. Efficiency never comes from skipping photos.
- **Photos demote, never promote.** No condition rises above UNVERIFIED on photographic evidence.
- Condition calls come from full-resolution single photos only. Contact sheets are inventory.
- Staging is adversarial. Every concealed surface is `not_shown`, never fine.
- Unverified condition on a pre-2000 house is priced as probably-not-done.
- Bias pessimistic. Decisions on p80.
- Sold comps arrive at offer stage. Ceilings are provisional and labelled.
- Split levels take a 5% livability dock.
- The output is a verdict and a showing agenda, not a letter grade.
