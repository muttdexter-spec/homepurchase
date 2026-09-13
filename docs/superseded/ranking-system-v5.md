# Ranking system v5: gates, cost to own, fit, and a dominance frontier

Written 13 September 2026. Supersedes `superseded/ranking-system-v4.md` and the
"rank ascending on `all_in_psf`" rule in `HANDOFF-START-HERE.md` section 2.
Derived from `REVIEW-2026-09-12.md` sections 3 and 4. Implemented in `pipeline/score.py`;
every parameter lives in `pipeline/costs.yaml` under `hold`, `gates`, `fit_weights` and `rank`.

The cost model did not change except for the six bug fixes in `QA-PASS-2026-09-13.md`.
What changed is what the ranking is computed from.

---

## 1. Why v4 was not built

v4 proposed five axes combined by a weighted geometric mean. Recomputed on the 37 rows, three
of the five (cost efficiency, exposure, carry) are size or price in different clothing:
cost and exposure correlate at 0.78 with each other and at about 0.7 to 0.8 with log usable
area. Two components of the correlation matrix carry 67% of the variance and three carry 92%,
so the five weights do not mean what they say. Exposure is worse than redundant: `recovered_pct`
takes only two values across the batch, 23 to 33% for the 12 houses where the ask-derived peer
norm sits below the ask and 48 to 67% for the other 25, with nothing in between.

The deeper problem is that five weights cannot be set. The 37 rows are what sellers ask,
filtered to a price band. They contain no information about what the buyers want, and a
weight fitted on them is a weight fitted on sellers. A geometric mean over correlated axes then
rewards the house with no distinguishing feature, which is why v4 put Barberry first.

v5 reduces the asserted preference parameters from five weights plus ten anchors to four:
a space knee, a condition demote, a fit tolerance, and the hold length.

## 2. The shape

A lexicographic gate ladder over a two-axis dominance frontier. Money on one axis, preference
on the other, and no exchange rate asserted between them.

```
G0  STOP       verdict() == STOP                      -> excluded, shown at the bottom
G1  program    beds_effective < 3, or baths_full < 1  -> excluded, reason shown
G2  budget     ask + day1_p80 > max_all_in            -> excluded  (null = off)
G3  cash       cash_to_close_20pct > max_cash_close   -> excluded  (null = off)
H   HOLD       oil tank, in-ground pool, tenanted     -> ranked, flagged, never "See first"
```

G1 removes Kent (2 bedrooms above grade) and Middlesmoor (a 41 sq ft "bedroom" in the room
table drops it to 2 effective; verify before trusting it, see backlog item 2). G2 and G3 are
the buyers' to set and are `null` today, because the saved search's price filter is doing G2's
job. A HOLD is priced or flagged, never a silent exclusion.

## 3. Money: cost to own over the hold

Under zero appreciation and "you get the price back at exit", which is the neutral assumption
when resale is not trusted:

```
own_H  = (1 - rec_day1) * day1_p80                  # the sunk part of day-one work
       + (r * H) * (ask + day1_p80) + comm * ask    # financing, opportunity cost, exit commission
       + H * annual_taxes
       + H * 12 * reserve_monthly
       + LTT_net(ask) + closing_extras
own_mo = own_H / (12 * H)
```

`rec_day1` is the expected-spend-weighted AIC mid recovery over the day-one lines with no
conformity cap, typically 0.45 to 0.55. `r` is 0.040 and `comm` is 0.055, both market inputs
rather than preferences, both in `costs.yaml: hold`. Appreciation is deliberately zero: it is
common to every house in Halton so it cannot rank them, and its idiosyncratic part is small
and badly measured.

Composition across the 34 ranked rows, per month, from `out/score_report.txt`:

| Part | Mean | Sd |
|---|---|---|
| capital | $5,097 | $510 |
| taxes | $461 | $63 |
| closing | $323 | $41 |
| day-one sunk | $274 | $85 |
| reserve | $151 | $16 |

