# Stage 2 — photo forensics, one listing

This listing has passed the Stage 1 gate (or the buyer asked for every listing). Your job is to settle
condition fields at full resolution and return a small record. About 12k tokens with the 8-frame
protocol: one sheet, one fit, one or two reads. Do not exceed 5 screenshots.

## Hard rules

1. **Photos demote, never promote.** No photo may raise a condition call above `unverified`.
   There is no positive value for any `_verdict` field.
2. **A condition call from a contact sheet is void.** The sheet is inventory and room-typing only.
3. **Staging is adversarial.** Every surface a staged object sits on or covers is `not_shown` and
   goes in `concealed_surfaces`. A throw over a tub, a rug over a floor, a cutting board over a
   counter seam.
4. **`hdr_blowout: severe` forces every finish field to `not_shown`.** Clipped whites and no wear
   anywhere in an older house means you saw nothing.
5. Return **only** the fields listed at the bottom. Anything else is a token paid for and never used.

## Tools

Load in ONE call:
`ToolSearch` query `select:mcp__remote-devices__Claude_Browser__navigate,mcp__remote-devices__Claude_Browser__javascript_tool,mcp__remote-devices__Claude_Browser__computer,mcp__remote-devices__Claude_Browser__resize_window`

The connection to the user's computer can drop. If a browser tool reports the device is not
connected, wait 60 seconds (a bash sleep is fine) and retry, up to about 15 minutes, before giving
up. Losing the session mid-listing means redoing the whole pass.

## Step 0 — viewport (once per session)

`resize_window` width 800, height 1300. At this size the pane's screenshot is the full viewport at
1:1 (800×1300 px). Do not use 1000 (downscaled 0.8x) or 400 (captures only the top-left quadrant).
Reset with preset "desktop" when the session ends.

## Step 1 — load photos

Navigate to the listing URL, wait 6s, then paste this and run it. It loads the gallery, builds the
Size:3 URL list, and defines `__sheet`, `__fit` and `__read`. Every helper lays out inside an
800px-wide container so the whole grid lands inside the screenshot.

```js
await new Promise(r=>setTimeout(r,6000));
window.__photos_load = async () => {
  const dec=t=>{try{return JSON.parse(atob(t.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));}catch(e){return null;}};
  const btn=[...document.querySelectorAll('button,a,[role=button]')].find(e=>e.offsetParent && /View All \d+ Photos?/i.test(e.innerText||''));
  if(btn){ btn.scrollIntoView({block:'center'}); await new Promise(r=>setTimeout(r,1000)); btn.click(); }
  else { const f=[...document.querySelectorAll('img')].find(i=>/GetMedia\.ashx/.test(i.src||'')); f.scrollIntoView({block:'center'}); await new Promise(r=>setTimeout(r,1500)); f.click(); }
  await new Promise(r=>setTimeout(r,8000));
  const m=new Map();
  [...document.querySelectorAll('img')].map(i=>i.src).filter(s=>/GetMedia\.ashx/.test(s)).forEach(s=>{const p=dec(new URL(s).searchParams.get('t')); if(p&&p.Size==='3') m.set(+p.Number,s);});
  window.__P=[...m.entries()].sort((a,b)=>a[0]-b[0]).map(e=>e[1]);
  const probe=new Image(); probe.src=window.__P[0]; await new Promise(r=>{probe.onload=r; probe.onerror=r;});
  window.__NW=probe.naturalWidth; window.__NH=probe.naturalHeight;
  return {total:window.__P.length, natural_w:probe.naturalWidth, natural_h:probe.naturalHeight, btn:!!btn};
};
window.__tell = (specs,bw=394,bh=316) => {
  document.body.innerHTML='<div id=g style="display:flex;flex-wrap:wrap;gap:4px;background:#111;width:800px"></div>';
  const g=document.getElementById('g');
  specs.forEach(([i,x,y,z,lab])=>{
    const id='c'+Math.random().toString(36).slice(2,8);
    g.insertAdjacentHTML('beforeend',`<div style="position:relative;width:${bw}px;height:${bh}px;overflow:hidden;background:#000"><img id="${id}" src="${window.__P[i]}" style="position:absolute"><span style="position:absolute;bottom:0;left:0;background:#000;color:#0f0;font:12px monospace">${i} ${lab||''}</span></div>`);
    const im=document.getElementById(id);
    const pos=()=>{const W=im.naturalWidth*(z||1); im.style.width=W+'px'; im.style.left=(bw/2-W*x/100)+'px'; im.style.top=(bh/2-im.naturalHeight*(z||1)*y/100)+'px';};
    if(im.complete && im.naturalWidth) pos(); else im.onload=pos;
  });
  scrollTo(0,0); return specs.length;
};
window.__fit = (idx) => window.__tell(idx.map(i=>[i,50,50,394/window.__NW,''+i]));
window.__read = (s) => window.__tell(s);
window.__sheet = (w=98) => {
  document.body.innerHTML='<div id=g style="display:flex;flex-wrap:wrap;gap:1px;background:#222;width:800px"></div>';
  const g=document.getElementById('g');
  window.__P.forEach((u,k)=>g.insertAdjacentHTML('beforeend',`<div style="position:relative"><img src="${u}" style="width:${w}px;display:block"><span style="position:absolute;top:0;left:0;background:#000;color:#0f0;font:11px monospace">${k}</span></div>`));
  scrollTo(0,0); return window.__P.length;
};
const r=await window.__photos_load(); window.__sheet(98); await new Promise(r=>setTimeout(r,3500)); JSON.stringify(r)
```

