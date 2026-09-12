#!/usr/bin/env python3
"""Showing record: the interactive half of the walk-through page.

Everything here is generated per listing from the same observations the model scores, so the
questions the page asks are exactly the fields score.py is currently guessing at. Answers are
written to the artifact's shared store (db capability) and exported as a patch that merges
straight into observations.json.

Imported by build_walkthrough.py. Nothing in here touches the ranking.
"""
import html, json

def esc(s): return html.escape(str(s if s is not None else ""))

# ---------------------------------------------------------------- the questions
# field -> (question, [(value, chip label, is_bad)]).  Values are the exact enums score.py reads.
QS = {
 "kitchen_sink_mount":   ("Kitchen sink", [("undermount","Undermount",0),("topmount","Topmount, visible rim",1)]),
 "kitchen_counter_edge": ("Counter edge", [("square_eased","Squared, stone",0),("rolled_bullnose","Rolled, laminate",1)]),
 "kitchen_soffit":       ("Above the uppers", [("removed","Runs to ceiling",0),("present","Bulkhead",1)]),
 "kitchen_door_profile": ("Cabinet doors", [("crisp_shaker","Crisp shaker",0),("slab","Slab",0),
                                            ("raised_panel_square","Square raised panel",0),("soft_raised_panel","Soft raised panel",1)]),
 "bath_tub_type":        ("Main bath tub", [("alcove_tiled","Alcove, tiled",0),("freestanding","Freestanding",0),
                                            ("one_piece_insert","One-piece insert",0),("corner_garden_platform","Corner platform tub",1)]),
 "bath_tile_scale":      ("Bath tile", [("large_format","Large format",0),("subway_modern","Modern subway",0),
                                        ("12x12_wide_grout","12x12, wide grout",1),("small_4x4","4x4, original",1)]),
 "bath_vanity_top":      ("Vanity top", [("undermount_stone","Undermount stone",0),("integrated_modern","Modern integrated",0),
                                         ("vessel_on_wood","Vessel on wood",0),("integrated_cultured_marble","Cultured marble",1),
                                         ("laminate_dropin","Laminate, drop-in",1)]),
 "floor_condition":      ("Floors, where visible", [("no_defect_seen","Nothing wrong",0),("uneven_stain","Uneven or stained",1),
                                                    ("gaps_at_base","Gaps at the base",1)]),
 "ceiling_main":         ("Main-floor ceilings", [("flat_painted","Flat painted",0),("stipple_popcorn","Stipple",1),("drop_tile","Drop tile",1)]),
 "window_frame":         ("Window frames", [("vinyl","Vinyl",0),("wood_original","Original wood",1),("aluminum_original","Original aluminum",1)]),
 "panel_type":           ("Electrical panel", [("breaker","Breakers",0),("fuse","Fuses",1)]),
 "basement_ceiling":     ("Basement ceiling", [("drywall","Drywall",0),("drop_tile","Drop tile",1),("exposed","Exposed joists",1)]),
 "basement_walls":       ("Basement walls", [("drywall","Drywalled",0),("painted_block","Painted block",1),
                                             ("bare_block","Bare block",1),("panelling","Panelling",1)]),
 "basement_moisture":    ("Base of the basement walls", [("none_visible","Dry, nothing visible",0),("efflorescence","Efflorescence",1),
                                                         ("staining","Moisture staining",1)]),
 "driveway":             ("Driveway", [("sound","Sound",0),("cracked","Cracked",1)]),
 "secondary_bath_original": ("Second full bath", [("false","Been done",0),("true","Original",1)]),
}

# which priced line each field moves, for the "what this is worth" hint
FIELD_LINE = {
 "kitchen_sink_mount":"kitchen", "kitchen_counter_edge":"kitchen", "kitchen_soffit":"kitchen", "kitchen_door_profile":"kitchen",
 "bath_tub_type":"main bath", "bath_tile_scale":"main bath", "bath_vanity_top":"main bath", "secondary_bath_original":"bath 2",
 "floor_condition":"flooring", "ceiling_main":"ceilings", "window_frame":"windows",
 "basement_ceiling":"basement", "basement_walls":"basement", "basement_moisture":"waterproofing",
 "driveway":"driveway", "panel_type":"panel",
}

