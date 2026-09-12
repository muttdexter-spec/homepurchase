# Test run: 2450 Overton Drive, start to finish

Run live 2026-09-06. This is the reference output. Compare your own run against it.

**It exposed three bugs in the spec. The photo one would have broken every listing.** Fixes are in
section 5 and supersede the snippets in the analysis spec and the crawler doc.

---

## 1. The prompt

Fresh Cowork session, desktop app open on the laptop.

```
Read claude/search-harvest.md and sections 5, 6, 7, 7A, 8, 8A, 9, 9A and 11 of
claude/photo-reno-grading-handoff.md. Also read claude/testrun-overton.md,
which carries corrected snippets that supersede the spec.
Do NOT read listings_graded.csv or listings_master_graded.csv into context.

Single-property test run on:
https://portal.onehome.com/en-CA/property/aotf~1177100090~ITSO?token=<...>&searchId=<...>

Do it in this exact order, and show me the output of each step before moving on:

1. Crawl. Run __intake(). Report field count, room count with levels, and the
   key values (price, sqft above/below, lot, taxes, year, style, basement,
   roof, foundation, heating, neighbourhood, inclusions).
2. Photo harvest. Confirm you minted all Size:3 links and report the count.
3. Full coverage. Contact sheets at tile width 128 until every photo is seen.
   coverage.photos_seen must equal coverage.photos_total. Show me each sheet.
4. Detail pass. Tile width 265, on kitchen, bathrooms, basement and rear
   exterior. Show me each sheet.
5. Observation record. Section 6 schema, including evidence_completeness,
   single_photo_rooms and red_flags.
6. Cost and value. Write a Python script, do not do it by hand. Apply section
   7A in full. Report reno_now, reno_5yr, reno_elective separately, plus
   reno_expected and reno_p80.
7. Value. Provisional neighbourhood ceiling, value_add, arv, net_position_p80.
   Label the ceiling as provisional and say why it is not trustworthy on a
   single listing.

Then tell me in plain prose what I would actually be buying.
```

---

## 2. What the crawl returned

65 fields, 14 rooms across three levels, in one page load, no clicking except Read More.

| | |
|---|---|
| Price / ppsf | $1,149,000 / $589 above grade |
| Above / below grade | 1,950 sqft / 839 sqft |
| Lot | 49.86 x 104.12, zoning R3.2 |
| Year built / style | 1987, Traditional |
| Basement | Full, Finished, Sump Pump |
| Roof / foundation / construction | Asphalt Shingle / Poured / Aluminum Siding, Brick |
| Heating / cooling / fireplaces | Forced Air Gas / Central Air / 1 |
| Taxes | $5,684 (2026) |
| Neighbourhood / DOM / photos | 341 - Brant Hills / 53 / 50 |

Rooms, level-aware: Main has kitchen 110 sqft, family 234, living 158, dining 112, breakfast 110,
laundry 69, 2-piece bath. Second has three bedrooms at 158 / 123 / 122 sqft and a 4-piece. Basement
has two bedrooms at 216 / 120 and a 4-piece.

Derived correctly: primary 158, minimum secondary 122, zero bedrooms under 100 sqft, and the two
basement bedrooms correctly excluded from both.

---

## 3. What the photos showed

Six screenshots total: three coverage sheets at 128px covering all 50 photos, three detail sheets at
265px.

**Renovated, genuinely, on the main and upper floors.** Kitchen is painted shaker with a stone
counter, mosaic tile backsplash, stainless including a built-in wall oven, hardwood, soffit removed.
A real 2010s renovation, not a reface. Main bathroom is fully tiled with a glass shower, tiled tub
deck and a skylight. Powder and basement baths both updated. **Windows are white vinyl throughout**,
which is a $20k to $28k item avoided and the single most valuable thing the photo pass found.

**The basement is a generation older than the rest of the house.** Drop tile ceiling, painted
textured panel walls rather than drywall, a wet bar with busy 2000s granite and dark cabinets, and
carpet in at least one room. It is finished and functional, but it is a 1990s-2000s finish sitting
under a 2010s house.

**Zero mechanical photos.** Fifty photos, not one of the furnace, panel, or water heater, and no
mechanical ages anywhere in the listing. On a 39-year-old house that is the single most consequential
gap, and per rule 6 of section 7A it is costed pessimistically rather than assumed fine.

**Roof not assessable.** Visible only in aerials. No stated age on a 1987 build.

Other notes: stipple ceilings throughout main and upper, though 1987 puts them past the Ontario
asbestos window; a large elevated wood deck with weathered red stain; thin grass on a sloped lot;
dated teal garage door; cracked asphalt driveway.