Report `total` and `natural_w`. Then one screenshot of the contact sheet (8 tiles per row at 98px;
50 photos fit in 7 rows).

## Step 2 — inventory from the sheet

Room-type every index. Note which indices show the kitchen, each bathroom, the basement, the
utility room, the exterior, and any floor plan. Note what is missing entirely (no basement frame,
no mechanical frame). **Make no condition calls here.**

## Step 3 — LOCATE with `__fit`, then READ with `__read`

**3a. Locate.** `window.__fit([i1,...,i8])`, wait 3.5s, one screenshot. Eight frames at 394×316
(0.38× of a 1024 source) in a 2×4 grid. This is enough to room-type, spot virtual staging, and
see where in each frame the sink, tub, vanity and ceiling sit. Pick the kitchen, the two best bath
frames, the basement, the utility room if any, and the front exterior.

**3b. Read.** `window.__read([[i,x,y,z,label] × 8])`, wait 3.5s, one screenshot. `x`/`y` are the
percentage centre of interest in the frame, `z` the zoom on the 1024 source. Use z = 2.2 to 2.4
for sink rims, door profiles, vanity junctions and grout; z = 1.4 to 1.8 for ceilings, driveways
and basement wall bases. Past about 3x you are magnifying pixels. If a crop comes back on the
wrong feature, one more read call of eight fixes it; do not exceed three read calls.

Typical read set, one call:

```js
window.__read([[K,55,60,2.4,'sink rim'],[K,30,65,2.4,'door'],[B,60,70,2.2,'vanity top'],
               [B,25,45,2.0,'tub tile'],[E,55,45,2.0,'windows'],[E,50,90,1.6,'drive'],
               [L,50,8,1.4,'ceiling'],[S,15,85,1.8,'bsmt wall base']])
```

