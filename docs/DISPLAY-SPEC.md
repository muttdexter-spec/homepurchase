# Display spec: putting the v5 numbers on the existing page

Written 2026-09-12 against `full.html` (md5 b2b1f0a7, 37 cards). The page is not to be
redesigned. Every addition below reuses a component the page already has, keeps its colour
vocabulary, and can be deleted without breaking anything else. `reference/page/` holds the
page's CSS verbatim, two complete cards, the header and table, both scripts, and a class
inventory, so the builder can be brought to parity even if the newer `build_walkthrough.py`
that produced this page is not found (see `README-COWORK.md`, prerequisite 1).

## 0. The three bar components the page already has

| Component | Where | Shape | Use it for |
|---|---|---|---|
| `.sp` | score panel, room score | label · 30 px bar · `n / max` | any score part out of a maximum |
| `.rh-bar` | needs-work score | full-width 7 px bar, coloured fill, number + word above | any single 0 to 100 or money-as-length bar |
| `.scorecol` | whole table | letter · number · 30 px bar | any per-row mini bar in the table |

Colour vocabulary (from the legend): `--clear` no problem, `--warn` unseen or under half,
`--bad` under 30%, `--flag` confirmed / costs money, `--accent` grade and score. Nothing new
is introduced. Overpay is money you would pay, so it is `--flag`.

## 1. Reading rules for the numbers

1. **One headline per card, and it is the thing the page is sorted on.** Today that is
   `$/usable sq ft`; it becomes **overpay per month**. A reader should never see a bigger
   headline number on rank 3 than on rank 5 and wonder why.
2. **Every number carries its comparison.** Overpay is always "+$153 /mo vs Hazelwood".
   Fit is always "79 of 100". A cost is always "at 5 yr hold". No naked numbers.
3. **Round for reading.** Own /mo and overpay /mo to the nearest $10. Five-year totals to the
   nearest $1k. Fit to an integer on the card, one decimal in the table. `$5,201` is false
   precision; `$5,200` is a number someone can hold in their head in a hallway.
4. **Bars fill one way per panel.** In the score panel more fill is better. In the money
   panel the bar is a length of cost and the `--flag` segment is the overpay; less is better.
   The two panels never share a row.
5. **Subtraction is shown, not hidden.** The condition demote appears as its own row with a
   minus sign and as "83 − 4" under the big number. Never fold it silently into the total.
6. **Ties are ties.** Within $50 /mo of the frontier reads "≈ frontier", not "+$12".
7. **Rank is for the dominated.** Frontier houses show `F` in the rank slot; their order
   among themselves is the buyer's, so the page does not assign them 1 to 5.
8. **Keep `$/sq ft`, demote it.** It stays in the cost breakdown as "for reference, not the
   rank", so nothing the couple got used to disappears.

## 2. Card, top to bottom

### 2.1 Rail (`.rail`)

Today: rank · grade · `$410 per usable sq ft` · `1–1 rank if unknowns flip`.

```
<div class="rank">F</div>                          F for frontier, else the rank number
<div class="grade g-b">B+</div>                    unchanged
<div class="psf"><b>$0</b><span>/mo over frontier</span></div>              headline
<div class="psf"><b>$6,270</b><span>/mo to own · 5 yr</span></div>          own cost
<div class="psf"><b>3–10</b><span>rank band</span></div>                    unchanged label shortened
```

Headline text: `$0` on the frontier, `≈ $0` within $50, otherwise `+$153`. Colour the `<b>`
with `--clear` on the frontier, `--flag` otherwise, matching the legend.

### 2.2 Head (`.lot-head`)

Add one line after `.where`, same style as `.where`:

```
<p class="where why">+$153 /mo vs 3217 Hazelwood (A−, $1,235,000) for about the same house</p>
```
or, on the frontier: `Frontier · nothing within 3 fit points is cheaper`.

Stamps (`.tags`), additive:
- `Frontier` (`.stamp.seen`) when overpay = 0.
- `Worth a look` (`.stamp.seen`) when rank_p10 ≤ 10 and rank > 10. This is the
  visit-on-the-band rule made visible.
- `HOLD · pool` / `HOLD · oil tank` / `HOLD · tenanted` (`.stamp.unseen`) replacing the
  current POOL, OIL TANK and TENANTED stamps (whose text today includes a dash and a note), same class.
- `Robust` (`.stamp.seen`) for houses on the frontier under every setting in the
  sensitivity grid (today: Clinton, Hazelwood, and Enfield or Cavendish). Optional.

