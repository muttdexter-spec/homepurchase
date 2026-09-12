# OneHome crawler: searches and listing details

**Correction 2026-09-09: see Part 6 before running the photo harvest.** The media-host match and the
Size:3 link assumption in Part 2 and in the Overton test run are both wrong on TRREB.

Built and validated live 2026-09-06 against both boards. Every snippet here was run and its output
checked against `listings_master.csv`. Supersedes the accordion-expansion guidance in the operating
manual, which is wrong and should be deleted.

---

## Part 1: Harvest the saved searches

Two searches on two boards, no address overlap. 25 live listings total.

| Board | Account on token | Saved search | Live count |
|---|---|---|---|
| ITSO | alexander.sutcliffe@outlook.com | (unnamed) | 8 |
| TRREB | giuliab1998@gmail.com | "Oakville-Burlington Search" | 17 |

Each token is bound to its own account, so an ITSO listing must be opened with the ITSO token.

```
https://portal.onehome.com/en-CA/property/<listing_id>?token=<board token>&searchId=<board searchId>
```

**The map view renders nothing extractable.** Everything is behind the **"Cards"** toggle.

```js
const btn = [...document.querySelectorAll('button,div,span')]
  .find(e => e.innerText && e.innerText.trim() === 'Cards' && e.offsetParent);
if (btn) btn.click();
await new Promise(r => setTimeout(r, 6000));

const seen = new Set(); const out = [];
document.querySelectorAll('a[href*="/property/"]').forEach(a => {
  const id = (a.getAttribute('href').match(/property\/([^?]+)/) || [])[1];
  if (!id || seen.has(id)) return; seen.add(id);            // 2 links per card
  let c = a; for (let i = 0; i < 8 && c; i++) { if (c.innerText && /MLS/.test(c.innerText)) break; c = c.parentElement; }
  const t = (c && c.innerText || '').replace(/\s+/g, ' ');
  out.push({ id,
    mls:   (t.match(/MLS[®\s#]*([A-Z0-9]+)/) || [])[1] || null,
    price: (t.match(/\$[\d,]+/) || [])[0] || null,
    city:  (t.match(/(Burlington|Oakville|Hamilton|Milton), ON [A-Z0-9]{3} ?[A-Z0-9]{3}/) || [])[0] || null,
    bd:    (t.match(/([\d+]+)\s*bd/) || [])[1] || null,
    ba:    (t.match(/([\d+]+)\s*ba/) || [])[1] || null,
    sqft:  (t.match(/([\d,\-]+) sqft/) || [])[1] || null,
    badge: (t.match(/(Back on Market|New Listing|Price Decrease|Price Increase|Open House)/) || [])[1] || null });
});
JSON.stringify({ results: document.body.innerText.match(/(\d+) Results/)?.[1], n: out.length, rows: out })
```

**Key on the MLS number**, not an address slug. It is on the card, it is unambiguous, and a
terminate-and-relist produces a new MLS for the same address, which is how you detect that trick.

Status badges are transient. Capture them every run.

---

## Part 2: The listing crawler

### Two rules that matter more than the code

**Everything is already in the DOM, hidden by CSS.** `innerText` returns about 3,000 characters with
no rooms, taxes or lot size, which makes the detail sections look gated. They are not. `innerText`
excludes CSS-collapsed panels; `textContent` and ordinary selectors reach all of it. **No sign-in,
no account activation, no credentials.**

**Never click the accordion headers.** On the ITSO account, clicking "Property Details" triggers an
"Unlock The Full Experience" modal that gates the UI. Reading the DOM sidesteps it entirely. The
only safe click on the page is **"Read More"**, which is required for full remarks.

### The crawler

Run on a listing page after about six seconds. Extract details **before** touching any photo,
because opening the lightbox and rendering contact sheets destroys the DOM.

