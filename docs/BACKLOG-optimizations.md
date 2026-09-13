# Further optimizations to grading, ratings and scores

Beyond `REVIEW-2026-09-12.md`. Each item says what data it needs and whether the listings
have to be browsed again. **Nothing in the review or in v5 needs a photo pass.** Items 1 and
2 are the only ones that touch a listing page at all, and both are one page load, not photos.

Priority: A do now, B do with the next batch, C when there is time.

## Data completeness (these change scores that are already computed)

| # | Item | Why | Data / browsing | Effort | Pri |
|---|---|---|---|---|---|
| 1 | **Room tables for the 12 listings without one** (Rexway, Stillmeadow, Grand, Pondview, Centennial, Aldridge, Lark, Pallatine, Crosby, Windermere, Yarmouth, Wyandotte) | The tiny-bedroom rule and the room-driven score can only fire where a room table exists. Today 25 of 37 have one, so the 12 without are structurally favoured on layout. The rule has fired once (Middlesmoor) and it may be a data error. | **Stage-1 crawl, one page load each, no photos.** `crawl_v3b.js` `__intake()` already extracts rooms. | 1 h | A |
| 2 | **Verify Middlesmoor's 41 sq ft second bedroom** (`rooms_raw`: `['Second','Bedroom',41]`) | 5 × 8 ft is a closet. If it is 141, Middlesmoor is a 3-bed B− at $1.05M and lands near Bunton on the frontier instead of being gated. | **One listing page.** | 5 min | A |
| 3 | **GO station distance per address** (Burlington, Aldershot, Appleby, Bronte, Oakville GO) | The location term is walk + transit + school. For a Toronto commuter in Halton, GO access is the location variable. | Geocode 37 addresses, haversine to five station coordinates. **No listing browsing.** | 1 h | A |
| 4 | **Highway and rail proximity** (QEW, 403, 407, Lakeshore West corridor) | Noise and resale. Demote-only: −2 location within 300 m, −1 within 600 m. | Same geocode as 3, distance to line features. **No browsing.** | 1 h | B |
| 5 | **Conservation Halton regulated area / floodplain flag** | Insurance and resale; a HOLD-class flag, not a score. | Public CH mapping by address. **No browsing.** | 1 h | B |
| 6 | **Ensuite present** | A couple's layout term the grade lacks. `n_4pc` / `n_3pc` by level exist for 8; room tables give it for 25 (item 1 makes it 37). +2 layout. | From room tables. | 30 min | B |

## Scoring logic

| # | Item | Why | Data | Effort | Pri |
|---|---|---|---|---|---|
| 7 | **Per-person fit weights** | The fit score is a preference. Two weight vectors (`fit_weights.alex`, `fit_weights.partner`) in `costs.yaml`, two grade badges on the card, frontier computed on the mean, and a `Disagree` stamp where the two grades differ by a band. Turns the open elicitation problem into a feature. | None. | 2 h | A |
| 8 | **In-page elicitation** | Build the review's §2.9 questions into the page: the frontier-five choice and the six near-frontier pairs, answered by each person, stored and exported through the existing showing-record machinery (`sr-expbox`) as a `preferences_patch`. A small script fits λ and reports whether the chosen "dominated" houses share a feature the fit score lacks (municipality is the candidate). | None. | 3 h | A |
| 9 | **Wire the calculator to the gates** | The page already has cash-to-close and monthly inputs. Entering "cash available" and "max monthly" should grey out cards that fail G2/G3 rather than leaving the gates at `null`. | None. | 1 h | A |
| 10 | **Mechanical `_seen` promotion** | `kitchen_seen` / `bath_seen` / `basement_seen` can promote after a showing; there is no `furnace_seen` / `roof_seen` / `ac_seen` / `panel_seen` wired to the reserve, so a verified 2022 furnace never leaves it. 18 listings carry seller-claimed ages to verify. Add the four toggles to the showing record and zero the reserve line on `new`/`recent`. | Showing record only. | 1 h | A |
| 11 | **Price the pool; HOLD the tank** | `pool_carry_annual` placeholder ($2k / $3k / $5k, UNSOURCED) as a reserve line so POOL stops being a warning that changes nothing. Oil tank stays a HOLD until TSSA status is known. | `costs.yaml`. | 30 min | B |
| 12 | **Lot weight rises with the hold** | At H = 10 land holds value and structure depreciates. `lot.pts` 15 at H ≤ 5, 20 at H = 10 with the space cap lowered by the same 5 so the total stays 100. Exposes the 3-vs-10 year question as a visible difference on the page. | None. | 30 min | B |
| 13 | **Robust-frontier stamp** | Re-run the sensitivity grid (knee 1,600/1,800/2,200 × tol 0/3/6 × demote on/off × H 3/5/10) in the build and stamp houses on the frontier in every cell. Today: Clinton, Hazelwood, and Enfield or Cavendish. | None. | 1 h | B |
| 14 | **DOM and back-on-market stamps** | `dom` is in every record (Samford 72, Barberry 66, Pallatine 65, Yarmouth 50, Osborne 46). Not a rank input; a negotiation-context stamp `60+ days`. Maplewood and Columbus were back-on-market per `00-README.md`; a `Back on market` stamp with the standing agent question. | Existing fields. | 30 min | B |
| 15 | **Sold $/sq ft by pocket** | Replaces `arv_psf_renovated`, which is ask-derived and produces the artifacts in review §5.8. Until then the resale block stays hidden on the card. | **Ask the agent.** Four sold addresses are already named in `00-README.md`. | External | A |
| 16 | **Batch log** | The fit grade is absolute; overpay is batch-relative. Write `out/frontier_YYYY-MM-DD.json` on every build so that when a listing sells or drops off, the page can say what moved and why. | None. | 30 min | C |
| 17 | **Floor tell has no power** | `floor_condition = no_defect_seen` on 36 of 37. A tell that is the same on every row discriminates nothing and is the second-largest day-one line. Replacing it with material + visible-wear tells would need a re-read of floors at full resolution. | **Full photo pass. Not recommended now.** | Days | C |
| 18 | **Tiny-bedroom rule per room** | −4 flat for any bedroom under 100 sq ft; could be −2 per bedroom under 100 and −4 under 80. Minor. | Room tables. | 15 min | C |

## Presentation (see DISPLAY-SPEC.md)

| # | Item | Pri |
|---|---|---|
| 19 | Cost bullet bar under the money panel (existing `.rh-bar`) | A |
| 20 | Condition row in the score panel, shown as a subtraction | A |
| 21 | Hold toggle 3 / 5 / 10 in the control strip, numbers switch, order does not | A |
| 22 | Frontier group header in the whole table; `F` in the rank slot | A |
| 23 | Frontier chart SVG in the table section (the only new element) | B |
| 24 | `Worth a look` stamp from the rank band | A |

## Answer to "do I have to browse again?"

No, for everything in v5 and for items 3 to 24. Items 1 and 2 are stage-1 page loads (room
tables and one bedroom dimension), about an hour, and they are worth it because they make the
layout score consistent across all 37. Item 17 would need a photo pass and is not worth it
now. Item 15 is a question for the agent, not a browse.
