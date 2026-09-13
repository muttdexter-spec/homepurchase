import re
#!/usr/bin/env python3
"""Showing record, v2 — generalised questions, one note-taker.

Differences from v1:
  * Questions are grouped by AREA and worded plainly ("The kitchen: redone / dated / original")
    instead of one jargon chip set per model field ("rolled_bullnose", "integrated_cultured_marble").
    Each answer still maps to the exact observations.json fields score.py reads; the mapping lives
    in QS[...]["opts"][n]["patch"] and is shipped to the page so the export needs no translation.
  * One person records for both of you. No author tagging, no second gut score.

Used by inject_showing.py, which grafts this onto an already-built walkthrough HTML.
"""
import html, json

def esc(s): return html.escape(str(s if s is not None else ""))

# ---------------------------------------------------------------- questions
# ask: which observations fields, if unresolved, make this question worth asking
# opts: v (stored), label (what you tap), bad (reads as a cost), patch (what goes to observations.json)
UNSET = (None, "", "not_shown")

QS = {
 "kitchen": {
   "label": "The kitchen",
   "tells": ["kitchen_sink_mount", "kitchen_counter_edge", "kitchen_soffit", "kitchen_door_profile"],
   "line": "kitchen",
   "opts": [
     {"v": "done",   "label": "Redone, current",       "bad": 0, "patch": {"kitchen_seen": "done"}},
     {"v": "dated",  "label": "Dated but sound",       "bad": 0, "patch": {"kitchen_seen": "dated"}},
     {"v": "orig",   "label": "Original, needs doing", "bad": 1, "patch": {"kitchen_verdict": "defect_confirmed"}},
   ]},
 "bath": {
   "label": "The main bathroom",
   "tells": ["bath_tub_type", "bath_tile_scale", "bath_vanity_top"],
   "line": "main bath",
   "opts": [
     {"v": "done",  "label": "Redone, current",       "bad": 0, "patch": {"bath_seen": "done"}},
     {"v": "dated", "label": "Dated but sound",       "bad": 0, "patch": {"bath_seen": "dated"}},
     {"v": "orig",  "label": "Original, needs doing", "bad": 1, "patch": {"bath_verdict": "defect_confirmed"}},
   ]},
 "bath2": {
   "label": "The other bathrooms",
   "needs_second_bath": True,
   "tells": ["secondary_bath_original"],
   "line": "bath 2",
   "opts": [
     {"v": "done",  "label": "Also redone",       "bad": 0, "patch": {"secondary_bath_seen": "done"}},
     {"v": "mixed", "label": "One done, one not", "bad": 1, "patch": {"secondary_bath_original": True}},
     {"v": "orig",  "label": "All original",      "bad": 1, "patch": {"secondary_bath_original": True}},
   ]},
 "basement": {
   "label": "The basement",
   "needs_basement": True,
   "tells": ["basement_ceiling", "basement_walls"],
   "line": "basement",
   "opts": [
     {"v": "done",  "label": "Finished properly",   "bad": 0, "patch": {"basement_seen": "done"}},
     {"v": "dated", "label": "Finished but dated",  "bad": 0, "patch": {"basement_seen": "dated"}},
     {"v": "redo",  "label": "Needs redoing",       "bad": 1, "patch": {"basement_seen": "redo"}},
   ]},
 "moisture": {
   "label": "Base of the basement walls",
   "tells": ["basement_moisture"],
   "line": "waterproofing",
   "opts": [
     {"v": "dry",  "label": "Dry, nothing to see", "bad": 0, "patch": {"basement_moisture": "none_visible"}},
     {"v": "damp", "label": "Damp, stained, chalky", "bad": 1,
      "patch": {"basement_moisture": "staining", "moisture_confidence": "high"}},
   ]},
 "windows": {
   "label": "The windows",
   "tells": ["window_frame"],
   "line": "windows",
   "opts": [
     {"v": "vinyl", "label": "Newer vinyl",        "bad": 0, "patch": {"window_frame": "vinyl"}},
     {"v": "mixed", "label": "Some new, some old", "bad": 1, "patch": {"window_frame": "mixed"}},
     {"v": "orig",  "label": "Original wood or aluminum", "bad": 1, "patch": {"window_frame": "original"}},
   ]},
 "panel": {
   "label": "The electrical panel",
   "tells": ["panel_type"],
   "line": "panel",
   "opts": [
     {"v": "b200", "label": "Breakers, 200A", "bad": 0, "patch": {"panel_type": "breaker", "panel_amps": 200}},
     {"v": "b100", "label": "Breakers, 100A", "bad": 0, "patch": {"panel_type": "breaker", "panel_amps": 100}},
     {"v": "b60",  "label": "Breakers, 60A",  "bad": 1, "patch": {"panel_type": "breaker", "panel_amps": 60}},
     {"v": "fuse", "label": "Fuses",          "bad": 1, "patch": {"panel_type": "fuse"}},
   ]},
 "floors": {
   "label": "Floors, where you can see them",
   "tells": ["floor_condition"],
   "line": "flooring",
   "opts": [
     {"v": "ok",   "label": "Nothing wrong",             "bad": 0, "patch": {"floor_condition": "no_defect_seen"}},
     {"v": "bad",  "label": "Uneven, stained or gappy",  "bad": 1, "patch": {"floor_condition": "uneven_stain"}},
   ]},
 "ceilings": {
   "label": "Ceilings",
   "tells": ["ceiling_main"],
   "line": "ceilings",
   "opts": [
     {"v": "flat", "label": "Flat and painted",   "bad": 0, "patch": {"ceiling_main": "flat_painted"}},
     {"v": "text", "label": "Stipple or drop tile", "bad": 1, "patch": {"ceiling_main": "stipple_popcorn"}},
   ]},
 "driveway": {
   "label": "The driveway",
   "tells": ["driveway"],
   "line": "driveway",
   "opts": [
     {"v": "ok",  "label": "Sound",   "bad": 0, "patch": {"driveway": "sound"}},
     {"v": "bad", "label": "Cracked", "bad": 1, "patch": {"driveway": "cracked"}},
   ]},
}
QORDER = ["kitchen", "bath", "bath2", "basement", "moisture", "windows", "panel", "floors", "ceilings", "driveway"]

