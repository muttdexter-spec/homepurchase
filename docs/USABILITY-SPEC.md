# Usability spec: the page as the tool that decides viewings and the purchase

Written 2026-09-13 against the shipped `full.html` (md5 `e4ca7f5a…`). Scope: what the page
needs to do three jobs without another redesign. (1) On a weekday evening, pick which houses to
see on Saturday. (2) In the house, record what you saw. (3) At the end, choose one and decide
what to offer, together. Everything here is additive on the page Opus built and reuses its
components. Items marked **now** ship in this pass; nothing is marked "later" because the brief
is to stop revising.

## 0. Two things that are wrong today, and why

**The monthly numbers disagree because they are different numbers.** The bottom table's
`Total / mo` is the calculator: mortgage principal and interest at 4.25% on 80% over 25 years,
plus tax, plus reserve. Cash out the door each month. The card's `$6,920 /mo to own · 5 yr` is the
economic cost of the hold: interest-only at 4.0% on the full price, plus 5.5% exit commission,
land transfer tax, closing costs and the unrecovered day-one work, spread over 60 months, with
no principal. For Yarmouth that is $6,210 against $6,920. Both are labelled "/mo". They will
never agree, and one of them should not be a monthly number at all. Fix in §1.

**"+$1,710 /mo extra, for no more house" is the v5 overpay.** It says: the cheapest house whose
facts score is within three points *or higher* costs $1,710 a month less to own, and that house
is Enfield. The page then says Enfield "scores about the same", which is false (Enfield scores
14 points higher), and it compares a $1.3M Oakville raised bungalow with a double garage to an
$825k Burlington bungalow with oil heat, which is a comparison the facts score cannot carry.
It is a price argument, not a house argument, and it does not belong on a card. Removed from
the card entirely (§4.3 keeps its one legitimate use).

## 1. One vocabulary, seven terms

Every number on the page is one of these, named exactly this way, defined once in the glossary,
and never given a second name. Anything not in this list is deleted or renamed.

| Term | What it is | Where | Unit |
|---|---|---|---|
| **Score** | The v6 composite, your weights | rail, table, compare | 0 to 100 |
| **Grade** | The facts letter, unchanged | rail, score panel | A to D |
| **Condition** | Share of this house's work not expected | score panel, compare | 0 to 100, with the $ behind it |
| **Monthly payment** | Mortgage P&I at the page settings + tax + upkeep | rail, money, table, calculator | $/mo |
| **Day-one work** | p80 of what must be done before move-in | money, compare | $ |
| **Wish list** | p80 of kitchen, baths, basement, if you choose | money, compare | $ |
| **5-year cost** | What owning for the hold costs beyond getting the price back: financing, exit commission, LTT, closing, unrecovered day-one work, tax, upkeep. The basis of the price component. | money (one line), compare | $ total, **never /mo** |

Retired words: *true cost, own /mo, cost to own, extra, overpay, frontier, best value, needs-work,
reserve* (becomes *upkeep*), *carry*. `Cash on closing day` stays as the calculator's name for
down payment + LTT + closing + day-one work, and is the G3 gate.

**Monthly payment is the only thing with "/mo" after it.** It is computed once, in the page's
JavaScript, from three global settings, and every place that shows it reads the same function.

## 2. Global settings, in the control bar (`.sr-ctl`)

Down payment %, mortgage rate, amortization, hold (3/5/10). Defaults from `costs.yaml`:
`hold.mortgage_rate: 0.0425`, `hold.down_payment: 0.20`, `hold.amortization: 25`,
`hold.years_default: 5`. `hold.cost_of_capital` is no longer a free number; it is derived in
`score.py` as `0.8 × mortgage_rate + 0.2 × hold.opportunity_rate (0.03)`, so the ranking's price
component and the page's monthly payment come from the same rate by construction. The control
bar says "Ranked at 4.25%, 20% down, 5 years" and, when the user changes a setting, "Ranked at
4.25%; you are viewing 5.0%". Monthly payment and cash on closing re-derive live; the rank does
not (it is Python), and the page says so in the same sentence. Settings persist in localStorage.

## 3. Job 1: choosing Saturday's viewings