# asked on every house, in the order you actually walk one
WALK = [
 "Kitchen tap and a shower at once: does the pressure hold",
 "Far corner of the basement: any damp or musty smell",
 "Open and close three windows, one on each elevation",
 "Walk the upstairs hall barefoot: slope, bounce, soft spots",
 "Sump pit: is there one, is it dry, does it have a pump",
 "Outside: do grading and downspouts run away from the wall",
 "Main breaker amperage, and any cloth or knob-and-tube in the joists",
 "Supply line at the shutoff: copper, PEX, galvanized or Poly-B",
 "Attic hatch: insulation depth, daylight, staining on the sheathing",
 "Put the car in the garage and shut the door",
 "Two minutes on the front lawn: road, rail, flight path",
 "Phone signal in the basement and the back bedroom",
 "Bathroom fans: do they vent outside, any staining above them",
 "Every interior door: do any scrape or fail to latch",
]

def unresolved(o):
    """The fields this house is still being guessed at on, in question order."""
    out = []
    nf = o.get("baths_full") or 0
    for f, (q, opts) in QS.items():
        if f == "secondary_bath_original":
            if nf > 1 and not o.get(f): out.append(f)
            continue
        if o.get(f) in (None, "", "not_shown"): out.append(f)
    return out

def _hint(f, d):
    """What settling this field is worth on this house."""
    nm = FIELD_LINE.get(f)
    if not nm: return ""
    it = next((i for i in d.get("items", []) if i["name"] == nm), None)
    if not it: return ""
    p = it.get("p")
    if p is None:
        r = next((x for x in (d.get("reno") or []) if x["name"] == nm), None)
        p = r["p"] if r else None
    full = it.get("hi") or 0
    if p is None or p >= 0.99 or not full: return ""
    return f"${round(full/1000):,}k line, carried at {round(p*100)}%"

def questions_html(k, o, d):
    fs = unresolved(o)
    if not fs:
        return '<p class="rnone">Every condition field on this house was settled by the photos. Nothing here needs a call.</p>'
    out = []
    for f in fs:
        q, opts = QS[f]
        hint = _hint(f, d)
        chips = "".join(
            f'<button type="button" class="chip{" bad" if bad else ""}" data-kind="tell" data-h="{k}" data-f="{f}" data-v="{v}">{esc(lab)}</button>'
            for v, lab, bad in opts)
        chips += f'<button type="button" class="chip skip" data-kind="tell" data-h="{k}" data-f="{f}" data-v="not_shown">Still can\'t tell</button>'
        out.append(f'<div class="q"><p class="ql">{esc(q)}{f"<em>{esc(hint)}</em>" if hint else ""}</p><div class="chips">{chips}</div></div>')
    return "".join(out)

MECH = [("roof_year","Roof"), ("furnace_year","Furnace"), ("ac_year","A/C"), ("water_heater_year","Water heater")]

def mech_html(k):
    ins = "".join(f'<label class="my"><span>{lab}</span><input type="number" inputmode="numeric" placeholder="year" min="1940" max="2026" '
                  f'data-kind="mech" data-h="{k}" data-f="{f}"></label>' for f, lab in MECH)
    ins += (f'<label class="my"><span>Panel</span><input type="text" inputmode="numeric" placeholder="amps" '
            f'data-kind="mech" data-h="{k}" data-f="panel_amps"></label>')
    ins += (f'<label class="my wide"><span>Rented equipment</span><input type="text" placeholder="tank, furnace, none" '
            f'data-kind="mech" data-h="{k}" data-f="rentals"></label>')
    return f'<div class="mech">{ins}</div>'

