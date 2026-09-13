# Usability addendum: what is left

Written 2026-09-13 on top of `USABILITY-SPEC.md` and `V6.1-REFINEMENTS.md`. These are the
remaining changes that alter how well the page evaluates houses, in the order they earn their
place. Everything is additive and reuses existing components. The closing list is what not to
build, so this is the end of the UI list.

## 1. Weight sliders with a live re-rank

You said you are unsure about the weights and you do not want to give numbers. The eight
component scores for every house are already in the page, so a score is one multiply-add away.
Put eight sliders in the weights panel; dragging one re-scores and re-sorts the cards, the strip
and the table on the spot, with the stacked "where the 68 comes from" bar updating under each
panel. A "Reset to fitted" button restores the file weights. A "Save as mine" button records the
slider positions as `weights.alex` with `method: manual_sliders`, which is honest and better
than the current provisional set. Show the fitted weights and the slider weights side by side so
you can see where they disagree. This is the tool for the sentence "I'm not sure about the
weightage"; nothing else answers it as directly.

## 2. "Why A over B" in the compare view

Add one row to the compare view: for each component, the points difference between the two
houses (weight × (score_A − score_B) / 100), and a total. The question you will ask most when
looking at any ranking is why one house is above another, and this answers it in score units:
"Delaney is 2.3 ahead of Barberry: +2.5 space, +1.2 layout, −1.6 price, +0.2 baths, …". With
three or four houses in the view, show it against the first column.

## 3. Decision readiness and next action, per house

A five-box checklist in the card head, rendered as a small progress bar in the existing bar
style: walked · mechanical years known · agent questions answered · HOLD items resolved · both
gut scores in. The first unchecked box is the house's next action, printed as one line under the
address: "Next: ask the agent about the furnace and the tank" or "Next: her score". A house with
all five checked is ready to decide, and the compare view can filter to those. This is what
drives the end of the funnel.

## 4. Agent questions with answers

The questions exist per house; their state does not. Each becomes a row with an answer field and
an "asked / answered" state in the showing record, persisted and exported like the rest. The
mechanical-year questions pre-fill from the seller claims. The roll-up ("3 of 5 answered") feeds
item 3. An answered mechanical year flows into `cost()` on rebuild, which is the only way a
house gets out of the age-prior on its furnace.

## 5. Map with score-coloured pins

Once the addresses are geocoded for the location rebuild, a Leaflet map on OpenStreetMap tiles
is about forty lines: one pin per house coloured by score band, the GO stations as fixed markers,
the Saturday plan drawn as a route, and a pin tap that opens the card. It answers "where is it"
for the two of you and for the location component's sanity. Tiles need a network, so it is a
planning-at-home view; it degrades to nothing at a showing and nothing else depends on it.

## 6. Two-device sync without a backend

Your phone, her phone and the desktop each hold their own localStorage, and the export-and-paste
path is what will make you stop recording. The zero-code fix: a Google Form with the same fields
as the showing record (house, who, verdict, gut score, notes, the four mechanical years, the
answered questions, the plan and picks). The record's "Submit" button opens the form pre-filled
from the page (a URL with `entry.NNN=` parameters), you tap send, and `refresh.sh` pulls the
response sheet as CSV and merges it into `observations_patch` before scoring. No tokens on the
page, works on both phones, both people's records merge on every rebuild. Keep the export block
as the fallback.

## 7. Timeline and offer tracker

Under the showing record, one line per event from `price_history`, `status`, the showing dates
and the offers: "Listed 2 Sep $1,199,000 · Price drop 10 Sep $1,174,900 · Walked 13 Sep (you 7,
her 5) · Offered 20 Sep $1,140,000 · Result …". Offers are recorded in the record with amount,
date, conditions and outcome. This is the memory of the process, and it is where the sold price
lands when a house you passed on sells, which is the start of the sold-comp file.

## 8. Small things that prevent large mistakes

- **Stale build warning**: when the build is more than seven days old, the mast says so in the
  warning colour. The changes line already shows what moved; this says it might be wrong.
- **Changed since you last looked**: a per-device last-visit stamp; cards whose score, price or
  status changed since then carry a small `Changed` stamp for one visit.
- **Backup and restore**: one button that exports everything in localStorage (weights, plan,
  picks, records, settings) as one JSON and one that restores it. Phones get wiped.
- **Band as a bar**: the rank band in the rail as a short range bar on a 1 to 36 axis with a dot
  at the rank, instead of "4 to 7" as text.
- **Sticky compare button and Saturday count** on the phone so they are reachable from any card.

## What not to build

- Listing photos on the card: copyright, weight, and the photo pass already extracted what
  photographs can tell you.
- A two-column card grid on desktop: the table is the dense view; the card is the reading view.
- Swipe between cards: the jump list and sticky header do the job without gesture conflicts.
- Dark mode, themes, fonts.
- A chatbot or free-text search over the cards.
- Anything that fetches at a showing.

## For the prompt

Append as task 8 of `COWORK-PROMPT-v6.1.md`:

> **8. Usability addendum.** `USABILITY-ADDENDUM.md` items 1 to 8, in that order. Item 6 needs a
> Google Form; create the form spec (field names and types) and the prefill URL builder, and
> leave the form itself for me to create from the spec; wire `refresh.sh` to read a
> `responses.csv` if present. Show me the sliders re-ranking live, the "why A over B" row with
> Delaney and Barberry, the readiness bar on a walked house and an unwalked one, and the map.