# the same fourteen in every house, in the order you actually walk one
WALK = [
 "Kitchen tap and a shower at once: does the pressure hold",
 "Far corner of the basement: any damp or musty smell",
 "Open and close three windows, one on each side of the house",
 "Walk the upstairs hall: slope, bounce, soft spots",
 "Sump pit: is there one, is it dry, does it have a pump",
 "Outside: do grading and downspouts run away from the wall",
 "Any cloth-wrapped or knob-and-tube wiring visible in the joists",
 "Supply line at the shutoff: copper, PEX, galvanized or Poly-B",
 "Attic hatch: insulation depth, daylight, staining on the sheathing",
 "Put the car in the garage and shut the door",
 "Two minutes on the front lawn: road, rail, flight path",
 "Phone signal in the basement and the back bedroom",
 "Bathroom fans: do they vent outside, any staining above them",
 "Every interior door: do any scrape or fail to latch",
]

MECH = [("roof_year", "Roof"), ("furnace_year", "Furnace"), ("ac_year", "A/C"),
        ("water_heater_year", "Water heater")]


def asked(o):
    """Which questions this house still needs, in walking order."""
    nf = o.get("baths_full") or 0
    bg = (o.get("sqft_below") or 0) or ("basement" in str(o.get("remarks", "")).lower())
    out = []
    for k in QORDER:
        q = QS[k]
        if q.get("needs_second_bath") and nf < 2: continue
        if k == "bath2":
            if o.get("secondary_bath_original"): continue
            out.append(k); continue
        unresolved = any(o.get(t) in UNSET for t in q["tells"])
        if k == "kitchen" and o.get("kitchen_verdict") == "defect_confirmed": unresolved = False
        if k == "bath" and o.get("bath_verdict") == "defect_confirmed": unresolved = False
        if unresolved: out.append(k)
    return out