That is the finding. Once you stop dividing by square feet, the money side is the ask, and the
cost model differentiates only at the tails. Its job is the verdict, the outliers and the
showing agenda, not the rank.

## 4. Fit: facts only, condition demote-only

Same component maxima as v3 (25 / 20 / 20 / 15 / 12 / 8 = 100) so the grade bands stay
comparable. Layout, baths, lot, location and parking are unchanged. Two things changed.

**Space saturates.** 16 points linear from 1,000 to the knee at 1,800 sq ft above grade, then
4 more points linear to 2,600. A couple planning a family gets most of the value of a 3-bed
house by about 1,800 sq ft above grade; the next 800 is nice and costs money to heat, tax and
clean. Below grade leaves the number entirely and becomes a discrete amenity from MLS text:
+3 finished, +1 partially finished, +2 for exterior access (separate entrance, walk-out,
walk-up, apartment). The 70% footprint estimate is fine for costing a refinish and stays there.
This matters because 18 of 37 basement areas are estimates, and the old linear term put the
model's least reliable input in the denominator of the rank.

**Condition subtracts.** Kitchen confirmed a full gut is -8, a confirmed cosmetic kitchen -6,
main bath confirmed original -4, a secondary bath -2, capped at -12, then scaled by era
(1.0 before 1990, 0.67 for 1990 to 2004, 0.33 for 2005 and later). "Confirmed" means the cost
model puts that line at p >= 0.95. Not shown is zero. Clean is zero. So a nice photograph still
cannot raise the grade, and a 2008 builder kitchen with a topmount sink is a 2-point issue
where a 1965 kitchen with the same sink is 7.

The split-level dock of 0.94 is unchanged. It is a preference and should be elicited.

## 5. Rank

The two axes are traded against each other at one rate, which is the only preference in the
ranking and the only number that sets the order:

```
lambda          = rank.dollars_per_fit_point_mo = 120      # dollars a month per fit point
value(i)        = own_mo(i) - lambda * fit(i)              # lower is better
sort by (value, own_mo)
band            = p10 to p90 of the rank over 1,000 re-rankings, one per day-one draw,
                  each re-ranking applying the same rule to that draw's day-one cost
```

Lambda was elicited on 13 September 2026 by showing the buyer the list under four settings
(money only, $80 a point, $120 a point, and grade bands first) and asking which one to keep.
$120 was chosen. It is a preference, not a measurement, and it belongs to the buyer: at $0 the
list is cheapest-first and the C+ bungalows lead it; at $120 the fit spread across the batch
(42 points, so $5,040 a month) is worth about 2.7 times the money spread ($1,885 a month), so
the grade leads the order and cost to own decides between houses that score about the same.

Overpay against the dominance frontier is still computed and still shown on every card, but it
no longer sets the order:

```
dominated_by(i) = argmin own_H over { j : fit_j >= fit_i - tol }    tol = 3 points
overpay(i)      = own_H(i) - own_H(dominated_by(i))                 0 means on the frontier
```

It answers a different question from the rank. The rank asks "which house do I want at these
prices". Overpay asks "am I paying more than I have to for this much house", which is an
argument about price rather than a reason to prefer a house. Five houses have overpay zero at a
5-year hold: Hazelwood, Clinton, Ravine, Bunton and Enfield. On the page they are stamped
best value, and the page says plainly that this does not put them at the top.

Overpay is a sentence: you are paying $X a month more than House Y for about the same amount
of house. Zero means nothing within three fit points of this house is cheaper to own.

Every ranked house carries a number, and the number now reflects both axes, so the top of the
list is the best house the buyer can have rather than the cheapest square footage in the batch.
The page calls the frontier set the best-value houses rather than the frontier. The rank band replaces v4's P(top 8), which
hard-coded 8 and reported a probability of a threshold rather than a range. Use the band
asymmetrically: visit if its top end reaches the shortlist even when the point rank does not,
and offer on the pessimistic end.

## 6. The order on the 37, H = 5