def tri(k, kind, i, text):
    return (f'<li class="tri-row" data-row="{kind}{i}"><span class="tt">{esc(text)}</span>'
            f'<span class="tri"><button type="button" class="ok" data-kind="{kind}" data-h="{k}" data-i="{i}" data-v="ok">Fine</button>'
            f'<button type="button" class="no" data-kind="{kind}" data-h="{k}" data-i="{i}" data-v="issue">Problem</button></span>'
            f'<input class="tn" type="text" placeholder="what you saw" data-kind="{kind}n" data-h="{k}" data-i="{i}"></li>')

def tri_js():
    """The same markup as tri(), built client-side so the generic 14 aren't repeated 37 times in the file."""
    return json.dumps(WALK)

def record_html(k, o, d, checks):
    targ = "".join(tri(k, "targ", i, t) for i, t in enumerate(checks))
    walk = ""   # filled by showing.js from SHOW_DATA.walk when the record opens
    gut = ""
    for w in ("a", "b"):
        btns = "".join(f'<button type="button" class="g" data-kind="gut" data-h="{k}" data-who="{w}" data-v="{n}">{n}</button>' for n in range(1, 6))
        gut += f'<div class="gutrow"><span class="gn" data-person="{w}"></span><span class="gbtns">{btns}</span></div>'
    verdict = "".join(f'<button type="button" class="v v-{v}" data-kind="verdict" data-h="{k}" data-v="{v}">{lab}</button>'
                      for v, lab in [("shortlist","Shortlist"), ("maybe","Maybe"), ("out","Out")])
    return f"""
        <section class="rec" data-rec="{k}">
          <div class="rec-head">
            <h3>Showing record</h3>
            <button type="button" class="visit" data-kind="visited" data-h="{k}">Mark as visited</button>
            <span class="recmeta" data-meta="{k}"></span>
          </div>
          <div class="rec-body">
            <div class="rb">
              <h4>Settle what the photos couldn't <em>this is what the model is guessing at</em></h4>
              {questions_html(k, o, d)}
            </div>
            <div class="rb">
              <h4>Dates off the equipment labels <em>every one of these shrinks the monthly reserve</em></h4>
              {mech_html(k)}
            </div>
            <div class="rb">
              <h4>This house in particular</h4>
              <ul class="tris">{targ or '<li class="tri-row"><span class="tt">Nothing listing-specific flagged.</span></li>'}</ul>
            </div>
            <div class="rb">
              <h4>Every house, same fourteen</h4>
              <ul class="tris walkhost" data-walk="{k}">{walk}</ul>
            </div>
            <div class="rb">
              <h4>Call it</h4>
              <div class="verdicts">{verdict}</div>
              <div class="guts"><p class="gl">Out of 5, each of you</p>{gut}</div>
              <textarea class="notes" rows="3" placeholder="Anything the fields above don't hold" data-kind="notes" data-h="{k}"></textarea>
            </div>
          </div>
        </section>"""

