Read `V6.1-REFINEMENTS.md` first; it is the spec for this pass. It is additive on the
14 September build and changes no catalog cost, no CSS variable, no card section order. Then
do the following in order and show me each before the next.

## 1. Answers you need from me

Record these in `costs.yaml` exactly as given before you compute anything.

- Payment: comfortable $[FILL] a month, maximum $[FILL] a month (P&I + tax + upkeep).
- Space: cramped below [FILL] sq ft above grade; more stops mattering above [FILL] sq ft.
- Yard: [matters / does not matter]. If it matters: small is [FILL] sq ft, plenty is [FILL].
- Ensuite: [matters / does not matter].

## 2. Location rebuilt (§2)

Geocode the 37 addresses (cache in `pipeline/geo.json`), add the fixed tables (GO stations,
highways and the rail corridor as line features, major parks, the lake, a Halton arterials
list) to `costs.yaml`, and compute the five parts. The assigned-school lookup is a web call per
address; cache it; if it fails, score the midpoint and stamp `Location partly estimated`. Show me
the 37 location scores old and new, and which five houses move most.

## 3. Price rebuilt (§3), space, lot and layout anchors (§5)

Price on monthly payment at the `costs.yaml` defaults with my comfortable and maximum figures;
gate at maximum. Space and lot anchors from my numbers. Ensuite into layout if I said it matters.
Show me how many houses sit at price 100, and which are gated by the maximum.

## 4. Pairs, re-selected and fitted (§7.1, §7.2)

Re-run the D-optimal selection on the rebuilt components. If choices exist from the 14 September
build, keep them, re-fit, and report the movement. Apply the 11-of-15 consistency gate. Update
the pair section on both pages with the new pairs.

## 5. The why (§4)

Under the score panel: the stacked contribution bar and its two lines; the per-component
one-liners with the batch-range mini-bar and "adds X of Y"; the scale text moved to one "How the
scales work" box in the glossary; the effective-influence row next to the weights. Delete the
current "Why each score" prose.

## 6. Money block (§6) and stamps (§7.3 to §7.5)

The five cells with their sub-lines, the 5-year cost reconciliation, the "Price and financing"
strip removed. Ties, `Robust`, one `Weights provisional` in the mast and none on cards, the band
with the rate variant. Then the letter grade, per the last message: removed from the rail, the
panel, the address line, the table and the glossary, the "two different numbers" paragraph
deleted, `grade` kept in `decision.csv` and `detail.json` and rendered nowhere.

## 7. Rebuild, verify, package

Both pages, 1280 and 360 px, no JS errors. Show me one card with the new why block, the money
block for Barberry with its sub-lines, the location table from step 2, and the mast. Then
`QA-PASS-2026-09-15.md` with what changed, the location and price movements, the fitted weights
if the choices are in, and everything you were unsure about. Package as before, no dotfiles.

## Stop and ask me if

- geocoding or the school locator fails on more than five addresses;
- my payment maximum gates more than a third of the batch;
- the D-optimal selection cannot meet the three-pairs-per-component constraint;
- anything would touch a catalog number, a CSS variable or the card section order.