### 3.1 What changed since last build **(now)**

A line in the mast, built by the pipeline from the previous `out/decision.csv` and
`live_*.json`: "Since 12 Sep: 3 new · 2 gone · 1 price drop · 1 back on market". Each word
filters the cards. Needs three fields on every record and one file:

- `status: active | conditional | sold | delisted`, `status_date`, `sold_price` (null until
  known). A sold or delisted house stays in the batch, greyed, with its rank frozen, its card
  intact, and the sold price shown when known. **This is how sold comps accumulate**: every
  `sold_price` lands in `out/sold.csv` with the house's usable area and municipality, and the
  day there are five of them, `arv_psf_renovated` can be replaced. Nothing else in the model
  has to change for that.
- `price_history: [[date, price], …]`, appended by the crawl when the ask changes.
- `out/batch_YYYY-MM-DD.json` written on every build (rank, score, ask, status per house), so the
  diff is against the last build and the frontier of the search is visible over time.

### 3.2 Saturday plan **(now)**

An "Add to Saturday" toggle on every card (same `.stamp` styling, `.on` when set), a strip under
the control bar listing the plan in rank order with addresses, and two buttons: "Route in Google
Maps" (a `https://www.google.com/maps/dir/?api=1&origin=…&destination=…&waypoints=…` URL built
from the addresses, in plan order) and "Print sheet" (print CSS: one page per house with rank,
score, address, the three highest-value agent questions, the check-when-there list, blank lines
for the gut score and notes). Plan persists in localStorage and exports with the showing record.

### 3.3 Filters and sort **(now)**

The control bar gains: municipality (All / Burlington / Oakville), max ask (a number input), and
sort (Score · Monthly payment · Condition · Band top · Days on market). Cards, strip, jump list
and table all follow the sort. Default is Score.

### 3.4 Data-quality stamps **(now)**

Per card, `.stamp.unseen`: `No room table` (12 today; the layout component cannot lose a bedroom
on these), `Basement area estimated`, `Build year estimated`, `Partner weights pending`. The
reader should know which scores are shaky without opening anything.

### 3.5 Days on market and back on market **(now)**

`60+ days` and `Back on market` stamps from `dom` and `status`. Negotiation context, not a score.

## 4. Job 2: in the house

### 4.1 Card layout on the phone **(now)**

Below the money block, every section is a `<details>` collapsed by default: renovations,
settled by the photos, check when you're there, showing record, rooms, cost lines. In showing
mode (the existing `Walked` / `Not walked` control), "Check when you're there" and the showing
record open by default and the rest stay closed. A sticky mini-header (rank · score · street)
appears when the card's top scrolls off. This is the difference between a card you can use in a
hallway and one you scroll for two minutes.

### 4.2 Two people, one record **(now)**

The showing record already has a verdict and a gut score. Make both per person: `gut_alex`,
`gut_partner` (1 to 10), `verdict_alex`, `verdict_partner`, `notes_alex`, `notes_partner`, and a
`who` selector at the top of the record that persists. The export block carries all of it; the
`observations_patch` merges both people's fields without overwriting the other's. On the card
the two gut scores sit beside the score: "Score 61 · You 7 · Partner 5", and a `Disagree` stamp
appears when they differ by 3 or more (the weights `Disagree` in v6 is on rank; this one is on
gut).

### 4.3 The one place price arguments live **(now)**

In the showing record, under "Before you offer", three lines the pipeline fills: "Cheapest house
scoring within 3 points: Clinton, $1,174,900, monthly payment $180 less" (the old overpay, in
words, where it is useful); "At $1,250,000 this house would score 58 and rank 9; at $1,200,000,
60 and rank 6" (the score at ask minus $50k and minus $100k, pure arithmetic, so you can see
what a discount is worth in rank terms); and "Cash on closing day at your settings: $319,000".
Nothing here is an offer price, and the line says so.

### 4.4 Mechanical years **(now)**

The four `roof_year` / `furnace_year` / `ac_year` / `water_heater_year` inputs Opus added to the
showing record are wired into `cost()` per `RANK-V6-DECISION.md` §7 item 3, and the 18 seller
claims from `mech_ages_stated` pre-fill them as "claimed 2022, verify" so the question at the
showing is "is it 2022?" not "how old is it?".