```js
window.__intake = async () => {
  const T = e => e ? e.textContent.replace(/\s+/g,' ').trim() : null;

  // ---- the one safe click: full remarks ----
  const rm = [...document.querySelectorAll('button,a,span,div')]
    .filter(e => e.offsetParent && e.innerText && /^Read More$/i.test(e.innerText.trim()))
    .sort((a,b) => a.innerText.length - b.innerText.length)[0];
  if (rm) { rm.click(); await new Promise(r => setTimeout(r, 1200)); }
  const txt = document.body.innerText;

  // ---- structured fields: 51 to 65 per listing ----
  const fields = {};
  document.querySelectorAll('dl.property-details').forEach(dl => {
    const dts = [...dl.querySelectorAll('dt')], dds = [...dl.querySelectorAll('dd')];
    dts.forEach((dt,k) => { if (dds[k]) fields[dt.textContent.replace(/:$/,'').trim()] = T(dds[k]); });
  });

  // ---- level-aware room table ----
  const rooms = []; let lvl = null;
  document.querySelectorAll('.level-heading, .room-row').forEach(el => {
    if (el.classList.contains('level-heading')) { lvl = T(el); return; }
    const c = [...el.children];
    const name = T(c[0]); if (!name || name === 'Room Type') return;
    const d = el.textContent.match(/([\d.]+)\s*x\s*([\d.]+)\s*ft/);
    const feat = c.slice(1).filter(x => !x.classList.contains('room-details'))
                  .map(T).filter(v => v && !/^[\d.\sxft]+$/.test(v));
    rooms.push({ level: lvl, name, w: d ? +d[1] : null, l: d ? +d[2] : null,
                 sqft: d ? Math.round(d[1]*d[2]) : null, feat });
  });

  // ---- schools (DOM, not innerText regex) ----
  const schools = [...document.querySelectorAll('*')]
    .filter(e => e.children.length === 0 && /^Distance:/.test(e.textContent.trim()))
    .map(e => { let p = e;
      for (let i = 0; i < 4 && p.parentElement; i++) { p = p.parentElement;
        if (/Schools/.test(p.textContent) && p.textContent.length < 200) break; }
      const m = p.textContent.replace(/\s+/g,' ').trim()
                 .match(/^(.+?)(Public|Private) Schools\s*Distance:([\d.]+) km\s*(?:Grades:(\S+))?/);
      return m ? { name: m[1].trim(), type: m[2], km: +m[3], grades: m[4] || null } : null; })
    .filter(Boolean);

  const isp = (() => { const a = txt.indexOf('Internet Service Providers'), b = txt.indexOf('Powered by');
    return a > -1 && b > a
      ? [...new Set(txt.slice(a,b).match(/\b(DSL|Cable|Fiber|Fixed Wireless|Satellite)\b/g) || [])] : []; })();

  return {
    listing_id:  (location.pathname.match(/property\/([^?]+)/) || [])[1],
    mls:         (txt.match(/MLS[®\s#]*([A-Z0-9]+)/) || [])[1] || null,
    list_price:  (txt.match(/\$[\d,]{7,}/) || [])[0] || null,
    est_monthly: (txt.match(/Estimated\s*\$?([\d,]+)\/mo/) || [])[1] || null,
    dom:          +((txt.match(/Days on OneHome\s*(\d+)/) || [])[1] || 0) || null,
    photo_count:  +((txt.match(/1 \/ (\d+)/) || [])[1] || 0) || null,
    virtual_tour: /View Virtual Tour/.test(txt),
    open_houses:  /No upcoming open houses/.test(txt) ? 0 : 1,
    scores: Object.fromEntries([...txt.matchAll(/(Walk|Bike|Transit)\s+(\d+)\/100/g)]
              .map(m => [m[1].toLowerCase(), +m[2]])),
    remarks: (T(document.querySelector('.overview-container')) || '')
               .replace(/Read (More|Less)$/,'').trim() || null,
    schools, isp, fields, rooms
  };
};
JSON.stringify(await window.__intake());
```

### Validated output

**2450 Overton (ITSO)**: 65 fields, 14 rooms across Main Level / Second Level / Basement,
remarks 1,043 chars, 10 schools with nearest at 0.43 km, walk 40 / bike 50 / transit 30, 50 photos.

**2105 Maplewood (TRREB)**: 51 fields, 18 rooms, virtual tour present.

Cross-checked against `listings_master.csv` and matching exactly: lot `49.86 x 104.12`, annual taxes
`$5,684`, year built 1987, neighbourhood `341 - Brant Hills`, zoning `R3.2`, basement
`Full, Finished, Sump Pump`, below grade 839 sqft, primary bedroom 158 sqft, minimum secondary
bedroom 122 sqft, bedrooms under 100 sqft = 0, nearest school 0.43 km.

### Field inventory

`fields` returns, among others: Beds, Above and Below Grade Bedrooms, Total / Full / Half Bathrooms,
Above and Below Grade Finished Area, Building Area Total Range, Storeys, Basement, Fireplace and
count, Rooms Total, Property Type, Style, **Lot Size Dimensions**, Parking Spots, Garage Spaces,
Garage/Parking Features, Attached Garage, Direction Faces, Heating, Cooling, Laundry Features,
Sewer, Water Source, Construction Materials, Year Built, Year Built Details, Roof, Foundation
Details, Property Attached, List Price, Price per Sq Ft, **Inclusions**, **Exclusions**, Other
Structures, Lease Considered, Zoning Details, Possession, Listing Brokerage and Phone, Tax Year,
**Annual Taxes**, Region, Directions, Municipality, **Neighbourhood**, Community Features,
Postal City.