From `out/decision.csv`. "v3.4" is the $/sq ft rank on the same patched model, so the two
columns differ only by the ranking rule. "Fit in $/mo" is lambda times the score, and "rank
value" is own /mo minus that, which is what the list is sorted on. Band is p10 to p90.

| # | v3.4 | Gr | House | Ask | Day one | Own/mo | Fit | Fit in $/mo | Rank value | Over/mo | Band |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | A | 3205 Tania Crescent | $1,274,999 | $61,599 | $7,040 | 78.7 | $9,444 | -2,405 | +$200 | 1-3 |
| 2 | 2 | A- | 470 Delaney Court | $1,249,900 | $42,779 | $6,840 | 76.6 | $9,192 | -2,352 | +$190 | 1-3 |
| 3 | 12 | A- | 3217 Hazelwood Avenue | $1,235,000 | $46,209 | $6,650 | 74.9 | $8,988 | -2,336 | $0 | 1-3 |
| 4 | 7 | A- | 3212 Pinemeadow Drive | $1,299,900 | $40,844 | $6,930 | 74.6 | $8,952 | -2,025 | +$280 | 4-6 |
| 5 | 15 | B+ | 1273 Barberry Green | $1,199,000 | $28,486 | $6,280 | 68.4 | $8,208 | -1,925 | +$10 | 5-6 |
| 6 | 14 | B+ | 1493 Clinton Court | $1,174,900 | $30,552 | $6,270 | 68.3 | $8,196 | -1,925 | $0 | 4-6 |
| 7 | 21 | B+ | 659 Cherrywood Drive | $1,299,999 | $34,621 | $7,100 | 69.5 | $8,340 | -1,244 | +$820 | 7-11 |
| 8 | 3 | B- | 5174 Ravine Crescent | $1,098,000 | $35,923 | $5,960 | 59.6 | $7,152 | -1,196 | $0 | 7-10 |
| 9 | 8 | B | 2294 Seton Crescent | $1,194,900 | $26,212 | $6,290 | 61.0 | $7,320 | -1,032 | +$330 | 8-14 |
| 10 | 5 | B | 4831 Columbus Drive | $1,250,000 | $29,237 | $6,660 | 63.8 | $7,656 | -992 | +$390 | 8-15 |
| 11 | 6 | C+ | 1319 Bonnie Court | $999,900 | $28,973 | $5,320 | 51.9 | $6,228 | -903 | +$110 | 10-16 |
| 12 | 25 | B | 1228 Pallatine Drive | $1,228,000 | $33,860 | $6,540 | 61.9 | $7,428 | -891 | +$580 | 9-17 |
| 13 | 16 | C+ | 2120 Cavendish Drive | $969,900 | $29,271 | $5,230 | 50.9 | $6,108 | -879 | +$20 | 11-17 |
| 14 | 4 | B- | 5180 Bunton Crescent | $1,050,000 | $34,872 | $5,740 | 55.1 | $6,612 | -877 | $0 | 10-16 |
| 15 | 13 | C+ | 522 Enfield Road | $825,000 | $84,179 | $5,210 | 50.6 | $6,072 | -861 | $0 | 9-17 |
| 16 | 10 | B- | 2148 Stillmeadow Road | $1,098,000 | $27,816 | $5,890 | 55.8 | $6,696 | -803 | +$160 | 12-17 |
| 17 | 18 | C+ | 3469 Caplan Crescent | $988,800 | $40,340 | $5,450 | 51.4 | $6,168 | -721 | +$240 | 12-18 |
| 18 | 27 | C+ | 1453 Mountain Grove Avenue | $1,079,000 | $31,597 | $5,860 | 53.5 | $6,420 | -560 | +$650 | 16-20 |
| 19 | 17 | B | 506 PONDVIEW Place | $1,299,000 | $28,310 | $6,860 | 61.4 | $7,368 | -506 | +$910 | 17-20 |
| 20 | 28 | B- | 2105 Maplewood Drive | $1,199,000 | $31,679 | $6,540 | 57.3 | $6,876 | -331 | +$810 | 19-22 |
| 21 | 9 | C+ | 3490 Rexway Drive | $1,079,000 | $34,811 | $5,860 | 51.1 | $6,132 | -270 | +$650 | 19-23 |
| 22 | 20 | C+ | 5190 Wood Crescent | $1,099,900 | $26,338 | $5,820 | 49.6 | $5,952 | -133 | +$610 | 21-24 |
| 23 | 24 | B- | 395 LARK Avenue | $1,249,000 | $38,211 | $6,780 | 56.5 | $6,780 | 5 | +$1,050 | 22-26 |
| 24 | 22 | B- | 1379 Christina Court | $1,299,900 | $29,850 | $6,770 | 56.2 | $6,744 | 23 | +$1,030 | 22-26 |
| 25 | 35 | C+ | 1218 Oxlow Drive | $1,249,999 | $24,489 | $6,490 | 53.5 | $6,420 | 67 | +$1,280 | 23-26 |
| 26 | 23 | C | 1280 ALDRIDGE Crescent | $1,018,800 | $38,173 | $5,620 | 44.7 | $5,364 | 251 | +$400 | 24-27 |
| 27 | 26 | C+ | 1177 GRAND Boulevard | $1,299,900 | $37,430 | $6,850 | 53.9 | $6,468 | 381 | +$1,620 | 26-28 |
| 28 | 19 | C | 3202 Centennial Drive E | $1,059,900 | $33,411 | $5,730 | 43.5 | $5,220 | 508 | +$520 | 27-29 |
| 29 | 31 | C | 462 Samford Place | $1,099,000 | $36,114 | $5,970 | 42.9 | $5,148 | 823 | +$760 | 29-32 |
| 30 | 36 | C+ | 568 Weir Avenue | $1,299,999 | $45,489 | $7,020 | 51.6 | $6,192 | 824 | +$1,800 | 28-32 |
| 31 | 34 | C+ | 2221 Wyandotte Drive | $1,299,999 | $31,120 | $6,880 | 50.3 | $6,036 | 843 | +$1,670 | 29-32 |
| 32 | 30 | C+ | 28 Osborne Crescent | $1,299,000 | $33,785 | $6,900 | 49.7 | $5,964 | 931 | +$1,680 | 29-32 |
| 33 | 37 | C- | 493 CROSBY Avenue | $1,149,900 | $28,386 | $6,110 | 40.3 | $4,836 | 1,272 | +$900 | 33-33 |
| 34 | 33 | C- | 2501 Yarmouth Crescent | $1,298,000 | $37,527 | $6,920 | 36.7 | $4,404 | 2,518 | +$1,710 | 34-34 |
| - | 32 | C+ | 5322 Windermere Drive | $999,900 | $54,398 | $5,820 | 48.3 | | | | GATED: STOP |
| - | 11 | C | 2265 Middlesmoor Crescent | $1,049,900 | $28,855 | $5,570 | 44.8 | | | | GATED: 2 bed AG < 3 |
| - | 29 | C | 275 Kent Crescent | $1,179,000 | $31,297 | $6,310 | 42.8 | | | | GATED: 2 bed AG < 3 |