### 2.3 Score panel (`aside.scorepanel`)

Today: letter, `83 / 100`, six `.sp` rows. Becomes letter, `79 / 100`, with the `em` reading
`Grade · facts only, no price · 83 − 4 condition`, and seven rows:

```
<div class="sp"><em>Space</em><span><i style="width:92%"></i></span><b>23<s> / 25</s></b></div>
<div class="sp"><em>Layout</em>…</div>
<div class="sp"><em>Baths</em>…</div>
<div class="sp"><em>Lot</em>…</div>
<div class="sp"><em>Location</em>…</div>
<div class="sp"><em>Parking</em>…</div>
<div class="sp bad"><em>Condition</em><span><i style="width:33%"></i></span><b>−4<s> / −12</s></b></div>
```

"Size" is renamed "Space" because it now includes the basement amenity and saturates. The
Condition row uses `.sp.bad` (existing, `--bad` fill) when non-zero and `.sp` with an empty
bar and `0<s> / −12</s>` when zero, so the row is always present and the reader learns that
condition can only subtract. `.sp-foot` gains one sentence: "Condition can only subtract, and
only on a defect confirmed at full resolution."

### 2.4 Money (`dl.money`)

Today: Ask · **Day-one cash** (hero) · True cost · Taxes + reserve /mo · Wish list.

```
<div><dt>Ask</dt><dd>$1,174,900</dd></div>
<div><dt>Day-one cash</dt><dd>$30,552</dd></div>
<div><dt>True cost</dt><dd>$1,205,452</dd></div>
<div class="hero"><dt>Own · 5 yr</dt><dd>$6,270<span class="per">/mo</span></dd></div>
<div><dt>Taxes + reserve</dt><dd>$629<span class="per">/mo</span></dd></div>
<div><dt>Wish list</dt><dd>$77,237</dd></div>
```

Hero moves from day-one cash to own /mo, because the page is now sorted on a derivative of
own /mo. Day-one cash keeps its slot.

### 2.5 The cost bullet bar (new element, existing component)

Directly under `dl.money`, one `.rh-bar` with a tick. This is the picture of "overpay":

```
<div class="reno-head" style="margin-top:6px">
  <div class="rh-score">
    <span class="rh-lab">Cost to own, per month, 5-year hold</span>
    <span class="rh-num"><b>$6,420</b><i>/mo</i><u style="color:var(--flag)">+$150 vs Hazelwood</u></span>
    <span class="rh-bar" style="position:relative">
      <i style="width:78%; background:var(--accent)"></i>
      <i style="position:absolute; left:76%; top:0; width:2%; background:var(--flag)"></i>
      <i style="position:absolute; left:76%; top:-3px; width:2px; height:13px; background:var(--ink)"></i>
    </span>
    <em>Bar is this house. Tick is the cheapest house that is about as much house. The gap is the overpay.</em>
  </div>
</div>
```

Scale: bar width = own /mo divided by the set maximum (Weir, $6,980). Tick at the dominating
house's own /mo on the same scale. Frontier: fill `--clear`, no tick, `<u>` reads
`Frontier`. Everything here is inline style on existing classes; no new CSS is required,
though a `.rh-bar .tick` rule would be cleaner if the builder is being edited anyway.

### 2.6 Renovations (`section.reno`)

Unchanged, except the needs-work `em` becomes: "The list above as a share of the asking
price. Shown for context; it is not in the rank." That sentence prevents the reader from
assuming the bar they see is the thing the page is sorted on (it was v4's burden axis, and it
is not in v5).

### 2.7 Everything below

Settled by the photos, Check when you're there, Showing record, Rooms and room-driven
score, Cost breakdown: unchanged. In the cost breakdown, add one line:
`$620 per usable sq ft · for reference, not the rank`.

## 3. The whole table (`table.big`)

Columns today: `# · House · Score · Ask · Day one · $/sq ft · Carry/mo · Wish list · Tells ·
Evid. · Band · Cash close · Verdict · Flags`.

Replace `$/sq ft` with two columns and keep the rest:

```
<th class="n">Own/mo</th>
<th class="n">Over/mo</th>
…
<td class='n'>$6,270</td>
<td><span class="scorecol"><b class="v">$150</b><span class="bar"><i style="width:8%; background:var(--flag)"></i></span></span></td>
```

Over/mo bar width = overpay divided by the set maximum overpay (Weir, $1,780 /mo). Frontier
rows: `F` in the `#` cell, `$0` in `--clear`, empty bar. Default sort is the v5 order.
Sortable-column JS, if present, treats the two new columns as numeric.