---

## Part 3: Raw to grading fields

Everything the grading model needs, and where it comes from. `AG` means above grade, meaning any
room whose `level` is not Basement or Lower.

| Grading field | Source |
|---|---|
| primary_bed_sqft | max `sqft` of AG rooms matching /Bedroom/ |
| min_secondary_bed_sqft | min `sqft` of AG bedrooms |
| beds_under_100sqft | count of AG bedrooms with `sqft` < 100 |
| kitchen_sqft | `sqft` of the Main Level Kitchen row |
| main_living_sqft | sum of Main Level Living, Family and Dining rows |
| n_4pc / n_3pc / n_2pc | count Bathroom rows whose `feat` contains Four / Three / Two Piece |
| lower_kitchen | any Kitchen row at Basement level |
| lower_laundry / second_laundry | Laundry rows by level, and count > 1 |
| hardwood_rooms / carpet_free | scan `feat` across rooms for Hardwood, Carpet |
| flooring per room | `feat` on each room row |
| sqft_above / sqft_below | fields: Above / Below Grade Finished Area |
| lot_frontage_ft / lot_depth_ft / lot_sqft | fields: Lot Size Dimensions, split on `x` |
| annual_taxes / tax_year | fields: Annual Taxes, Tax Year |
| year_built / style / storeys / basement | fields, direct |
| zoning / neighbourhood / municipality | fields, direct |
| parking_spots / garage_spaces / attached_garage | fields, direct |
| heating / cooling / roof / foundation / construction | fields, direct |
| inclusions / exclusions | fields, direct |
| appliance_tier | derive from Inclusions text plus Kitchen row `feat` |
| separate_entrance / suite_ready_score | derive from Basement field, remarks, lower kitchen and bath |
| mech_ages / oldest_mech_yr | mine `remarks` for year patterns near furnace, roof, windows, a/c |
| nearest_school_km / schools_within_1km | `schools`, min km and count km <= 1 |
| score_walk / score_bike / score_transit | `scores` |
| photo_count | direct |
| dom_onehome | direct |
| remarks / remarks_len | direct, untruncated |
| fiber_available / isp_types | `isp`, best effort, see caveat |

### Two fields the PDF process was losing

The room table carries **per-room flooring** and **per-room features**, for example Maplewood's
`Kitchen | Quartz Counters, Stainless Steel Appliance(s)` and `Living Room | Fireplace, Shutters`.
These do not appear to have survived the PDF parse.

This is structured condition evidence available before a single photo is viewed, and it upgrades the
claim-versus-evidence check in the analysis spec from a judgment call to a hard contradiction test.
If the room table says quartz and stainless and the photo pass returns `laminate` and
`white appliances`, something is wrong and the listing gets flagged.

It also lets the photo pass be aimed at what the text does **not** settle, which is the design
principle in section 4 of the analysis spec.

---

## Part 4: Sequencing one listing

```
1. Navigate to the listing URL with the matching board token
2. Wait ~6s
3. Run __intake()                      → data.json
4. Then run the photo harvest          → observations.json
   (see section 11 of the analysis spec; it clicks a photo and rewrites document.body,
    which is why details must be captured first)
5. Optionally print to PDF as an archive artifact
```

One page load, no manual expansion, no print dialog, no sign-in.

### Known gaps and caveats

- **ISP data is unreliable.** The widget is a third-party iframe (Cordless) that loads
  asynchronously and returned different provider lists across runs on the same listing. Treat
  `fiber_available` and `isp_types` as best-effort and do not let them influence a grade.
- **Some listings have no room dimensions at all.** Where the agent did not enter them, `.room-row`
  entries exist with null sqft. That is a real data gap, not an extractor failure, and it should
  feed `evidence_completeness` rather than silently defaulting.
- **Bathroom rows carry no dimensions**, only piece counts in `feat`. Expected.
- **Broker-only fields** such as offer instructions are not in the consumer portal. Where
  `listings_master.csv` has `offers_note`, that came from remarks text, and it should keep coming
  from there.
- The remarks "Read More" click is safe on both boards and was verified not to trigger the gate.

---

## Part 5: Reconciliation against the prior 28

**Four listings are gone** since `listings_master.csv` was built:

| Address | Prior grade |
|---|---|
| 2150 Hunt Crescent | A- |
| 3148 Bentworth Drive | A |
| 1228 Pallatine Drive | A |
| 2293 Oakhaven Drive | B- |