def _hint(qkey, d):
    """What settling this area is worth on this house."""
    nm = QS[qkey].get("line")
    it = next((i for i in d.get("items", []) if i["name"] == nm), None)
    if not it: return ""
    p, full = it.get("p"), it.get("hi") or 0
    if p is None or not full: return ""
    if p >= 0.99: return f"${round(full/1000):,}k, already confirmed"
    return f"${round(full/1000):,}k line, carried at {round(p*100)}%"


def questions_html(k, o, d):
    ks = asked(o)
    if not ks:
        return '<p class="sr-none">The photos settled every condition field on this house. Nothing here needs a call.</p>'
    out = []
    for qk in ks:
        q = QS[qk]
        hint = _hint(qk, d)
        chips = "".join(
            f'<button type="button" class="sr-chip{" bad" if op["bad"] else ""}" data-kind="ans" '
            f'data-h="{k}" data-q="{qk}" data-v="{op["v"]}">{esc(op["label"])}</button>' for op in q["opts"])
        chips += (f'<button type="button" class="sr-chip skip" data-kind="ans" data-h="{k}" '
                  f'data-q="{qk}" data-v="unsure">Couldn\'t tell</button>')
        out.append(f'<div class="sr-q"><p class="sr-ql">{esc(q["label"])}'
                   f'{f"<em>{esc(hint)}</em>" if hint else ""}</p><div class="sr-chips">{chips}</div></div>')
    return "".join(out)


CLAIM_WORD = {"roof_year": "roof", "furnace_year": "furnace", "ac_year": "a/c",
              "water_heater_year": "water heater"}
def claimed_year(o, f):
    """v6, USABILITY-SPEC 4.4. The 18 mech_ages_stated claims, pre-filled as 'claimed 2022, verify',
    so the question at the showing is 'is it 2022?' and not 'how old is it?'."""
    t = str(o.get("mech_ages_stated") or "").lower()
    w = CLAIM_WORD.get(f, "")
    if not t or not w: return ""
    m = re.search(re.escape(w) + r"[^.;]{0,40}?((?:19|20)\d{2})", t)
    if not m: m = re.search(r"((?:19|20)\d{2})[^.;]{0,20}?" + re.escape(w), t)
    return m.group(1) if m else ""

def mech_html(k, o=None):
    o = o or {}
    def one(f, lab):
        c = claimed_year(o, f)
        ph = f"claimed {c}, verify" if c else "year"
        cl = " claimed" if c else ""
        return (f'<label class="sr-my{cl}"><span>{lab}</span><input type="number" inputmode="numeric" '
                f'placeholder="{ph}" min="1940" max="2026" data-kind="mech" data-h="{k}" data-f="{f}"'
                + (f' data-claim="{c}"' if c else "") + '></label>')
    ins = "".join(one(f, lab) for f, lab in MECH)
    ins += (f'<label class="sr-my wide"><span>Rented equipment</span><input type="text" '
            f'placeholder="tank, furnace, none" data-kind="mech" data-h="{k}" data-f="rentals"></label>')
    return f'<div class="sr-mech">{ins}</div>'


def short_check(t):
    """The listing-specific lines run long and carry photo numbers. Keep the point, drop the citation."""
    t = t.split(":")[0]
    t = t.split(" (")[0]
    t = t.replace("never framed at readable size", "not shown")
    return (t[:88].rstrip(" ,;") + ("…" if len(t) > 88 else ""))[0].upper() + \
           (t[:88].rstrip(" ,;") + ("…" if len(t) > 88 else ""))[1:]


def tri(k, kind, i, text):
    return (f'<li class="sr-row"><span class="sr-t">{esc(text)}</span>'
            f'<span class="sr-tri"><button type="button" class="ok" data-kind="{kind}" data-h="{k}" data-i="{i}" data-v="ok">Fine</button>'
            f'<button type="button" class="no" data-kind="{kind}" data-h="{k}" data-i="{i}" data-v="issue">Problem</button></span>'
            f'<input class="sr-tn" type="text" placeholder="what you saw" data-kind="{kind}n" data-h="{k}" data-i="{i}"></li>')