Add a one-row group header above the frontier block:
`<tr class="grp"><td colspan="15">Frontier · five houses, none cheaper for the same fit · pick your price point</td></tr>`
and one above the rest: `Dominated · ranked by overpay`. Use the existing `.section-head`
type styles inline if no `.grp` rule exists.

## 4. Page head

- `mast-meta`: `Ranked by overpay vs the frontier · 5-yr hold` replaces `Ranked by cost per
  usable sq ft`; `Model v3.4 · rank v5` replaces `Model v3.2`.
- `legend`: no new swatches. Overpay is `--flag`, which the legend already reads as "Confirmed,
  costs money". If a distinct wording is wanted: `<span><i style="background:var(--flag)"></i>Costs money, or overpay vs the frontier</span>`.
- `glossary`: add three terms in the existing `dl.glossary` shape.

```
Own /mo     What it costs to live here for the hold, per month, if you get the price back when
            you sell: financing and opportunity cost on the price, the part of day-one work you
            do not recover, taxes, the component reserve, land-transfer tax and commission out.
            No appreciation assumed.
Frontier    A house is on the frontier when nothing within three fit points of it costs less
            to own. The frontier is the shortlist. Its order is yours.
Overpay     Own /mo minus own /mo of the cheapest house that is about as much house. Zero on
            the frontier. It is the number the page is sorted on.
```
  and edit `Grade`: "…No price in it. Condition can only subtract, and only on a confirmed
  defect, so a nice photo never raises it."
- `howto`: one added sentence after the photos rule: "The rank is no longer dollars per
  square foot. It is how much more per month a house costs than the cheapest house that is
  about as much house."

## 5. Hold toggle

The page has a live calculator (`page-script-1.js`, `.ctrl` inputs) and a control strip
(`.sr-ctl`). Add three buttons in `.sr-ctl`, same `.sr-mode` class, `data-kind="hold"`,
values 3 / 5 / 10, default 5. Each card carries `data-own3`, `data-own5`, `data-own10`,
`data-over3`, `data-over5`, `data-over10`, `data-vs3`, `data-vs5`, `data-vs10` (all
precomputed by the builder from `rank_v5.run()` at each H). The toggle rewrites the rail,
the money hero, the bullet bar and the table cells. **It does not re-sort the cards.** The
order is the 5-year rank and the page says so in `mast-meta`; the table shows the 3 and 10
year ranks in the `Band` column's tooltip. Re-sorting on the phone is more motion than it is
worth for an order that moves one house.

## 6. The frontier chart (optional, the only genuinely new element)

One inline SVG in the "whole table" `section-head`, 100% wide, 220 px tall, viewBox
0 0 720 220. x = own /mo ($5,000 to $7,200), y = fit (30 to 85). 37 circles r=5: frontier
houses filled `--clear` with their street name as a 10 px `--mono` label to the right;
dominated houses filled `--rule-soft` stroked `--muted`; gated houses hollow. A polyline
through the frontier houses in `--clear`, stroke 1.5, joining them as a staircase. Axis
titles in `.rh-lab` style: "Cost to own /mo →" and "↑ Fit". Each circle carries `<title>` with
name, own /mo, fit, overpay.

This is the one picture that makes overpay self-explanatory: the eye sees five dots on a
line and everything else above-right of it. It survives 360 px wide because only five labels
are drawn. It uses no colours the legend does not already define. If the constraint "no new
elements" is applied strictly, skip it; nothing depends on it.

## 7. Mobile (`mobile.html`)

Same changes. The rail already collapses to a row under 640 px (`.rail{flex-direction:row}`).
Order in the row: rank, grade, overpay, own /mo, band. The bullet bar is full width by
construction. The `why` line wraps under the address. The table is already horizontally
scrollable; the two new columns sit where `$/sq ft` was so the scroll width barely changes.
The SVG, if built, is width 100% and stays legible at 360 px because only frontier labels
are drawn.

## 8. What not to do

- Do not add a second headline number in the rail. Overpay is the headline; own /mo is its
  context.
- Do not colour dominated houses red. Overpay is a distance, not a verdict; only the
  `--flag` segment and the `+$` number carry colour.
- Do not show `recovered %`, `resale after reno`, `breakeven` or `peer norm` on the card until
  `arv_psf_renovated` has a sold source (review §5.8). They are still in `detail.json`.
- Do not drop the rank band, the evidence stamp, or the needs-work bar. They all still mean
  what they meant; only the sort changed.
- Do not change any CSS variable, font size, or the card's section order.
