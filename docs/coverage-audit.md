# Coverage audit: can the new pipeline reproduce `listings_master_graded.csv`?

Audited 2026-09-06 against the 85-column, 28-row sheet produced by the previous Opus analysis.

**Short answer: 82 of 85 columns, yes. Three need an external source. And the new pipeline adds
roughly 40 columns the old sheet does not have, which are the ones that would have prevented the bad
Saturday.**

---

## Column-by-column source map

| Source | Columns | Notes |
|---|---|---|
| Crawler `fields` (`dl.property-details`) | **39** | Verified present on both boards |
| Crawler room table (`.room-row` + `.level-heading`) | **4** | lower_kitchen, lower_laundry, lower_full_bath, second_laundry |
| Crawler scores | **3** | walk, bike, transit |
| Remarks text mining | **12** | mech_ages, deposit_pct, offers_note, suite_language, etc. |
| Computed in script | **24** | ppsf, CMHC, LTT, cash_to_close, suite_ready_score, GRADE |
| **Needs an external source** | **3** | tax_assessed, price_to_mpac, tax_id |
| Unclassified | 0 | every column accounted for |

### The three that need outside data

- **`tax_assessed`** — the MPAC assessed value. Currently filled on 9 of 28, and those came from
  listings where the agent happened to include it. It is not a OneHome field.
- **`price_to_mpac`** — derived from `tax_assessed`, so blocked by the same gap.
- **`tax_id`** — the property roll number. Filled on 8 of 28, same reason.

Three ways to close this, in order of effort:

1. Ask the agent to pull assessed values and roll numbers for the shortlist only. Trivial for them,
   and you only need it on the handful you are seriously considering.
2. MPAC's AboutMyProperty gives assessed value per address, but it is one lookup at a time and
   account-gated.
3. Drop `price_to_mpac` from the model. Honestly, it is doing less work than you think. Assessments
   in Ontario are still frozen at 2016 valuations, so `price_to_mpac` is measuring how much the
   market has moved since 2016 more than it is measuring whether a given house is well priced. The
   within-cohort `over_under` benchmark in the analysis spec is a better instrument for the same
   question, and it needs no external data.

---

## Where the crawler should beat the PDF pipeline

The sheet has real gaps, and most of them are parse loss rather than missing data.

| Column | Current fill | Cause |
|---|---|---|
| deposit_pct | 3/28 (10%) | remarks mining, genuinely sparse |
| mech_ages | 6/28 (21%) | remarks mining, and agent silence is itself a signal |
| cross_street | 6/28 (21%) | crawler exposes this as `Directions` |
| fronting_on | 8/28 (28%) | crawler exposes this as `Direction Faces` |
| driveway | 8/28 (28%) | crawler exposes `Garage/Parking Features` |
| area_source | 8/28 (28%) | |
| tax_id | 8/28 (28%) | external |
| exclusions | 9/28 (32%) | crawler exposes `Exclusions` directly |
| tax_assessed | 9/28 (32%) | external |
| interior_feats | 12/28 (42%) | |
| zoning | 15/28 (53%) | crawler exposes `Zoning Details` |
| year_built | 17/28 (60%) | partly structural, see below |

**Verified gain:** 2105 Maplewood has `fronting_on` blank in your sheet. The crawler returns
`Direction Faces: North` for it. Same for `Exclusions`, which the crawler returns in full.

**One honest limit.** The crawler cannot invent data the listing agent never entered, and the two
boards differ. ITSO publishes an exact `Year Built` (Overton returns 1987). TRREB frequently
publishes only `Year Built Details` as an age band (Maplewood returns `51-99`). So some `year_built`
gaps are structural rather than extraction failures. The band is still worth capturing, since a
"51-99 years old" flag is a strong prior for pre-1980 construction, which drives the 25 percent
contingency rule and the asbestos check in the analysis spec. Your PDF parse was discarding it.

---

## What the new sheet gains

The audited sheet has 85 columns and **not one of them describes the condition of the house**. That
is the whole reason 343 Duncombe graded A. The v2 output keeps all 82 reproducible columns and adds:

**Condition (from the photo pass, about 30 columns)** — kitchen cabinets, counter, appliances,
vintage, whether the kitchen was reconfigured or only resurfaced; bath surround, vanity, vintage,
count updated; flooring by level; ceiling type; window frame type and opening count; electrical
panel type; basement ceiling, walls, moisture evidence, headroom; roof condition; soffit and fascia;
driveway condition; light quality; staging method; photo inventory by room type;
`evidence_completeness` and `not_shown` counts.

**Renovation cost (about 8 columns)** — reno_now, reno_5yr, reno_expected, reno_p80, gut_required,
gut_scope, gut_band, value_gap. All after the anti-underestimation rules, so `reno_p80` is the number
decisions get made on.

**Value (about 6 columns)** — neighbourhood ceiling, max_recoverable_spend, value_add, arv,
net_position, net_position_p80.

**Market signals the crawler picks up for free (about 5 columns)** — status badge, original list
price, price history, virtual tour present, terminate-and-relist detection.

Plus the per-room flooring and features from the room table, which your PDF parse was dropping
entirely and which feed the claim-versus-evidence contradiction test.

---

## Two structural improvements to the sheet itself

**Key on MLS, not address.** The current sheet has `address` and `file` using three different naming
conventions, and `1432 Dewbourne` in one file against `1432 DEWBOURNE Crescent` in another. Joins
will silently drop rows, and a dropped row looks exactly like a listing that never qualified. The
crawler exposes the MLS number directly.

**Split the sheet in three.** Eighty-five columns in one file mixes three things with completely
different lifecycles:

- `listings_observed.csv` — raw crawl and photo observations. Append-only, never regenerated.
- `listings_costed.csv` — cost and value model output. Regenerated free whenever assumptions change.
- `listings_graded.csv` — grades and rankings. Regenerated on every re-rank.

Right now, changing a kitchen cost estimate means rebuilding an 85-column file that also contains
raw source data. After the split it means rerunning a script over CSVs in about ten seconds, with
the expensive crawl and photo data untouched.

---

## Verdict

The pipeline reproduces the sheet, fills several of its gaps, and adds the condition and value
layers that the sheet is missing. The only genuine loss is MPAC assessment data, which is worth
about three columns and is better replaced by the within-cohort benchmark than restored.