def record_html(k, o, d, checks):
    targ = "".join(tri(k, "targ", i, short_check(t)) for i, t in enumerate(checks))
    gut = "".join(f'<button type="button" class="sr-g" data-kind="gut" data-h="{k}" data-v="{n}">{n}</button>'
                  for n in range(1, 6))
    verdict = "".join(f'<button type="button" class="sr-v sr-v-{v}" data-kind="verdict" data-h="{k}" data-v="{v}">{lab}</button>'
                      for v, lab in [("shortlist", "Shortlist"), ("maybe", "Maybe"), ("out", "Out")])
    return f"""
        <section class="sr" data-rec="{k}">
          <div class="sr-head">
            <h3>Notes and verdict</h3>
            <button type="button" class="sr-visit" data-kind="visited" data-h="{k}">Mark as visited</button>
            <span class="sr-meta" data-meta="{k}"></span>
          </div>
          <div class="sr-body">
            <div class="sr-b">
              <h4>What the photos couldn't settle <em>answer these and the ranking changes</em></h4>
              {questions_html(k, o, d)}
            </div>
            <div class="sr-b">
              <h4>Dates off the equipment labels <em>every one shrinks the monthly reserve</em></h4>
              {mech_html(k, o)}
            </div>
            <div class="sr-b">
              <h4>This house in particular</h4>
              <ul class="sr-list">{targ or '<li class="sr-row"><span class="sr-t">Nothing listing-specific flagged.</span></li>'}</ul>
            </div>
            <div class="sr-b">
              <h4>Every house, same fourteen</h4>
              <ul class="sr-list sr-walkhost" data-walk="{k}"></ul>
            </div>
            <div class="sr-b">
              <h4>Call it <em>each of you separately; the export carries both</em></h4>
              <label class="sr-my wide sr-whorow"><span>Who is answering</span>
                <select class="sr-who" data-kind="who" data-h="{k}">
                  <option value="alex">Me</option><option value="partner">My partner</option></select></label>
              <div class="sr-verdicts">{verdict}</div>
              <div class="sr-guts"><p class="sr-gl">Out of 5</p><span class="sr-gbtns">{gut}</span>
                <span class="sr-gpair" data-gpair="{k}"></span></div>
              <textarea class="sr-notes" rows="3" placeholder="Anything the questions above don't hold" data-kind="notes" data-h="{k}"></textarea>
            </div>
          </div>
        </section>"""


CONTROL_BAR = """
  <div class="sr-ctl" id="sr-ctl">
    <div class="sr-modes">
      <button type="button" class="sr-mode on" data-kind="mode" data-v="all">All {N}</button>
      <button type="button" class="sr-mode" data-kind="mode" data-v="todo">Not walked</button>
      <button type="button" class="sr-mode" data-kind="mode" data-v="seen">Walked</button>
      <button type="button" class="sr-mode" data-kind="mode" data-v="short">Shortlist</button>
    </div>
    <button type="button" class="sr-exp" data-kind="export">Export notes</button>
    <span class="sr-pill" id="sr-pill"></span>
  </div>
  <div class="sr-strip" id="sr-strip"></div>
  <div class="sr-expbox" id="sr-expbox">
    <p>Everything recorded so far. Paste it into the chat, or merge the <code>observations_patch</code>
      block into <code>observations.json</code> and run <code>refresh.sh</code> to re-rank on what you saw.</p>
    <textarea id="sr-exptext" readonly></textarea>
  </div>
"""