**Claim versus evidence: mild overstatement.** The remarks call it a "carpet-free home." There is
carpet in the basement.

---

## 4. The numbers

Base costs at the top of every range, then section 7A applied: cascade 1.15, contingency 1.20 for a
1987 build, HST 1.13, then $10k of forgotten items, then p80 at 1.25.

| Bucket | Base | After 7A |
|---|---|---|
| Must do now (roof + HVAC, both provisioned because unphotographed) | $28,000 | **$43,663** |
| Should do in 5 years | $42,500 | **$66,274** |
| Elective (stipple removal, landscaping, driveway) | $19,000 | **$29,629** |
| Forgotten items (disposal, permits, adjacent repaint) | | **$10,000** |

- **`reno_committed_p80` = $149,922** (everything except elective)
- **`reno_expected` = $149,566, `reno_p80` = $186,958** (everything)
- `gut_required` = false
- `evidence_completeness` = **0.60**, so 3 of 5 tier 1 fields observed. Windows, basement moisture
  and ceilings yes. Roof and electrical panel no.

Value, against a **provisional** Brant Hills ceiling of $1.30M taken from the top of current asks in
that pocket:

| | |
|---|---|
| All in, committed | $1,268,938 |
| All in, everything | $1,298,566 |
| Max recoverable spend | $151,000 |
| ARV | $1,188,475 |
| **net_position_p80** | **−$147,483** |
| net_position_committed_p80 | −$110,447 |

---

## 5. Three spec bugs this run found

**Bug 1, critical. The photo selector fails on every listing.** Section 11 of the analysis spec and
Part 2 of the crawler doc both filter on `naturalWidth > 100`. Gallery images are lazy-loaded, so
all 52 report `naturalWidth: 0` and the selector returns undefined. **Use this instead:**

```js
const first = [...document.querySelectorAll('img')].find(i => /matrixmedia/.test(i.src || ''));
first.scrollIntoView({ block: 'center' });
await new Promise(r => setTimeout(r, 1500));
first.click();
await new Promise(r => setTimeout(r, 5000));
```

No `naturalWidth` filter, scroll into view first, longer wait. Verified: harvests all 50.

**Bug 2. The contingency table has a hole.** Section 7A specifies 25 percent pre-1980 and 15 percent
post-2000, and says nothing about 1980 to 1999. Overton is 1987. Use **20 percent for 1980-1999**.

**Bug 3. The `not_shown` penalty needs conditioning on build era.** Rule 6 charges the cohort 75th
percentile for any unobserved tier 1 field. That is right for a roof, whose age is genuinely unknown
on a 39-year-old house. It is wrong for an electrical panel: a 1987 build has breakers with near
certainty, so charging a panel upgrade would be manufacturing a cost. **Amend rule 6:** apply the
75th percentile penalty only where the era makes the risk real. Panel and knob-and-tube risk applies
to pre-1970 builds; roof, furnace and AC risk applies to anything over 15 years old regardless.

**Two settings worth freezing.** Tile width **128** puts 21 photos in one screenshot at enough
resolution to judge a countertop, so three sheets cover 50 photos. Tile width **265** gives four
photos per screenshot at detail quality. Do not use `resize_window`.

**One minor gap.** `Direction Faces` is present on TRREB listings and absent on this ITSO one, so
`fronting_on` will stay sparse on ITSO regardless of extraction quality.

---

## 6. What you would actually be buying

A genuinely renovated 1987 two-storey with new windows, a real 2010s kitchen, three updated
bathrooms and hardwood, sitting on a dated basement with a drop ceiling, an aging deck, and a
completely undocumented mechanical situation.

The old model graded this A. It is not wrong that this is one of the better houses in the set. But
the A came from $589 per foot above grade, and the honest picture is different: **at a committed p80
of $150k you are all in at $1.27M in a pocket where nothing currently asks above $1.30M.** Most of
that $150k is roof and HVAC that may already have been done, and the listing simply does not say.

Which makes the highest-value next action not a photo, a model tweak, or a showing. It is one email:
**how old are the roof, furnace and air conditioner?** That single answer moves $43,663 of provisioned
cost, and with it the entire verdict on this house.

**Read the value numbers with care.** `net_position_p80` is meaningless on a single listing. The
ceiling here is a guess from current asks in Brant Hills, not a sold comp, and the whole point of the
within-cohort benchmark is that it ranks listings against each other. Run the other 24 before
treating −$147k as anything more than a flag.