## 7. The frontier, and the one question to answer

| House | Grade | Own/mo | Fit | Step |
|---|---|---|---|---|
| 522 Enfield Road | C+ | $5,210 | 50.6 | |
| 5180 Bunton Crescent | B- | $5,740 | 55.1 | $116 per fit point per month |
| 5174 Ravine Crescent | B- | $5,960 | 59.6 | $49 |
| 1493 Clinton Court | B+ | $6,270 | 68.3 | $36 |
| 3217 Hazelwood Avenue | A- | $6,650 | 74.9 | $58 |

End to end the frontier costs $59 per fit point per month. The first step is the steepest, so a
linear exchange rate only ever selects Enfield (below about $59) or Hazelwood (above it) and
never the three houses between them. That is why the question is asked as a choice among five
houses rather than as a number: at these prices, which one? Picking Bunton, Ravine or Clinton
says the preference for fit is not linear, which is a legitimate answer and the one the model
cannot guess.

Six near-frontier pairs test whether fit is missing a term, municipality being the obvious
candidate (the asks say Oakville carries about 11.5% for the same house, and fit has no term
for it): Barberry against Clinton, Delaney against Hazelwood, Stillmeadow against Bunton,
Tania against Delaney, Seton against Ravine, Cavendish against Enfield. Consistently choosing
the dominated house means the fit score is short a component.