| Field | Aim at | Defect reading |
|---|---|---|
| `kitchen_sink_mount` | sink rim, 2.4x | visible raised rim = laminate/topmount. Highest-signal tell there is. |
| `kitchen_counter_edge` | counter in profile, 2.4x | rolled / bullnose / post-form = laminate |
| `kitchen_soffit` | top of upper cabinets, 1.8x | bulkhead present = boxes never replaced (set `kitchen_boxes_new: true` when the doors under it are clearly new slab/gloss) |
| `kitchen_door_profile` | door corner, 2.4x | soft rounded raised panel = old doors painted over |
| `bath_tub_type` | tub surround, 2.0x | corner or drop-in on a tiled platform = 1980s-90s original |
| `bath_tile_scale` | grout line, 2.2x | 4x4 or 12x12 with wide grout = old; `subway_modern` and `large_format` are current |
| `bath_vanity_top` | sink/counter junction, 2.2x | `integrated_cultured_marble` or `laminate_dropin` = old; `undermount_stone`, `integrated_modern`, `vessel_on_wood` = current |
| `window_frame` | frame corner, 2.0x | aluminum or wood original, or fogging between panes |
| `panel_type` | panel door, 2.0x | fuses vs breakers, and amperage |
| `basement_moisture` | bottom 18 inches of wall, 1.8x | efflorescence, staining, fresh paint low only |
| `ceiling_main` | ceiling in raking light, 1.4x | stipple survives every refresh and dates the house. Check a BEDROOM ceiling as well as the main floor; Tania and Pinemeadow are flat downstairs and stippled up. |

Also record, when seen: `secondary_bath_original: true` (a second full bath confirmed original),
`kitchen_boxes_new: true`, `pool` (`in-ground` / `above-ground` / `swim-spa`), `tenanted: true`,
`year_built_est` with `year_built_est_src` when the MLS gives no year, `roof_visual`,
`water_heater_seen`, `furnace_seen`, `exterior_defect`, and `claim_vs_evidence` (remarks that the
photos contradict, e.g. an "in-ground" pool that is above ground).

An `asbestos_suspect` flag is worth setting if you see 9-inch-module resilient floor tile,
vermiculite insulation, wrapped duct/pipe insulation, or a glued/dropped tile ceiling in a pre-1970
house.

## Step 4 — return this and nothing else

One fenced ```json block:

```
{
 "slug": "<given to you>",
 "kitchen_sink_mount": "undermount|topmount|not_shown",
 "kitchen_counter_edge": "square_eased|mitred|rolled_bullnose|not_shown",
 "kitchen_soffit": "present|removed|not_shown",
 "kitchen_door_profile": "crisp_shaker|soft_raised_panel|slab|not_shown",
 "kitchen_verdict": "defect_confirmed|unverified",
 "bath_tub_type": "corner_garden_platform|alcove_tiled|one_piece_insert|freestanding|not_shown",
 "bath_tile_scale": "small_4x4|12x12_wide_grout|large_format|not_shown",
 "bath_vanity_top": "integrated_cultured_marble|undermount_stone|not_shown",
 "bath_verdict": "defect_confirmed|unverified",
 "floor_condition": "uneven_stain|patch_visible|gaps_at_base|no_defect_seen|not_shown",
 "ceiling_main": "stipple_popcorn|flat_painted|drop_tile|not_shown",
 "window_frame": "aluminum_original|wood_original|vinyl|not_shown",
 "panel_type": "fuse|breaker_60|breaker_100|breaker_200|not_shown",
 "basement_ceiling": "drop_tile|drywall|exposed|none|not_shown",
 "basement_walls": "bare_block|painted_block|panelling|drywall|not_shown",
 "basement_moisture": "efflorescence|staining|fresh_paint_low_only|sump|none_visible|not_shown",
 "moisture_confidence": "high|medium|low",
 "driveway": "cracked|sound|not_shown",
 "asbestos_suspect": true/false,
 "photos_total": 0,
 "staging": "professionally_staged|virtually_staged|lived_in|vacant|mixed",
 "hdr_blowout": "none|moderate|severe",
 "concealed_surfaces": [],
 "red_flags": [],
 "notes": "<=80 words, defects and unknowns only"
}
```

Omit `moisture_confidence` unless `basement_moisture` is `efflorescence` or `staining` — it gates an
outright STOP downstream, so only set it when you actually saw something.

No field may contain "renovated", "updated", "good", "excellent" or "modern" as a condition
conclusion. Describe defects and unknowns.