Three of the eight A and A- homes are no longer available. Find out whether they sold and at what
price. **These are the first four entries for `sold.csv`**, and the most valuable ones you will ever
get, because grades and condition data already exist for them. A sold price on a home you already
scored is a direct calibration point for the entire model.

**One listing is new** and has never been analysed: **1379 Christina Court**, Burlington L7P 2V8,
$1,299,900, 3+1 bd, 3 ba, 1500-2000 sqft, MLS W13677482.

### Act on this before any grading runs

**Two homes are "Back on Market": 2105 Maplewood (A-) and 4831 Columbus (A-).** Back on market means
a firm deal collapsed, usually a failed inspection, financing falling through, or a buyer walking
during conditions. On homes the model graded A-, a collapsed deal is direct market evidence about
exactly what the model was getting wrong. Have the agent ask both listing agents why before spending
analysis on them.

**28 Osborne shows a Price Decrease** and was already graded D. Consistent with the model. Capture
the original list price for price history.

### Intake order

`claude/listings_live_queue.csv` holds all 25 with board, listing id, MLS, price, beds, baths, sqft,
badge and prior grade.

1. **1379 Christina Court**, the only completely unanalysed listing.
2. **2105 Maplewood and 4831 Columbus**, pending the back-on-market answers.
3. The five one-full-bath homes from section 8A of the analysis spec, which carry the highest-ROI
   fix and which the old model could not see: 343 Duncombe, 3453 Hannibal, 1486 Barker,
   495 Tipperton, 1432 Dewbourne.
4. Everything else in current-grade order.

Every one of the 25 gets a full image review regardless of queue position.


---

## Part 6: corrections from the 2026-09-09 TRREB batch

Found live while running seven listings. The first two would have returned zero photos on every
TRREB listing, which reads exactly like "the click missed" and invites a retry loop.

### 1. The media host is board-specific

`testrun-overton.md` section 5 matches on `matrixmedia`. That is the ITSO host. TRREB serves from
`media.trreb.mlxmatrix.com`. **Match on the endpoint, not the host:**

```js
const first = [...document.querySelectorAll('img')].find(i => /GetMedia\.ashx/.test(i.src || ''));
```

The rest of the Overton fix stands: no `naturalWidth` filter, `scrollIntoView` first, then click,
then wait. Six seconds is safer than five on a 48-photo listing.

### 2. Size:3 links cannot be minted. They only appear after the click.

The `t=` query parameter is a signed JWT whose payload carries `Size` and `Number`. Editing the
payload to `Size:3` and re-attaching the original signature fails to load — the signature is
verified server-side. Before the gallery click the DOM holds only `Size:1` thumbnails, which are
**133x88 px**, far below even contact-sheet usefulness. After the click both sizes are present and
the Size:3 set is complete.

```js
const dec = t => JSON.parse(atob(t.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
const map = new Map();
[...document.querySelectorAll('img')].map(i => i.src).filter(s => /GetMedia\.ashx/.test(s))
  .forEach(s => { const p = dec(new URL(s).searchParams.get('t'));
                  if (p && p.Size === '3') map.set(+p.Number, s); });
window.__photos = [...map.entries()].sort((a,b) => a[0]-b[0]).map(e => e[1]);
```

### 3. `photo_count` reads the wrong counter on TRREB

`txt.match(/1 \/ (\d+)/)` takes the first match. TRREB listing pages render two counters in the
header — on 3217 Hazelwood, `1 / 21` above `1 / 40`. The extractor returned 21 on a 40-photo
listing, which would have silently passed a coverage check at 21 of 21.

**Take the total from `window.__photos.length`, not from the page text.** Keep the text value only
as a cross-check, and treat a mismatch as a coverage failure.

### 4. Pane width, and what "full resolution" actually means here

The desktop browser pane is roughly **496 x 630 CSS px** and screenshots come back at about
**800 x 1016**, so roughly 1.6x. The spec's 760px single-photo target cannot be met as a CSS width,
but it does not need to be: an image rendered at 496 CSS px is captured at about 800 px, which is
better than the 760 the spec asks for. `resize_window` does not help — an emulated viewport larger
than the pane is scaled down to fit, so it costs detail rather than adding it.

Contact sheets at tile width 128 give 3 tiles per row and about 21 photos per screenful, which
matches the Overton finding.

### 5. Two fields that came back empty and should not be trusted blind

- `Year Built` was **absent** on one TRREB listing (3469 Caplan) and present on the others. An
  absent year silently becomes the worst-case era in costing, which is the right default but must be
  flagged rather than reported as a number.
- The `h1` address selector missed on one listing. Take the address from the page text near the
  price instead.