### 4.5 Offline **(now, small)**

A `manifest.json` and a 20-line service worker that caches `index.html`, `full.html`,
`mobile.html`. The page then opens in a basement with no signal, and "Add to Home Screen" works.
No dotfiles; both files sit at the repo root. GitHub Pages serves them as-is.

## 5. Job 3: deciding, together

### 5.1 Compare view **(now)**

A "Compare" toggle on every card; a sticky "Compare (3)" button appears when two or more are
set; it opens a section at the top of the page (same `.section-head` style) with the chosen
houses as columns and these rows: score, grade, the eight components as `.sp` bars, monthly
payment, day-one work, wish list, 5-year cost, cash on closing day, band, both gut scores, both
verdicts, HOLD and Project stamps, open agent questions (count and the top three), notes from
each person, days on market, and the "before you offer" lines. Up to four columns on desktop,
two on the phone with horizontal scroll. This is the artifact the final decision is made from;
it is also what to print for the agent.

### 5.2 Calibration panel **(now)**

Once five or more houses have a gut score from either person, a small section after the table:
a scatter of gut score (x) against model score (y), one dot per house per person, the fitted
line, and one sentence per component computed by the pipeline from the residuals: "Your gut runs
ahead of the model on lot (+0.4) and behind it on space (−0.3)". Below it, the eight current
weights as `.sp` bars with a note: "To act on this, change `weights.alex` in costs.yaml and
rebuild". This is the mechanism that replaces future redesigns with weight edits. The
computation is a rank correlation between each component and the gut residual; it needs nothing
but the fields in 4.2.

### 5.3 Our picks **(now)**

The existing `Shortlist` filter becomes per person: `My picks` / `Partner's picks` / `Both` /
`Either`. Starred by each person in the showing record's `who` context. `Both` is the decision
set.

## 6. Card and table, final layout

**Rail:** rank · Score · Grade · Monthly payment · Band. Five things. The gated show `-`.

**Under the address:** "Rank 3 of 34 · strongest baths, parking · weakest lot, price · You 7 ·
Partner 5". One line.

**Score panel:** eight `.sp` rows in weight order, `Label · bar · 71 × 14`. Footnote: "Your
weights, set 13 Sep. Condition is the share of this house's work that is not expected; the
dollars are under Renovations."

**Money (`dl.money`):** Monthly payment (hero) · Day-one work · Wish list · 5-year cost ·
Cash on closing day. Five cells. "Ask" moves into the `.where` line where it already appears in
the table. The `Taxes + reserve` cell becomes a sub-line of monthly payment: "$5,600 P&I ·
$458 tax · $147 upkeep".

**Renovations:** heading "Expected work $73k · $195k if everything were done", then the list.
No needs-work bar.

**Table:** rank · House · Score (`.scorecol` bar) · Grade · Monthly payment · Day-one · Condition ·
Band · DOM · Status · Verdict · Flags. Twelve columns, `$/sq ft` and `Over/mo` gone. Sort follows
the control bar.

**Removed from the page:** `$/sq ft` (stays in `decision.csv`), overpay in any form, `Best
value`, `Frontier`, needs-work score, the three table group headers, "Ranked on cost to own
less $120…" footer text, the ask-derived resale block.

**Glossary:** the seven terms in §1, then Band, Project, HOLD, Weights. Twelve entries, each two
sentences.

**Mast:** kicker "rebuilt 14 September 2026 · ranked at 4.25%, 20% down, 5 years · 37 listings,
34 ranked, 3 gated" and the changes line from §3.1.

## 7. What not to do

- No new colours, fonts, sizes or CSS variables. Compare, Saturday strip and calibration reuse
  `.section-head`, `.sp`, `.scorecol`, `.stamp`, `.sr-ctl` styles inline.
- No frontier chart. Dropped.
- No second letter scale on the Score.
- Nothing that requires a network call at a showing. Maps opens in another app.
- Nothing that puts a number next to "/mo" other than Monthly payment.