# ---------------------------------------------------------------- styles
CSS = """<style>
  /* ---------- showing record ---------- */
  .rec{border:1px solid var(--rule); border-radius:4px; background:var(--card); overflow:hidden}
  .rec-head{display:flex; align-items:center; gap:12px; flex-wrap:wrap; padding:10px 14px;
    border-bottom:1px solid var(--rule-soft); background:var(--accent-soft)}
  .rec-head{cursor:pointer}
  .rec-head h3{font-family:var(--mono); font-size:10px; letter-spacing:.11em; text-transform:uppercase;
    margin:0; font-weight:500; color:var(--accent); flex:1; display:flex; align-items:center; gap:7px}
  .rec-head h3::before{content:"+"; font-size:13px; line-height:1}
  .rec.open .rec-head h3::before{content:"−"}
  .rec .visit{font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase;
    background:var(--card); color:var(--ink); border:1px solid var(--rule); border-radius:3px;
    padding:5px 10px; cursor:pointer}
  .rec .visit.on{background:var(--clear); border-color:var(--clear); color:#fff}
  .rec .recmeta{font-family:var(--mono); font-size:10px; color:var(--muted)}
  .rec-body{display:none; padding:14px; flex-direction:column; gap:18px}
  .rec.open .rec-body{display:flex}
  .rb h4{font-family:var(--mono); font-size:10px; letter-spacing:.09em; text-transform:uppercase;
    margin:0 0 9px; font-weight:500; color:var(--ink); display:flex; gap:10px; flex-wrap:wrap; align-items:baseline}
  .rb h4 em{font-style:normal; font-family:var(--sans); font-size:12px; letter-spacing:0;
    text-transform:none; color:var(--muted)}
  .rnone{margin:0; font-size:13.5px; color:var(--muted)}
  .q{margin:0 0 11px}
  .q .ql{margin:0 0 5px; font-size:13.5px; display:flex; gap:9px; flex-wrap:wrap; align-items:baseline}
  .q .ql em{font-style:normal; font-family:var(--mono); font-size:10.5px; color:var(--muted)}
  .chips{display:flex; gap:6px; flex-wrap:wrap}
  .chip{font-size:12.5px; line-height:1.2; padding:6px 10px; border-radius:3px; cursor:pointer;
    border:1px solid var(--rule); background:transparent; color:var(--ink); font-family:var(--sans)}
  .chip.on{background:var(--clear-soft); border-color:var(--clear); color:var(--ink); font-weight:700}
  .chip.bad.on{background:var(--flag-soft); border-color:var(--flag)}
  .chip.skip{color:var(--muted)}
  .chip.skip.on{background:var(--rule-soft); border-color:var(--muted)}
  .mech{display:flex; gap:8px; flex-wrap:wrap}
  .my{display:flex; flex-direction:column; gap:3px; font-size:11px; color:var(--muted); width:88px}
  .my.wide{width:190px}
  .my input{font-family:var(--mono); font-size:13px; padding:6px 7px; border:1px solid var(--rule);
    border-radius:3px; background:var(--card); color:var(--ink); width:100%}
  .my input.set{border-color:var(--clear); font-weight:600}
  .tris{margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:4px}
  .tri-row{display:grid; grid-template-columns:1fr auto; gap:6px 10px; align-items:center;
    font-size:13.5px; line-height:1.35; border-bottom:1px dotted var(--rule-soft); padding-bottom:4px}
  .tri{display:flex; gap:4px}
  .tri button{font-family:var(--mono); font-size:9.5px; letter-spacing:.06em; text-transform:uppercase;
    padding:4px 7px; border:1px solid var(--rule); border-radius:3px; background:transparent;
    color:var(--muted); cursor:pointer}
  .tri .ok.on{background:var(--clear); border-color:var(--clear); color:#fff}
  .tri .no.on{background:var(--flag); border-color:var(--flag); color:#fff}
  .tri-row .tn{display:none; grid-column:1/-1; font-size:13px; padding:5px 8px; border:1px solid var(--rule);
    border-radius:3px; background:var(--card); color:var(--ink)}
  .tri-row.flagged .tn{display:block}
  .tri-row.done .tt{color:var(--muted)}
  .verdicts{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px}
  .verdicts .v{font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase;
    padding:7px 13px; border:1px solid var(--rule); border-radius:3px; background:transparent;
    color:var(--ink); cursor:pointer}
  .verdicts .v-shortlist.on{background:var(--clear); border-color:var(--clear); color:#fff}
  .verdicts .v-maybe.on{background:var(--accent); border-color:var(--accent); color:#fff}
  .verdicts .v-out.on{background:var(--flag); border-color:var(--flag); color:#fff}
  .guts{margin-bottom:11px}
  .guts .gl{margin:0 0 5px; font-family:var(--mono); font-size:10px; letter-spacing:.08em;
    text-transform:uppercase; color:var(--muted)}
  .gutrow{display:flex; align-items:center; gap:9px; margin-bottom:4px}
  .gutrow .gn{font-size:12.5px; color:var(--muted); width:74px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .gbtns{display:flex; gap:4px}
  .gbtns .g{width:27px; height:27px; border:1px solid var(--rule); border-radius:3px; background:transparent;
    color:var(--ink); font-family:var(--mono); font-size:12px; cursor:pointer}
  .gbtns .g.on{background:var(--accent); border-color:var(--accent); color:#fff}
  .notes{width:100%; font-family:var(--sans); font-size:13.5px; line-height:1.5; padding:8px 10px;
    border:1px solid var(--rule); border-radius:3px; background:var(--card); color:var(--ink); resize:vertical}

  /* interactive version of the old check list */
  .check .tris .tt{font-size:14px}

  /* ---------- control bar ---------- */
  .bar{position:sticky; top:0; z-index:40; display:flex; gap:10px; align-items:center; flex-wrap:wrap;
    padding:10px 14px; margin:0 -14px; background:color-mix(in srgb, var(--paper) 92%, transparent);
    backdrop-filter:blur(8px); border-bottom:1px solid var(--rule)}
  .bar .modes{display:flex; gap:5px; flex-wrap:wrap}
  .bar .m{font-family:var(--mono); font-size:10px; letter-spacing:.07em; text-transform:uppercase;
    padding:6px 10px; border:1px solid var(--rule); border-radius:3px; background:var(--card);
    color:var(--ink); cursor:pointer}
  .bar .m.on{background:var(--ink); border-color:var(--ink); color:var(--paper)}
  .bar .who{display:flex; align-items:center; gap:5px; margin-left:auto}
  .bar .who input{width:82px; font-size:12px; padding:5px 7px; border:1px solid var(--rule);
    border-radius:3px; background:var(--card); color:var(--ink)}
  .bar .who .sw{font-family:var(--mono); font-size:10px; padding:5px 8px; border:1px solid var(--rule);
    border-radius:3px; background:var(--card); color:var(--muted); cursor:pointer}
  .bar .who .sw.on{background:var(--accent); border-color:var(--accent); color:#fff}
  .bar .exp{font-family:var(--mono); font-size:10px; letter-spacing:.07em; text-transform:uppercase;
    padding:6px 10px; border:1px solid var(--accent); border-radius:3px; background:transparent;
    color:var(--accent); cursor:pointer}
  .pill{font-family:var(--mono); font-size:10px; color:var(--muted)}
  .pill.ok{color:var(--clear)} .pill.warn{color:var(--flag)}
  .strip{border:1px solid var(--rule); border-radius:4px; background:var(--card); padding:12px 14px; display:none}
  .strip.on{display:block}
  .strip h3{font-family:var(--mono); font-size:10px; letter-spacing:.11em; text-transform:uppercase;
    margin:0 0 8px; font-weight:500; color:var(--accent)}
  .strip ol{margin:0; padding-left:20px; font-size:14px; line-height:1.6}
  .strip .sv{font-family:var(--mono); font-size:10.5px; margin-left:8px; color:var(--muted)}
  .strip .empty{margin:0; font-size:13.5px; color:var(--muted)}
  .lot.hide{display:none}
  .expbox{display:none; flex-direction:column; gap:8px}
  .expbox.on{display:flex}
  .expbox textarea{width:100%; height:180px; font-family:var(--mono); font-size:11px;
    border:1px solid var(--rule); border-radius:3px; background:var(--card); color:var(--ink); padding:8px}
  @media (max-width:560px){
    .rec-body{padding:11px}
    .my{width:calc(50% - 4px)} .my.wide{width:100%}
    .bar{margin:0 -20px; padding:9px 20px}
    .bar .who{margin-left:0; width:100%}
  }
</style>
"""