CSS = """<style>
  /* ---------- showing record ---------- */
  .sr{border:1px solid var(--rule); border-radius:6px; background:var(--card); overflow:hidden; margin-top:4px}
  .sr-head{display:flex; align-items:center; gap:12px; flex-wrap:wrap; padding:11px 14px; cursor:pointer;
    border-bottom:1px solid var(--rule-soft); background:var(--accent-soft)}
  .sr-head h3{font-size:11px; letter-spacing:.09em; text-transform:uppercase; margin:0; font-weight:600;
    color:var(--accent); flex:1; display:flex; align-items:center; gap:7px}
  .sr-head h3::before{content:"+"; font-size:14px; line-height:1}
  .sr.open .sr-head h3::before{content:"\\2212"}
  .sr-visit{font-size:11px; letter-spacing:.04em; text-transform:uppercase; background:var(--card);
    color:var(--ink); border:1px solid var(--rule); border-radius:4px; padding:6px 11px; cursor:pointer; font-weight:600}
  .sr-visit.on{background:var(--clear); border-color:var(--clear); color:#fff}
  .sr-meta{font-size:11px; color:var(--muted)}
  .sr-body{display:none; padding:14px; flex-direction:column; gap:20px}
  .sr.open .sr-body{display:flex}
  .sr-b h4{font-size:11px; letter-spacing:.07em; text-transform:uppercase; margin:0 0 10px; font-weight:600;
    color:var(--ink); display:flex; gap:10px; flex-wrap:wrap; align-items:baseline}
  .sr-b h4 em{font-style:normal; font-size:12px; letter-spacing:0; text-transform:none; color:var(--muted); font-weight:400}
  .sr-none{margin:0; font-size:13.5px; color:var(--muted)}
  .sr-q{margin:0 0 13px}
  .sr-q .sr-ql{margin:0 0 6px; font-size:14px; display:flex; gap:9px; flex-wrap:wrap; align-items:baseline}
  .sr-q .sr-ql em{font-style:normal; font-size:11px; color:var(--muted)}
  .sr-chips{display:flex; gap:6px; flex-wrap:wrap}
  .sr-chip{font-size:13px; line-height:1.2; padding:8px 12px; border-radius:4px; cursor:pointer;
    border:1px solid var(--rule); background:transparent; color:var(--ink); font-family:inherit}
  .sr-chip.on{background:var(--clear-soft); border-color:var(--clear); font-weight:600}
  .sr-chip.bad.on{background:var(--flag-soft); border-color:var(--flag)}
  .sr-chip.skip{color:var(--muted)}
  .sr-chip.skip.on{background:var(--rule-soft); border-color:var(--muted)}
  .sr-mech{display:flex; gap:8px; flex-wrap:wrap}
  .sr-my{display:flex; flex-direction:column; gap:3px; font-size:11px; color:var(--muted); width:92px}
  .sr-my.wide{width:200px}
  .sr-my input{font-size:14px; padding:7px 8px; border:1px solid var(--rule); border-radius:4px;
    background:var(--card); color:var(--ink); width:100%; font-family:inherit}
  .sr-my input.set{border-color:var(--clear); font-weight:600}
  .sr-list{margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:5px}
  .sr-row{display:grid; grid-template-columns:1fr auto; gap:6px 10px; align-items:center;
    font-size:13.5px; line-height:1.35; border-bottom:1px solid var(--rule-soft); padding-bottom:5px}
  .sr-tri{display:flex; gap:4px}
  .sr-tri button{font-size:10.5px; letter-spacing:.04em; text-transform:uppercase; padding:5px 9px;
    border:1px solid var(--rule); border-radius:4px; background:transparent; color:var(--muted);
    cursor:pointer; font-family:inherit; font-weight:600}
  .sr-tri .ok.on{background:var(--clear); border-color:var(--clear); color:#fff}
  .sr-tri .no.on{background:var(--flag); border-color:var(--flag); color:#fff}
  .sr-row .sr-tn{display:none; grid-column:1/-1; font-size:13px; padding:6px 9px; border:1px solid var(--rule);
    border-radius:4px; background:var(--card); color:var(--ink); font-family:inherit}
  .sr-row.flagged .sr-tn{display:block}
  .sr-row.done .sr-t{color:var(--muted)}
  .sr-verdicts{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:14px}
  .sr-v{font-size:11px; letter-spacing:.05em; text-transform:uppercase; padding:9px 15px; font-weight:600;
    border:1px solid var(--rule); border-radius:4px; background:transparent; color:var(--ink); cursor:pointer; font-family:inherit}
  .sr-v-shortlist.on{background:var(--clear); border-color:var(--clear); color:#fff}
  .sr-v-maybe.on{background:var(--accent); border-color:var(--accent); color:#fff}
  .sr-v-out.on{background:var(--flag); border-color:var(--flag); color:#fff}
  .sr-whorow{margin-bottom:10px}
  .sr-my.claimed span{color:var(--accent)}
  .sr-gpair{font-size:11.5px; color:var(--muted)}
  .sr-guts{display:flex; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap}
  .sr-guts .sr-gl{margin:0; font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted)}
  .sr-gbtns{display:flex; gap:5px}
  .sr-g{width:34px; height:34px; border:1px solid var(--rule); border-radius:4px; background:transparent;
    color:var(--ink); font-size:13px; cursor:pointer; font-family:inherit}
  .sr-g.on{background:var(--accent); border-color:var(--accent); color:#fff}
  .sr-notes{width:100%; font-family:inherit; font-size:13.5px; line-height:1.5; padding:9px 11px;
    border:1px solid var(--rule); border-radius:4px; background:var(--card); color:var(--ink); resize:vertical}

  /* ---------- control bar ---------- */
  .sr-ctl{position:sticky; top:0; z-index:40; display:flex; gap:10px; align-items:center; flex-wrap:wrap;
    padding:10px 14px; margin:0 -14px 0; background:var(--paper); border-bottom:1px solid var(--rule)}
  .sr-modes{display:flex; gap:5px; flex-wrap:wrap}
  .sr-mode{font-size:11px; letter-spacing:.04em; text-transform:uppercase; padding:7px 11px; font-weight:600;
    border:1px solid var(--rule); border-radius:4px; background:var(--card); color:var(--ink);
    cursor:pointer; font-family:inherit}
  .sr-mode.on{background:var(--ink); border-color:var(--ink); color:var(--paper)}
  .sr-exp{font-size:11px; letter-spacing:.04em; text-transform:uppercase; padding:7px 11px; font-weight:600;
    border:1px solid var(--accent); border-radius:4px; background:transparent; color:var(--accent);
    cursor:pointer; font-family:inherit; margin-left:auto}
  .sr-pill{font-size:11px; color:var(--muted)}
  .sr-pill.ok{color:var(--clear)} .sr-pill.warn{color:var(--flag)}
  .sr-strip{border:1px solid var(--rule); border-radius:6px; background:var(--card); padding:13px 15px; display:none}
  .sr-strip.on{display:block}
  .sr-strip h3{font-size:11px; letter-spacing:.09em; text-transform:uppercase; margin:0 0 9px;
    font-weight:600; color:var(--accent)}
  .sr-strip ol{margin:0; padding-left:20px; font-size:14px; line-height:1.7}
  .sr-strip .sv{font-size:11.5px; margin-left:8px; color:var(--muted)}
  .sr-strip .empty{margin:0; font-size:13.5px; color:var(--muted)}
  .lot.sr-hide{display:none}
  .sr-expbox{display:none; flex-direction:column; gap:8px}
  .sr-expbox.on{display:flex}
  .sr-expbox p{margin:0; font-size:13.5px; color:var(--muted)}
  .sr-expbox textarea{width:100%; height:190px; font-size:11.5px; font-family:ui-monospace,Menlo,monospace;
    border:1px solid var(--rule); border-radius:4px; background:var(--card); color:var(--ink); padding:9px}
  @media (max-width:560px){
    .sr-body{padding:11px}
    .sr-my{width:calc(50% - 4px)} .sr-my.wide{width:100%}
    .sr-ctl{margin:0 -11px; padding:9px 11px}   /* v6.1 fix 2026-09-15: the -16px pull did not match .sr-body padding (11px), so the bar sat 5px past the container and mobile.html scrolled horizontally at 360px */
    .sr-exp{margin-left:0}
  }
</style>
"""