## 8. Moves worth arguing about

- **Enfield, v3.4 13 to 1.** Its old rank 3 was entirely an estimated basement, which the
  "Unfinished" bug had counted as finished. Here it is on merit: the low ask nearly pays for
  $84k of work over five years and fully pays for it over ten. Kitchen and both baths confirmed
  original hold it at C+ and the era-unscaled demote takes the full -12. Oil is a HOLD. Its band,
  1 to 11, is the widest in the set because its day-one distribution is, which is exactly the
  case for going to look rather than for shrinking the score.
- **Cavendish, 7, and $18 a month off the frontier.** The cheapest 3-bed 2-bath that is not
  Enfield, with a stated 1,007 sq ft finished walk-up basement and $4,782 of tax. At H = 3 it
  takes the frontier seat from Enfield, because three years of capital cost does not pay off
  $84k of work.
- **Clinton, v3.4 14 to 4.** 4 beds, 3 full baths, a 54 ft lot, 1973. The step from the B- pair to
  Clinton's B+ is 8.7 fit points for $310 a month, the cheapest fit on the frontier. The
  $/sq ft sort could not see it because 1,955 usable sq ft is average.
- **Tania, v3.4 1 to 11.** Not demoted for being large; it is still the most house in the set and
  the only A. It is off the frontier because Delaney is 2 fit points behind it and $200 a month
  cheaper, and Hazelwood is 2 behind Delaney and $190 cheaper again.
- **Barberry, 6, $10 a month off the frontier.** v4's number one. Here it is where a house with
  no weakness and no strength belongs, just behind the house it is nearly identical to.
- **Grand, v3.4 26 to 30, and Crosby, 37 to 25.** Both moved mostly through the basement-text fix.
  Grand's 800 sq ft of unfinished basement had been counted as usable; Crosby's 562.

## 9. Sensitivity of frontier membership

| Setting | Frontier |
|---|---|
| base (knee 1,800, tol 3, demote on, r 4.0%, H 5) | Enfield, Bunton, Ravine, Clinton, Hazelwood |
| H = 3 | Cavendish, Bunton, Ravine, Clinton, Hazelwood |
| H = 10 | Enfield, Bunton, Ravine, Clinton, Hazelwood |

The review also ran knee 1,600 and 2,200, tolerance 0 and 6, the demote off, and r at 6% on the
pre-patch model. Clinton and Hazelwood survived every setting, and one of Enfield or Cavendish
always held the cheap seat. Treat those three as the robust shortlist and the other two seats,
and the order within, as the buyers' to settle.

## 10. What is still wrong

- No sold price exists anywhere in this model. The resale block (`norm`, `headroom`, `arv_*`,
  `recovered_pct`, `breakeven`) is derived from asks and produces figures nobody believes at
  both ends of the batch, so it is hidden on the card and kept in `detail.json`. Only
  `sunk` is shown, because it is sourced and ask-free.
- Fit has no term for municipality and none for distance to a GO station, which is the location
  variable a Toronto commuter in Halton actually has. Backlog item 3.
- 12 of 37 listings have no room table, so the tiny-bedroom rule and the room-driven score
  cannot fire on them and they are structurally favoured on layout. Backlog item 1.
- The four preference parameters are asserted defaults, not elicited. Section 7 is the
  instrument for replacing them.
- Windows confirmed original are still annualised over a full life rather than over the hold
  (review 5.7), and there is no `furnace_seen` or `roof_seen` promotion wired to the reserve
  (review 5.10, backlog item 10). Both were left out of this pass deliberately.
