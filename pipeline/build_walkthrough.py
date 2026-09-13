#!/usr/bin/env python3
"""Build 'Walking the Shortlist', both builds, from the model outputs.

Reads:  observations.json, out/decision.csv, out/detail.json, rooms_legacy.json,
        live_2026-09-12.json, page_full.tpl.html, page_mobile.tpl.html
Writes: ../full.html   (desktop build)
        ../mobile.html (phone build)

The design is not in this file. It is frozen in the two templates, which are the
previously deployed pages with every model-produced region replaced by a
{{PLACEHOLDER}} (see make_page_templates.py). This file fills those placeholders,
so a regenerated page differs from the last one only where the model changed.
"""
import json, csv, os, re, html, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as S
import showing2 as SH

R = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(R, "..")
OBS = {o["slug"]: o for o in json.load(open(os.path.join(R, "observations.json")))}
DET = json.load(open(os.path.join(R, "out", "detail.json")))
ROWS = list(csv.DictReader(open(os.path.join(R, "out", "decision.csv"))))
LEGROOMS = json.load(open(os.path.join(R, "rooms_legacy.json")))
LIVE = json.load(open(os.path.join(R, "live_2026-09-12.json")))
URLT = LIVE["url_template"]
LIVE_IDS = {l[0] for l in LIVE["live"]}

def esc(s): return html.escape(str(s if s is not None else ""))
def money(n): return "${:,.0f}".format(n)
def kmoney(n): return f"${round(n/1000):,}k"
def short(slug): return slug.split("-", 2)[-1]          # bur-3205-tania -> tania
def addr_short(a): return a.split(",")[0].replace(" Crescent", " Cres").replace(" Avenue", " Ave").replace(" Drive", " Dr").replace(" Court", " Ct").replace(" Road", " Rd").replace(" Boulevard", " Blvd").replace(" Place", " Pl")

# ---------- rank v6 display constants (costs.yaml is the single source) ----------
HOLD_DEF = S.CFG["hold"]["years_default"]
HOLDS = list(S.HOLDS)
TOL = S.CFG["rank"]["dominance_tolerance_pts"]
VISIT_AT = S.CFG["rank"]["visit_if_band_top_at_or_above"]
WS = S.weight_sets()
PEOPLE = [w for w in ("alex", "partner") if w in WS]
PARTNER_IN = "partner" in PEOPLE
PROVISIONAL = S.PROVISIONAL
W_JOINT = {k: WS["joint"][k] * 100 for k in S.COMP_KEYS}
# the score panel is ordered by weight, heaviest first (USABILITY-SPEC section 6)
COMP_ORDER = sorted(S.COMP_KEYS, key=lambda k: -W_JOINT[k])
COMP_LABEL = {"space": "Space", "layout": "Layout", "baths": "Baths", "parking": "Parking",
              "lot": "Lot", "location": "Location", "condition": "Condition", "price": "Price"}
MORT_RATE = S.CFG["hold"]["mortgage_rate"] * 100
DOWN_PCT = S.CFG["hold"]["down_payment"] * 100
AMORT = S.CFG["hold"]["amortization"]
BUILD_DATE = "14 September 2026"
PAIRS = json.load(open(os.path.join(R, "out", "pairs.json"))) if os.path.exists(os.path.join(R, "out", "pairs.json")) else None

def r10(x): return int(round(float(x) / 10.0)) * 10
def money10(x): return "${:,}".format(r10(x))
def is_gated(row): return row["rank"] == "-"
def num(row, k, default=0.0):
    v = row.get(k, "-")
    try: return float(v)
    except (TypeError, ValueError): return default
def overpay(row): return None if is_gated(row) else num(row, "overpay_mo")
def comp(row): return {k: num(row, "c_" + k) for k in S.COMP_KEYS}
def score(row): return None if is_gated(row) else num(row, "score")

# v6, 14 Sep: the letter grade is no longer rendered anywhere on the page. `grade` and
# `fit_score` stay in decision.csv and detail.json for continuity with every earlier pass.
# These helpers are kept so a reader of an old record can still be shown a letter.
GR_CLASS = lambda g: "g-a" if g.startswith("A") else ("g-b" if g.startswith("B") else "g-c")
GRADE_TXT = lambda g: g.replace("-", "−")
GR_COLOUR = lambda g: "--accent" if g.startswith("A") else ("--ink" if g.startswith("B") else "--muted")

# ---------- card content ----------
NICE = {
 "kitchen_sink_mount": {"undermount": ("Undermount sink under a stone counter", False), "topmount": ("Topmount sink with a visible rim, the laminate-era tell", True)},
 "kitchen_counter_edge": {"square_eased": ("Squared counter edge, stone not laminate", False), "rolled_bullnose": ("Rolled post-form counter edge, laminate", True)},
 "kitchen_soffit": {"removed": ("Uppers run to the ceiling, no bulkhead", False), "present": ("Bulkhead retained above the uppers", True)},
 "kitchen_door_profile": {"crisp_shaker": ("Crisp shaker doors", False), "slab": ("Slab doors", False), "soft_raised_panel": ("Soft raised-panel doors, old boxes painted", True), "raised_panel_square": ("Square raised-panel doors, dated but sound", False)},
 "bath_tub_type": {"alcove_tiled": ("Alcove tub with a tiled surround", False), "freestanding": ("Freestanding tub", False), "corner_garden_platform": ("Corner tub on a tiled platform, a 1980s-90s original shell", True), "one_piece_insert": ("One-piece shower insert", False)},
 "bath_tile_scale": {"large_format": ("Large-format bath tile", False), "subway_modern": ("Modern subway tile", False), "small_4x4": ("4x4 bath tile, original era", True), "12x12_wide_grout": ("12x12 bath tile, a 2000s job", True)},
 "bath_vanity_top": {"undermount_stone": ("Undermount sink on a stone vanity top", False), "integrated_modern": ("Modern integrated vanity top", False), "vessel_on_wood": ("Vessel sink on a wood top", False), "integrated_cultured_marble": ("Cultured-marble integrated vanity top, original", True), "laminate_dropin": ("Laminate vanity top with a drop-in sink, original", True)},
 "ceiling_main": {"flat_painted": ("Flat painted ceilings", False), "stipple_popcorn": ("Stipple ceilings", True), "drop_tile": ("Drop-tile ceilings on the main level", True)},
 "window_frame": {"vinyl": ("Vinyl window frames", False), "wood_original": ("Original wood window frames", True), "aluminum_original": ("Original aluminum window frames", True)},
 "basement_ceiling": {"drywall": ("Basement ceiling is drywall", False), "drop_tile": ("Basement ceiling is drop tile", True), "exposed": ("Basement ceiling exposed", True)},
 "basement_walls": {"drywall": ("Basement walls drywalled", False), "painted_block": ("Painted block basement walls, at least in the utility room", True), "bare_block": ("Bare block basement walls", True), "panelling": ("Panelled basement walls", True)},
 "basement_moisture": {"none_visible": ("No moisture staining visible at the basement wall base", False), "efflorescence": ("Efflorescence on the basement walls", True), "staining": ("Moisture staining on the basement walls", True), "sump": ("Sump pump in the listing; no staining seen", False)},
 "driveway": {"sound": ("Driveway sound", False), "cracked": ("Driveway cracked, a repave line", True)},
 "floor_condition": {"no_defect_seen": ("No floor defect seen where floors are visible", False), "uneven_stain": ("Uneven or stained floors", True), "gaps_at_base": ("Gaps at the floor base", True)},
}

def known_lines(o):
    out = []
    for f, m in NICE.items():
        v = o.get(f)
        if v in m: out.append(m[v])
    if o.get("secondary_bath_original"): out.append(("Second full bath confirmed original", True))
    if o.get("kitchen_boxes_new") and o.get("kitchen_soffit") == "present": out.append(("Kitchen boxes are new even though the bulkhead stayed", False))
    if o.get("exterior_defect"): out.append((o["exterior_defect"][0].upper() + o["exterior_defect"][1:], True))
    if o.get("water_heater_seen"): out.append(("Water heater visible: " + o["water_heater_seen"].replace("_", " "), False))
    if o.get("furnace_seen"): out.append(("Furnace visible: " + o["furnace_seen"], False))
    if o.get("roof_visual") and "metal" in o["roof_visual"]: out.append(("Metal roof, confirmed at the eave", False))
    if o.get("staging") == "virtually_staged": out.append(("At least one frame is virtually staged", True))
    bad = [x for x in out if x[1]]; good = [x for x in out if not x[1]]
    return (bad + good)[:8]

def check_lines(o):
    items = []
    for c in (o.get("concealed_surfaces") or [])[:3]: items.append(c)
    for r in (o.get("red_flags") or [])[:4]: items.append(r)
    seen = set(); out = []
    for i in items:
        k = i[:40]
        if k in seen: continue
        seen.add(k); out.append(i[0].upper() + i[1:])
    if not any("panel" in x.lower() or "furnace" in x.lower() for x in out):
        out.append("Utility room: photograph the panel, furnace and water heater labels")
    return out[:6]

def ask_line(o):
    m = o.get("mech_ages_stated")
    q = "How old are the roof, furnace and A/C, and can you send the invoices?"
    if m and "remarks only" in str(m):
        q = "The remarks claim " + str(m).replace(" (remarks only)", "").replace("(remarks only)", "").strip() + ". Can you send the invoices, and how old are the items not mentioned?"
    extra = ""
    cve = o.get("claim_vs_evidence"); cve = [cve] if isinstance(cve, str) else (cve or [])
    if cve and isinstance(o.get("claim_vs_evidence"), list): extra = " Also: " + cve[0][0].lower() + cve[0][1:] + "; which is it?"
    if o.get("staging") == "virtually_staged": extra += " Which photos are virtually staged?"
    return q + extra

def where_line(o, d):
    yb = d["yb"]; src = d["yb_src"]
    yr = ("built " + str(yb)) if src == "mls" else (("about " + str(yb) + ", estimated") if yb else "build year not published")
    beds = str(o.get("beds_ag") or "?") + ("+" + str(o["beds_bg"]) if o.get("beds_bg") else "")
    nf, nh = o.get("baths_full") or 0, o.get("baths_half") or 0
    baths = f"{nf} full" + (f" + {nh} half" if nh else "")
    ag = o.get("sqft_above") or 0
    bg, est = S.below_grade(o)
    sq = f"{ag:,} sq ft up" + (f", {bg:,} down{' (estimated)' if est else ''}" if bg else "")
    lot = ""
    if o.get("lot_frontage_ft") and o.get("lot_depth_ft"): lot = f" · {o['lot_frontage_ft']:g} × {o['lot_depth_ft']:g} ft lot"
    g = o.get("garage_spaces") or 0
    gar = "double garage" if g >= 2 else ("garage" if g >= 1 else ("carport" if "carport" in str(o.get("remarks","")).lower() else "no garage"))
    return f"{esc(o.get('neighbourhood') or '')}, {esc(o.get('municipality') or '')} · {esc(o.get('style') or '')}, {yr} · {beds} bed, {baths} · {sq}{lot} · {gar}"

# ---------- the score panel: eight .sp rows in weight order (USABILITY-SPEC section 6) ----------
SCORE_TIP = "Score: the eight components above, each out of 100, combined with your weights. It is what this list is sorted on and it moves when the weights change."

def sp_row(label, value, weight, why=""):
    """One .sp row. The bar is the component out of 100; the right-hand figure is the component
    and the weight it carries. Same .sp element and the same amber and red thresholds as v5."""
    w = max(0.0, min(100.0, value))
    cls = "sp bad" if w < 30 else ("sp weak" if w < 50 else "sp")
    t = f' title="{esc(why)}"' if why else ""
    return (f'<div class="{cls}"{t}><em>{label}<u class="spw">{weight:.0f}%</u></em>'
            f'<span><i style="width:{w:.0f}%"></i></span>'
            f'<b>{w:.0f}<s> / 100</s></b></div>')

def weak_clause(c):
    weak = [COMP_LABEL[k].lower() for k in COMP_ORDER if c.get(k, 0) < 50][:3]
    if not weak: return "."
    if len(weak) == 1: return f": here the {weak[0]} is holding this house back."
    return ": here " + " and ".join(weak) + " are holding this house back."

def strongest_weakest(c):
    by = sorted(S.COMP_KEYS, key=lambda k: -c.get(k, 0))
    return [COMP_LABEL[k].lower() for k in by[:2]], [COMP_LABEL[k].lower() for k in by[-2:]]

def gated_line(row):
    """A gated house still needs its reason under the address. A ranked one does not need a
    summary line: the eight rows and the commentary under them say it better."""
    if not is_gated(row): return ""
    reason = row["notes"] if row["notes"] != "-" else "a rule"
    return f'<p class="where why" style="margin-top:5px">Not ranked · {esc(reason)} · still costed</p>'

def why_lines(o, d, row):
    """Why each component scores what it does, for THIS house, in its own numbers.

    Every sentence names the measurement that produced the number and the anchor it is measured
    against, so a reader can check the model rather than take it. Nothing here is a restatement of
    the bar."""
    fw = S.CFG["fit_weights"]["space"]; W = S.CFG["fact_weights"]
    c = comp(row); out = {}

    ag = o.get("sqft_above") or 0
    fin, part, sep = S.basement_flags(o)
    bg, bg_est = S.below_grade(o)
    bits = [f"{ag:,} sq ft above grade"]
    if fin: bits.append("a finished basement")
    elif part: bits.append("a partly finished basement")
    else: bits.append("no finished basement")
    if sep: bits.append("with its own entrance")
    out["space"] = (", ".join(bits) + f". The scale saturates at {fw['knee_sqft']:,} sq ft and caps at "
                    f"{fw['cap_sqft']:,}; a finished basement adds, an exterior entrance adds again.")

    beds = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
    raw = o.get("beds_ag") or 0
    pb = o.get("primary_bed_sqft") or 0
    lay = [f"{beds} bedroom{'s' if beds != 1 else ''} above grade"]
    if beds != raw: lay.append(f"{raw} on MLS, but {raw - beds} is under 60 sq ft and does not count")
    if pb: lay.append(f"primary {pb:,} sq ft" + (", over the 150 that earns the bonus" if pb >= 150 else ", under the 150 that earns the bonus"))
    if (o.get("beds_under_100sqft") or 0): lay.append(f"{o['beds_under_100sqft']} bedroom under 100 sq ft, which costs points")
    if not (o.get("rooms_raw") or LEGROOMS.get(short(o["slug"]))):
        lay.append("no room table on this listing, so the tiny-bedroom rule cannot fire")
    out["layout"] = ". ".join(x[0].upper() + x[1:] for x in lay) + ". Four bedrooms with a large primary is full marks."

    nf, nh = o.get("baths_full") or 0, o.get("baths_half") or 0
    out["baths"] = (f"{nf} full bath{'s' if nf != 1 else ''}"
                    + (f" and {nh} powder room{'s' if nh != 1 else ''}" if nh else " and no powder room")
                    + ". Three full plus a powder is full marks.")

    g, sp = o.get("garage_spaces") or 0, o.get("parking_spots") or 0
    out["parking"] = (("No garage" if not g else f"{g}-car garage")
                      + f" and {sp} parking spot{'s' if sp != 1 else ''}."
                      + " A double garage plus two spots is full marks.")

    fr, dp = o.get("lot_frontage_ft") or 0, o.get("lot_depth_ft") or 0
    area = round(fr * dp)
    out["lot"] = (f"{fr:g} by {dp:g} ft, about {area:,} sq ft."
                  f" {W['lot']['floor_sqft']:,} sq ft scores 0 and {W['lot']['ceiling_sqft']:,} scores 100.")

    wk, tr = o.get("walk") or 0, o.get("transit") or 0
    sch = o.get("nearest_school_km")
    out["location"] = (f"Walk {wk} and transit {tr}, {wk + tr} between them."
                       + (f" Nearest school {sch:g} km." if sch is not None else " No school distance on file.")
                       + " Full marks is 120 between the two scores with a school inside 500 m.")

    exp, full = num(row, "work_expected"), num(row, "work_full")
    lo, hi = num(row, "c_condition_low"), num(row, "c_condition_high")
    out["condition"] = (f"{money(round(exp))} of work expected against {money(round(full))} if every job on "
                        f"this house were needed. {'A showing has set a mechanical date, so the photo cap is lifted.' if row.get('seen_evidence') == 'yes' else 'Nobody has stood in it yet, so this cannot pass about 80 on photographs alone.'}"
                        f" On its own day-one uncertainty it runs {lo:.0f} to {hi:.0f}.")

    a = S.CFG["hold"]["price_anchor_per_year"]
    out["price"] = (f"{money(round(num(row, 'cost_hold_per_year')))} a year to hold, before any day-one work: "
                    f"financing and opportunity cost, commission out, land transfer, closing, tax and upkeep. "
                    f"{money(int(a['worst']))} a year scores 0 and {money(int(a['best']))} scores 100.")
    return out

def scorepanel(o, d, row):
    c = comp(row); g = row["grade"]; sc = score(row)
    why = why_lines(o, d, row)
    rows = "\n".join("                " + sp_row(COMP_LABEL[k], c[k], W_JOINT[k], why.get(k, ""))
                     for k in COMP_ORDER)
    dock = ""
    if row.get("split_docked") == "yes":
        pc = round(100 * (1 - S.CFG["split_dock"]))
        dock = (f'<p class="sp-foot" style="border-top:none; padding-top:4px">A split-level plan is '
                f'docked {pc}%, which is already in the score above.</p>')
    prov = (' These weights are <b>provisional</b> until the fifteen choices are answered.'
            if PROVISIONAL else "")
    return f"""<aside class="scorepanel">
            <div class="sp-top">
              <div class="sp-num">
                <span class="big" title="{esc(SCORE_TIP)}"><b>{"—" if sc is None else f"{sc:.0f}"}</b><i>/ 100</i></span>
                <em>Score · your weights, heaviest first</em>
              </div>
            </div>
            <div class="sp-parts">
{rows}
            </div>
            {dock}
          </aside>"""

# The room-driven score survives, inside the rooms disclosure only (USABILITY-SPEC section 6).
GPARTS = [("space", "Space", 25), ("layout", "Layout", 20), ("baths", "Baths", 20)]
def room_sp_row(label, pts, mx):
    w = round(100 * pts / mx)
    cls = "sp bad" if w < 30 else ("sp weak" if w < 50 else "sp")
    return (f'<div class="{cls}"><em>{label}</em><span><i style="width:{w}%"></i></span>'
            f'<b>{pts:.0f}<s> / {mx}</s></b></div>')

def rooms_html(o, d):
    k = short(o["slug"])
    rows = LEGROOMS.get(k)
    if not rows and o.get("rooms_raw"):
        rows = []
        for r in o["rooms_raw"]:
            lvl, name = r[0], r[1]; sq = r[2] if len(r) > 2 else None; ft = r[3] if len(r) > 3 else ""
            rows.append([lvl, name, None, sq, ft])
    if not rows: return ""
    fp = d["fact_parts"]
    rs = sum(fp.get(k2, 0) for k2, _, _ in GPARTS[:3])
    sp = "\n".join("              " + room_sp_row(lab, fp.get(k2, 0), mx) for k2, lab, mx in GPARTS[:3])
    h = ['<div class="roomswrap">',
         '          <div class="roomscore">',
         f'            <div><span class="rh-lab">From the room table</span><span class="rs-num"><b>{rs:.0f}</b><i>/ 65</i></span><em>The same space, layout and baths that are already in the score above, shown at their original scale, so nothing here is counted twice. The room table itself drives the layout number: a bedroom under 60 sq ft stops counting and a primary over 150 sq ft adds.</em></div>',
         '            <div class="sp-parts">', sp, '            </div>',
         '          </div>',
         '          <details class="rooms"><summary>Every room, as entered on MLS</summary>',
         '          <div class="roomtab"><table>',
         '<thead><tr><th>Level</th><th>Room</th><th>Feet</th><th style="text-align:right;padding-right:14px">Sq ft</th><th>Notes</th></tr></thead><tbody>']
    last = None
    for r in rows:
        lvl = "" if r[0] == last else r[0]; last = r[0]
        small = " small" if (r[3] and r[3] < 100 and re.search("bed", str(r[1]), re.I)) else ""
        h.append(f"<tr><td class='lvl'>{esc(lvl)}</td><td>{esc(r[1])}</td><td class='dim'>{esc(r[2] or '—')}</td>"
                 f"<td class='sq{small}'>{esc(r[3] or '—')}</td><td class='ft'>{esc(r[4] or '')}</td></tr>")
    h.append("</tbody></table></div></details></div>")
    return "\n".join(h)

BASIS_WORDS = [
    (r"^floor=no_defect_seen$", "No floor defect seen where the floors are visible"),
    (r"^floor=(.+?)( \(partly concealed\))?$", lambda m: "Floors read " + m.group(1).replace("_", " ")
        + (", and part of the floor is covered" if m.group(2) else "")),
    (r"^ceiling=flat_painted$", "Ceilings are flat and painted"),
    (r"^ceiling=(.+)$", lambda m: "Ceilings read " + m.group(1).replace("_", " ")),
    (r"^(\d)/(\d) tells seen, defect=False(.*)$", lambda m: f"{m.group(1)} of {m.group(2)} tells readable, nothing wrong found{m.group(3)}"),
    (r"^(\d)/(\d) tells seen, defect=True(.*)$", lambda m: f"{m.group(1)} of {m.group(2)} tells readable, a defect confirmed{m.group(3)}"),
    (r"^(\d)/(\d) tells seen(.*)$", lambda m: f"{m.group(1)} of {m.group(2)} tells readable{m.group(3)}"),
    (r"^unobserved$", "Never shown in the photos"),
    (r"^confirmed original$", "Confirmed original"),
    (r"^(\d+) half$", lambda m: ("One powder room" if m.group(1) == "1" else m.group(1) + " powder rooms")),
    (r"^(\d[\d,]*) sqft bg(.*)$", lambda m: f"{m.group(1)} sq ft below grade{m.group(2)}"),
    (r"^below-grade base rate$", "Base rate for a house with a basement"),
    (r"^life (\d+)y, age unstated$", lambda m: f"{m.group(1)} year life, age not published"),
    (r"^life (\d+)y, (.*)$", lambda m: f"{m.group(1)} year life, {m.group(2)}"),
    (r"^pre-1970, panel not shown$", "Built before 1970 and the panel was never photographed"),
    (r"^pre-1970 risk$", "Built before 1970, so some original wiring is likely"),
    (r"^fuse panel confirmed$", "Fuse panel confirmed in the photos"),
    (r"^fuse panel implies K&T$", "A fuse panel means knob and tube behind the walls"),
    (r"^oil heat in MLS$", "MLS lists oil heat"),
    (r"^moisture CONFIRMED$", "Moisture confirmed at the basement wall"),
    (r"^moisture suspected, low conf$", "Moisture suspected, read is not confident"),
    (r"^cracked, confirmed$", "Cracked, confirmed in the photos"),
    (r"^in-ground pool, annual carry$", "In-ground pool, what it costs to run each year"),
    (r"^metal roof in MLS/photo, long life$", "Metal roof, confirmed, so it lasts far longer"),
    (r"^suspect material, only if disturbed$", "Suspect material, charged only if it is disturbed"),
]
def pretty_basis(t):
    """The model's own shorthand made readable. 'floor=no_defect_seen' is a field name, not a
    sentence, and nothing on a card should make the reader learn the schema."""
    import re as _re
    t = str(t or "").strip()
    for pat, rep in BASIS_WORDS:
        m = _re.match(pat, t)
        if m:
            out = rep(m) if callable(rep) else rep
            return out[0].upper() + out[1:]
    t = t.replace("_", " ").replace("=", ": ")
    t = t.replace("(seen done at the showing)", "seen done at the showing")
    t = t.replace("(seen original at the showing)", "seen original at the showing")
    return (t[0].upper() + t[1:]) if t else ""

def costs_html(o, d, trow):
    def row(i):
        pct = round(i["p"] * 100)
        return (f"<tr><td class='odds'><i>{pct}%</i><u><s style='width:{pct}%'></s></u></td>"
                f"<td>{esc(nicename(i['name']))}<span class='why'>{esc(pretty_basis(i['basis']))}</span></td>"
                f"<td class='amt'>{money(i['exp'])}</td></tr>")
    d1 = "".join(row(i) for i in d["items"] if i["bucket"] == "day1")
    wl = "".join(row(i) for i in d["items"] if i["bucket"] == "wishlist")
    rs = "".join(f"<tr><td>{esc(nicename(i['name']))}<span class='why'>{i['life']} year life" + (f", charged at {round(i['p']*100)}%" if i['p'] < 1 else "") +
                 f"</span></td><td class='amt'>{money(i['exp']/max(i['p'],0.01))}</td><td class='amt'>{money(i['per_yr'])}/yr</td></tr>"
                 for i in d["items"] if i["bucket"] == "reserve")
    psf = 790 if (o.get("municipality") == "Oakville") else 720
    era = (f"built {d['yb']}" if d["yb_src"] == "mls" else f"build year estimated at {d['yb']} ({d['yb_src']})") if d["yb"] else "build year not published, treated as pre-1990"
    bgnote = " Below-grade area is an estimate (70% of the footprint) because MLS gave none; the peer benchmark moves with it." if d.get("bg_est") else ""
    big = " On a house this large a flat rate reads higher than anything in the pocket actually trades at, so treat that headroom as an upper bound." if d["headroom"] > 0.35 * d["list"] else ""
    return f"""<details class="costs"><summary>Renovation cost, line by line</summary><div class="costbody">
<div class="costgrid">
<section class="cb d1"><h4>Day one <b>{money(d['day1_p80'])}</b></h4><table><tbody>{d1}</tbody></table>
<p class="foot">Midpoint outcome {money(d['day1_p50'])}. The planning figure is the 80th percentile of 4,000 simulated outcomes taken on the <b>total</b>, not by adding up each line's high end, which would read {money(d['naive'])} once day one and the wish list are combined. A {d['contingency_pct']}% discovery contingency and HST are already inside every line.</p></section>
<section class="cb wl"><h4>Wish list <b>{money(d['wish_p80'])}</b></h4><table><tbody>{wl}</tbody></table>
<p class="foot">Midpoint {money(d['wish_p50'])}. None of this is required to move in and none of it is in the ranking. It is what the house would cost to bring fully current, on your timing.</p></section>
<section class="cb rs"><h4>Upkeep <b>{money(d['reserve_monthly']*12)} a year</b></h4><table><tbody>{rs}</tbody></table>
<p class="foot">Replacement cost and expected life, annualised. This is the upkeep line inside Monthly payment. {money(d['near_term_5yr'])} of this sits in components already past their rated life if the house is as old as it looks. Every date you get from the agent shrinks it.</p></section>
</div>
<div class="valuebox"><dl class="valuerow">
<div class="neg"><dt>Never comes back</dt><dd>{money(d['sunk'])}</dd></div><div><dt>Day one + wish list</dt><dd>{money(d['day1_p80']+d['wish_p80'])}</dd></div>
<div><dt>Usable area</dt><dd>{d['usable']:,} sq ft</dd></div><div><dt>Taxes</dt><dd>{money(d['taxes'] or 0)} a year</dd></div>
</dl><p class="valuenote">Spend the full {money(d['day1_p80']+d['wish_p80'])} and <b>{money(d['sunk'])} of it does not come back</b> on resale, using the AIC recovery band on each line. That sunk figure is the only resale number on this card. The peer benchmark, the after-renovation value, recovered % and break-even are all derived from asking prices rather than solds, which produces figures nobody believes at both ends of the batch, so they are held back until sold prices per square foot are available; they are still in <code>detail.json</code> and in <code>decision.csv</code>. {era[0].upper()+era[1:]}, so an unseen job is priced at {round(d['era_p']*100)}% likely.{bgnote}</p></div>
</div></details>"""

# ---------- renovations: the list, no needs-work bar (USABILITY-SPEC section 6) ----------
def nicename(n):
    return " ".join(w[:1].upper() + w[1:] for w in str(n).split(" "))

def reno_html(o, d, row):
    items = d.get("reno") or []
    needed = [i for i in items if i["status"] != "possible"]
    maybe = [i for i in items if i["status"] == "possible"]
    exp, full = num(row, "work_expected"), num(row, "work_full")
    head = (f'<div class="renofigs">'
            f'<div><span class="rf-lab">Expected work</span><b class="rf-val">{money(round(exp))}</b>'
            f'<span class="rf-note">every line at the odds the model gives it, over {HOLD_DEF} years</span></div>'
            f'<div><span class="rf-lab">If everything were done</span><b class="rf-val">{money(round(full))}</b>'
            f'<span class="rf-note">every line at a probability of one</span></div>'
            f'<div><span class="rf-lab">Day one, of that</span><b class="rf-val">{money(d["day1_p80"])}</b>'
            f'<span class="rf-note">before or at move-in, p80</span></div>'
            f'<div><span class="rf-lab">Wish list</span><b class="rf-val">{money(d["wish_p80"])}</b>'
            f'<span class="rf-note">your choice, your timing</span></div>'
            f'</div>')
    li = "".join(f'<li class="{"conf" if i["status"]=="confirmed" else "unseen" if i["status"]=="likely, unseen" else ""}" title="{i["status"]}, {round(i["p"]*100)}% likely, {i["bucket"]}">'
                 f'<span>{esc(nicename(i["name"]))}</span><span class="amt">{kmoney(i["cost"])}</span></li>' for i in needed)
    mb = ""
    if maybe:
        mb = '<p class="maybe"><i>Possible</i>' + ", ".join(f"{esc(nicename(i['name']))} {kmoney(i['cost'])} ({round(i['p']*100)}%)" for i in maybe) + "</p>"
    if any(i["status"] == "likely, unseen" for i in needed):
        mb += '<p class="maybe"><i>?</i>never shown in the photos, so priced at the base rate for a house this age. Roof, furnace, A/C, water heater and windows are charged at the chance they come due inside the hold, and they are inside Expected work.</p>'
    inner = costs_html(o, d, row)
    return (f'<section class="reno"><h3>Renovations</h3>{head}<ul>{li}</ul>{mb}{inner}</section>')

# ---------- status, days on market, what changed ----------
def status_of(o):
    return (o.get("status") or ("active" if o["listing_id"] in LIVE_IDS else "delisted"))

def dom_days(o):
    try: return int(o.get("dom") or 0)
    except (TypeError, ValueError): return 0

# ---------- the card ----------
HOLD_WORD = {"POOL": "pool", "OIL": "oil tank", "TENANTED": "tenanted"}

def band_txt(row):
    return "—" if is_gated(row) else f'{row["band_lo"]}–{row["band_hi"]}'

def worth_a_look(row):
    """The band reaches the top of the list even though the point rank does not."""
    if is_gated(row): return False
    return int(row["band_lo"]) <= VISIT_AT < int(row["rank"])

def under_address(row, o, n_ranked):
    """One line: rank of N, strongest two, weakest two, both gut scores when present."""
    if is_gated(row):
        return f'Not ranked · {esc(row["verdict"])} · {esc(row["notes"] if row["notes"] != "-" else "gated")} · still costed'
    st, wk = strongest_weakest(comp(row))
    return (f'Rank {row["rank"]} of {n_ranked} · strongest {st[0]}, {st[1]} · weakest {wk[0]}, {wk[1]}'
            f'<span class="gutline" data-gut="{esc(short(o["slug"]))}"></span>')

def pay_cell(o, big=False):
    """Every monthly payment on the page is written here by monthlyPayment() in the page script.
    Nothing else on the page carries '/mo'."""
    k = short(o["slug"])
    cls = "payhero" if big else "pay"
    return f'<b class="{cls}" data-pay="{k}">—</b>'

def card_data(o, row, d):
    """Everything the page script needs to compute this house's monthly payment and to filter."""
    return (f' data-ask="{o["list_price"]}" data-day1="{d["day1_p80"]}"'
            f' data-tax="{(o.get("annual_taxes") or 0)/12:.4f}" data-upkeep="{d["reserve_monthly"]}"'
            f' data-muni="{esc(o.get("municipality") or "")}" data-dom="{dom_days(o)}"'
            f' data-status="{esc(status_of(o))}" data-cond="{num(row, "c_condition"):.0f}"'
            f' data-score="{"" if is_gated(row) else row["score"]}"'
            f' data-bandlo="{"" if is_gated(row) else row["band_lo"]}"'
            f' data-rank="{99 if is_gated(row) else int(row["rank"])}"'
            + (' data-gated="1"' if is_gated(row) else ""))

def stamps_for(row, o, d, url):
    ev = row["evidence"]
    photos = int(row["photos_total"] or 0); tells = int(row["tells_seen_of_15"])
    st = [f'<span class="stamp seen">Photos reviewed · {photos} · {tells}/15 tells settled</span>',
          f'<span class="stamp {"seen" if ev=="high" else "unseen"}" title="{esc(row["evidence_notes"])}">Evidence {ev}</span>']
    v = row["verdict"]
    if v == "STOP": st.append('<span class="stamp unseen">STOP</span>')
    elif v == "SEE FIRST" and not row.get("hold_flags", "-") not in ("-", ""): st.append('<span class="stamp seen">See first</span>')
    elif v == "SEE FIRST": st.append('<span class="stamp seen">See first</span>')
    if PROVISIONAL:
        st.append('<span class="stamp unseen" title="fifteen pairwise choices not yet answered">Weights provisional</span>')
    if not PARTNER_IN:
        st.append('<span class="stamp unseen">Partner weights pending</span>')
    if row.get("project") == "yes":
        share = S.CFG["gates"].get("project_share_of_ask", 0.15)
        st.append(f'<span class="stamp unseen" title="expected work is more than {share:.0%} of the ask">Project</span>')
    if row.get("disagree") == "yes":
        st.append('<span class="stamp unseen" title="your rank and your partner\'s differ by more than five">Disagree</span>')
    st.append(f'<span class="stamp unseen gutdis" data-gutdis="{esc(short(o["slug"]))}" hidden>Disagree · gut</span>')
    if worth_a_look(row):
        st.append(f'<span class="stamp seen" title="its band reaches rank {row["band_lo"]}">Worth a look</span>')
    if not (o.get("rooms_raw") or LEGROOMS.get(short(o["slug"]))):
        st.append('<span class="stamp unseen" title="the layout component cannot lose a bedroom to the tiny-room rule on this listing">No room table</span>')
    if d.get("bg_est"): st.append('<span class="stamp unseen">Basement area estimated</span>')
    if d["yb_src"] != "mls": st.append('<span class="stamp unseen">Build year estimated</span>')
    if dom_days(o) >= 60: st.append(f'<span class="stamp unseen">{dom_days(o)}+ days</span>')
    if status_of(o) == "back": st.append('<span class="stamp unseen">Back on market</span>')
    if status_of(o) in ("sold", "delisted"):
        st.append(f'<span class="stamp unseen">{status_of(o).title()}</span>')
    if is_gated(row):
        st.append(f'<span class="stamp unseen">Gated · {esc(row["notes"] if row["notes"] != "-" else "a rule")}</span>')
    for nn in (d.get("verdict_notes") or []):
        if nn.startswith(("POOL", "TENANTED", "OIL")):
            st.append(f'<span class="stamp unseen">HOLD · {HOLD_WORD[nn.split(" ")[0]]}</span>')
        elif "virtually" in nn:
            st.append(f'<span class="stamp unseen">{esc(nn.split(" — ")[0])}</span>')
    st.append(f'<button type="button" class="stamp sat" data-sat="{esc(short(o["slug"]))}">Add to View List</button>')
    st.append(f'<button type="button" class="stamp cmp" data-cmp="{esc(short(o["slug"]))}">Compare</button>')
    # the label is repainted by the page script so it reads "Comparing, remove" once it is on
    st.append(f'<a class="stamp link" href="{esc(url)}" target="_blank" rel="noopener">Open listing ↗</a>')
    return st

def before_you_offer(row, o, d):
    """USABILITY-SPEC section 4.3. The only place a price argument lives. Overpay survives here,
    in words, and nothing on this list is an offer price."""
    lines = []
    b = BYSLUG.get(row.get("dominated_by", "-")) if not is_gated(row) else None
    if b is not None and overpay(row):
        lines.append(f'Cheapest house scoring within {TOL} points: <b>{esc(b["address"].split(",")[0].title())}</b>, '
                     f'{money(int(b["ask"]))}, monthly payment <span class="paydiff" data-a="{esc(short(o["slug"]))}" '
                     f'data-b="{esc(SLUG_SHORT[b["address"]])}">—</span> less.')
    else:
        lines.append(f'Nothing that scores within {TOL} points of this house costs less to own.')
    if not is_gated(row):
        lines.append(f'<span class="offerscore" data-k="{esc(short(o["slug"]))}">At {money(o["list_price"]-50000)} '
                     f'and {money(o["list_price"]-100000)} the score and rank move as shown on rebuild.</span>')
    lines.append(f'Cash on closing day at your settings: <span class="cashline" data-k="{esc(short(o["slug"]))}">—</span>.')
    return ('<div class="byo"><h4>Before you offer</h4><ul>'
            + "".join(f"<li>{t}</li>" for t in lines)
            + '</ul><p class="maybe"><i>!</i>None of these is an offer price. They are arithmetic on the '
              'asking price and on your own settings.</p></div>')

def details_wrap(summary, inner, open_when_showing=False):
    """Every section below the money block is collapsed by default (USABILITY-SPEC 4.1)."""
    cls = ' class="v6sec showopen"' if open_when_showing else ' class="v6sec"'
    return f'<details{cls}><summary>{esc(summary)}</summary>{inner}</details>'

def card(rank, row, o, d, n_ranked):
    slug = o["slug"]; k = short(slug)
    url = URLT.replace("{ID}", o["listing_id"])
    gated = is_gated(row)
    known = known_lines(o)
    def kl(t, b):
        return (f'<li class="hasbad"><span class="bad">{esc(t)}</span></li>' if b else f"<li>{esc(t)}</li>")
    known_html = "".join(kl(t, b) for t, b in known) or "<li>Nothing settled: no readable tells in the photo set</li>"
    checks = check_lines(o)
    check_html = "".join(f'<li>{esc(t)}</li>' for t in checks)
    take = esc(o.get("notes") or "")
    d1_txt = " Re-read on 12 September; the earlier pass had most tells unresolved." if o.get("stage2_pass") == "re-read" else ""
    grey = ' data-grey="1"' if status_of(o) in ("sold", "delisted") else ""
    CHECK_TITLE = "Check when you" + chr(39) + "re there"
    # Always on the card: renovations (with the line-by-line detail folded inside it), then what
    # the photos settled and what to check, side by side, then the room-driven score. The showing
    # record is the last thing on the card and the only section that starts closed.
    why = why_lines(o, d, row)
    cmp_ = comp(row)
    sec_why = details_wrap("Why each score", '<dl class="whylist">' + "".join(
        f'<div><dt>{COMP_LABEL[kk]}<b>{cmp_[kk]:.0f} / 100</b>'
        f'<u>{W_JOINT[kk]:.0f}% of the score</u></dt><dd>{esc(why.get(kk, ""))}</dd></div>'
        for kk in COMP_ORDER) + "</dl>")
    sec_reno  = reno_html(o, d, row)
    sec_split = ('<div class="split">'
                 '<section class="known"><h3>Settled by the photos</h3><ul>' + known_html + "</ul></section>"
                 '<section class="check"><h3>' + CHECK_TITLE + "</h3><ul>" + check_html + "</ul></section>"
                 "</div>"
                 '<p class="ask"><span>Ask before you go</span>' + esc(ask_line(o)) + "</p>")
    sec_rec   = details_wrap("Showing record", SH.record_html(k, o, d, checks) + before_you_offer(row, o, d),
                             open_when_showing=True)
    sec_costs = ""
    return f"""
    <article class="lot" id="sr-lot-{k}" data-slug="{k}"{card_data(o, row, d)}{grey}>
      <div class="rail"><div class="rank">{"—" if gated else rank}</div>
        <div class="psf" title="{esc(SCORE_TIP)}"><b>{"—" if gated else f'{num(row,"score"):.0f}'}</b><span>Score</span></div>
        <div class="psf">{pay_cell(o, big=True)}<span>Monthly payment</span></div>
        <div class="psf"><b>{band_txt(row)}</b><span>Band</span></div></div>
      <div class="body">
        <div class="stickymini" aria-hidden="true"><b>{"—" if gated else rank}</b>
          <b>{"—" if gated else f'{num(row,"score"):.0f}'}</b>
          <span>{esc(S.short_street(o["address"]))}</span></div>
        <div class="lot-head">
          <div class="lh-text">
          <h2><a href="{esc(url)}" target="_blank" rel="noopener">{esc(o['address'].split(',')[0].title().replace("Mls","MLS"))}</a></h2>
          <p class="where">{where_line(o, d)}</p>
          {gated_line(row)}
          <div class="tags">{''.join(stamps_for(row, o, d, url))}</div>
          <dl class="money">
          <div class="hero"><dt>Monthly payment</dt><dd>{pay_cell(o)}</dd>
            <dd class="paysub" data-paysub="{k}"></dd></div>
          <div><dt>Day-one work</dt><dd>{money(d['day1_p80'])}</dd></div>
          <div><dt>Wish list</dt><dd>{money(d['wish_p80'])}</dd></div>
          <div><dt>{HOLD_DEF}-year cost</dt><dd>{money(num(row, "cost_hold"))}</dd></div>
          <div><dt>Cash on closing day</dt><dd><span class="cashline" data-k="{k}">—</span></dd></div>
          </dl>
          </div>
          {scorepanel(o, d, row)}
        </div>
        <dl class="live-row" data-live="{k}" data-ask="{o['list_price']}"
            data-peryear="{round(num(row, 'cost_hold_per_year'))}"
            data-pricescore="{num(row, 'c_price'):.0f}"
            data-anchorbest="{int(S.CFG['hold']['price_anchor_per_year']['best'])}"
            data-anchorworst="{int(S.CFG['hold']['price_anchor_per_year']['worst'])}"></dl>
        {sec_why}
        <p class="take">{take}{d1_txt}</p>
        {sec_reno}
        {sec_split}
        {sec_rec}{sec_costs}
      </div>
    </article>"""

# ---------- assemble ----------
n = len(ROWS)
RANKED = [r for r in ROWS if not is_gated(r)]
N_RANKED = len(RANKED)
see_first = [r for r in ROWS if r["verdict"] == "SEE FIRST"]
SLUG_OF = {r["address"]: next(sl for sl, o in OBS.items() if o["address"] == r["address"]) for r in ROWS}
SLUG_SHORT = {a: short(s) for a, s in SLUG_OF.items()}
BYSLUG = {SLUG_OF[r["address"]]: r for r in ROWS}

cards = []; houses_js = []; reserve_js = {}; show_js = {}; compare_js = {}
for r in ROWS:
    slug = SLUG_OF[r["address"]]; o = OBS[slug]; d = DET[slug]
    cards.append(card(r["rank"], r, o, d, N_RANKED))
    houses_js.append({"k": short(slug), "n": addr_short(o["address"]), "p": o["list_price"],
                      "d": d["day1_p80"], "t": round(o.get("annual_taxes") or 0)})
    reserve_js[short(slug)] = d["reserve_monthly"]
    show_js[short(slug)] = {"slug": slug, "name": addr_short(o["address"].title()),
                            "psf": 0 if is_gated(r) else round(num(r, "score")),
                            "rank": 99 if is_gated(r) else int(r["rank"]),
                            "verdict": r["verdict"]}
    compare_js[short(slug)] = {
        "name": o["address"].split(",")[0].title(), "ask": o["list_price"],
        "score": "—" if is_gated(r) else round(num(r, "score"), 1),
        "comp": {k2: round(num(r, "c_" + k2)) for k2 in S.COMP_KEYS},
        "day1": d["day1_p80"], "wish": d["wish_p80"], "hold": round(num(r, "cost_hold")),
        "band": band_txt(r), "dom": dom_days(o), "status": status_of(o),
        "flags": [x for x in [("HOLD · " + ", ".join(HOLD_WORD.get(h.split(" ")[0], h.split(" ")[0]) for h in (r["hold_flags"].split("; ") if r["hold_flags"] != "-" else []))) if r["hold_flags"] != "-" else None,
                              "Project" if r.get("project") == "yes" else None] if x],
        "qs": ask_line(OBS[slug])[:110] + ("..." if len(ask_line(OBS[slug])) > 110 else ""),
    }

# ---------- what changed since the last build ----------
CHANGED = {}
def changes_line():
    prev = os.path.join(R, "out", "batch_prev.json")
    now = {short(SLUG_OF[r["address"]]): {"rank": r["rank"], "score": r["score"], "ask": r["ask"],
                                          "status": status_of(OBS[SLUG_OF[r["address"]]])} for r in ROWS}
    stamp = os.path.join(R, "out", f"batch_{BUILD_DATE.replace(' ', '-')}.json")
    old = json.load(open(prev)) if os.path.exists(prev) else None
    json.dump(now, open(os.path.join(R, "out", "batch_2026-09-14.json"), "w"), indent=1)
    json.dump(now, open(prev, "w"), indent=1)
    if not old:
        return ('<p class="changes" id="changes">First build under v6 · nothing to compare against yet · '
                'the next build will list what is new, gone, dropped in price and back on market.</p>')
    new = [k for k in now if k not in old]
    gone = [k for k in old if k not in now]
    drop = [k for k in now if k in old and float(now[k]["ask"]) < float(old[k]["ask"])]
    back = [k for k in now if now[k]["status"] == "back"]
    CHANGED.update({"new": new, "gone": gone, "drop": drop, "back": back})
    parts = [(len(new), "new", "new"), (len(gone), "gone", "gone"),
             (len(drop), "price drop", "drop"), (len(back), "back on market", "back")]
    inner = " · ".join(f'<button type="button" class="chg" data-chg="{c}">{v} {lab}</button>'
                       for v, lab, c in parts)
    return f'<p class="changes" id="changes">Since the last build: {inner}</p>'

# ---------- table ----------
tip_s = esc(SCORE_TIP)
THEAD = (f'<th class="n">#</th><th>House</th><th class="scoreth" title="{tip_s}">Score</th>'
         '<th class="n">Monthly payment</th><th class="n">Day-one</th><th class="n">Condition</th>'
         '<th class="n">Band</th><th class="n">DOM</th><th>Status</th><th>Verdict</th><th class="flag-col">Flags</th>')

def scorecol(row):
    """The composite, as a bar. Not a second letter scale."""
    if is_gated(row):
        return '<span class="scorecol"><b class="v">—</b><span class="bar"></span></span>'
    s = num(row, "score")
    bar = "--accent" if round(s) >= 55 else "--warn"
    return (f'<span class="scorecol"><b class="v">{s:.0f}</b>'
            f'<span class="bar"><i style="width:{s:.0f}%; background:var({bar})"></i></span></span>')

def flags_cell(r):
    out = []
    if r["hold_flags"] != "-": out.append("HOLD · " + r["hold_flags"])
    if r.get("project") == "yes": out.append("Project")
    if r.get("disagree") == "yes": out.append("Disagree")
    if is_gated(r): out.append("Gated")
    return esc(" · ".join(out))

def table_rows():
    out = []
    for r in ROWS:
        slug = SLUG_OF[r["address"]]; o = OBS[slug]; d = DET[slug]
        cls = ' class="stop"' if r["verdict"] == "STOP" else ""
        cell = "—" if is_gated(r) else r["rank"]
        btip = "" if is_gated(r) else f' title="rank {r["rank_3"]} at a 3-year hold, {r["rank_10"]} at 10"'
        out.append(f"<tr{cls}{card_data(o, r, d)} data-slug='{short(slug)}'><td class='n'>{cell}</td>"
                   f"<td><a class='tl' href='#sr-lot-{short(slug)}'>{esc(r['address'].split(',')[0].title())}</a></td>"
                   f"<td>{scorecol(r)}</td>"
                   f"<td class='n'>{pay_cell(o)}</td>"
                   f"<td class='n'>{money(int(r['day1_p80']))}</td>"
                   f"<td class='n'>{num(r,'c_condition'):.0f}</td>"
                   f"<td class='n'{btip}>{band_txt(r)}</td>"
                   f"<td class='n'>{dom_days(o)}</td>"
                   f"<td class='vd'>{esc(status_of(o))}</td>"
                   f"<td class='vd'>{esc(r['verdict'])}</td><td>{flags_cell(r)}</td></tr>")
    return "".join(out)

def minitable():
    out = []
    for r in ROWS:
        slug = SLUG_OF[r["address"]]; o = OBS[slug]; d = DET[slug]
        sc = None if is_gated(r) else num(r, "score")
        bar = "--accent" if (sc or 0) >= 55 else "--warn"
        cell = "—" if is_gated(r) else r["rank"]
        stop = ' class="stop"' if r["verdict"] == "STOP" else ''
        fig = (f'Not ranked · {esc(r["notes"] if r["notes"] != "-" else "a rule")}' if is_gated(r)
               else f'Band {band_txt(r)} · Condition {num(r,"c_condition"):.0f} · Day one {money(int(r["day1_p80"]))}')
        out.append(f'<li{stop}><a href="#sr-lot-{short(slug)}"><span class="mr-rank">{cell}</span>'
                   f'<span class="mr-name">{esc(r["address"].split(",")[0].title())}</span>'
                   f'<span class="mr-score"><b>{"—" if sc is None else f"{sc:.0f}"}</b>'
                   f'<span class="bar"><i style="width:{(sc or 0):.0f}%; background:var({bar})"></i></span>'
                   f'<em>{esc(r["verdict"])}</em></span>'
                   f'<span class="mr-figs">Monthly payment {pay_cell(o)} · {fig}</span></a></li>')
    return "\n        " + "\n        ".join(out)

def jumpopts(variant):
    if variant == "full":
        return '<option value="">Pick a house</option>'
    o = ['<option value="">Jump to a house…</option>']
    for r in ROWS:
        slug = SLUG_OF[r["address"]]
        o.append(f'<option value="sr-lot-{short(slug)}">{r["rank"]}. {esc(r["address"].split(",")[0].title())}</option>')
    return "".join(o)

# ---------- control bar: global settings, filters, sort ----------
FILTERS = f"""
    <label class="sr-jump"><span>Down</span><input type="number" id="g-dp" value="{DOWN_PCT:.0f}" min="5" max="100" step="1" style="width:52px"></label>
    <label class="sr-jump"><span>Rate</span><input type="number" id="g-rate" value="{MORT_RATE:.2f}" min="0.5" max="12" step="0.05" style="width:62px"></label>
    <label class="sr-jump"><span>Amort</span><input type="number" id="g-amort" value="{AMORT}" min="5" max="30" step="1" style="width:52px"></label>
    <label class="sr-jump"><span>Where</span><select id="g-muni"><option value="">All</option><option>Burlington</option><option>Oakville</option></select></label>
    <label class="sr-jump"><span>Max ask</span><input type="number" id="g-maxask" placeholder="any" step="25000" style="width:86px"></label>
    <label class="sr-jump"><span>Sort</span><select id="g-sort">
      <option value="score">Score</option><option value="pay">Monthly payment</option>
      <option value="cond">Condition</option><option value="band">Band top</option>
      <option value="dom">Days on market</option></select></label>
    <label class="sr-jump"><span>Picks</span><select id="g-picks"><option value="">All</option>
      <option value="mine">My picks</option><option value="partner">Partner's picks</option>
      <option value="both">Both</option><option value="either">Either</option></select></label>
"""

HOLD_BTNS = ("\n    <div class=\"sr-modes\" id=\"holdmodes\" style=\"margin-left:auto\">"
             + "".join(f'<button type="button" class="sr-mode{" on" if H == HOLD_DEF else ""}"'
                       f' data-kind="hold" data-v="{H}">{H} yr</button>' for H in HOLDS)
             + "</div>")

# ---------- Saturday plan ----------
SATURDAY = """
  <div class="satbox" id="satbox" hidden>
    <div class="section-head" style="padding-top:8px"><h2 style="font-size:19px">Saturday</h2>
      <p id="sat-count"></p></div>
    <ol class="satlist" id="sat-list"></ol>
    <p><button type="button" class="sr-exp" id="sat-map">Route in Google Maps</button>
       <button type="button" class="sr-exp" id="sat-print">Print sheet</button>
       <button type="button" class="sr-exp" id="sat-clear">Clear</button></p>
  </div>"""

# ---------- compare ----------
COMPARE = """
  <div class="cmpbox" id="cmpbox" hidden>
    <div class="section-head" style="padding-top:8px"><h2 style="font-size:19px">Compare</h2>
      <p>Up to four side by side. This is the sheet to print for the agent.
        Remove one with the cross above its column, or clear the lot.</p></div>
    <p><button type="button" class="sr-exp" id="cmp-clear">Clear all</button></p>
    <div class="cmpscroll"><table class="big" id="cmptab"></table></div>
  </div>
  <button type="button" class="cmpfab" id="cmpfab" hidden></button>"""

# ---------- the fifteen pairs ----------
def pairs_section():
    if not PAIRS:
        return ""
    def side(p, which):
        h = p[which]
        bars = "".join(sp_row(COMP_LABEL[k], h["comp"][k], W_JOINT[k]) for k in COMP_ORDER)
        return (f'<button type="button" class="pairpick" data-pair="{p["id"]}" data-pick="{which}">'
                f'<span class="pp-head"><b>{esc(h["street"])}</b>'
                f'<em>{money(h["ask"])}</em></span>'
                f'<span class="sp-parts">{bars}</span>'
                f'<span class="pp-line">{esc(h["line"])}</span></button>')
    cards_html = "".join(
        f'<div class="pairrow" data-pair="{p["id"]}" hidden>'
        f'<p class="pp-q"><span class="pp-n"></span>Which of these two would you rather buy?</p>'
        f'<div class="pp-two">{side(p, "A")}{side(p, "B")}</div></div>'
        for p in PAIRS["pairs"])
    return f"""
  <details class="pairbox" id="pairbox" open>
    <summary>Set my weights (3 minutes)</summary>
    <div class="pairbody">
      <p>Fifteen choices between two real houses from this batch. There are no numbers to give.
        The weights behind every score on this page are fitted from what you pick, so until both of
        you have answered, the page says the weights are provisional.
        <label class="sr-jump" style="margin-left:8px"><span>Answering</span>
          <select id="pp-who"><option value="alex">Me</option><option value="partner">My partner</option></select></label></p>
      <div id="pp-cards">{cards_html}</div>
      <p id="pp-done" hidden><b>All fifteen answered.</b>
        <button type="button" class="sr-exp" id="pp-export">Done, export</button>
        <button type="button" class="sr-exp" id="pp-reset">Start again</button></p>
      <textarea id="pp-text" readonly hidden></textarea>
    </div>
  </details>"""

# ---------- calibration ----------
CALIBRATION = """
  <div class="calbox" id="calbox" hidden>
    <div class="section-head"><h2>Where your gut and the model disagree</h2>
      <p>One dot per house per person: the gut score you gave it against the score the model gives it.
        It appears once five gut scores exist, and it is the mechanism that replaces redesigns with
        weight edits.</p></div>
    <div id="cal-body"></div>
  </div>"""

GLOSSARY = f"""
    <div class="term"><dt>Score</dt>
      <dd>The one number this page is sorted on: eight components, each 0 to 100 on an absolute scale, combined with <b>your weights</b>. Higher is better. <b>It is not the letter.</b> Change a weight and every score moves.</dd></div>
    <div class="term"><dt>Condition</dt>
      <dd>The share of this house's work that is <b>not</b> expected, cost-weighted, 0 to 100. The dollars behind it are under Renovations. Photographs alone cannot push it past about 77; the rest needs somebody standing in the house.</dd></div>
    <div class="term"><dt>Monthly payment</dt>
      <dd>Mortgage principal and interest at the settings in the control bar, plus property tax, plus upkeep. <b>The only number on this page with "/mo" after it</b>, and every place it appears it is the same figure.</dd></div>
    <div class="term"><dt>Day-one work</dt>
      <dd>The 80th percentile of what must be done <b>before or at move-in</b>: safety, insurability, and work that costs twice as much once the furniture is in.</dd></div>
    <div class="term"><dt>Wish list</dt>
      <dd>Kitchen, baths, basement, deck. <b>Your choice, your timing.</b> It is priced but it never gates a purchase.</dd></div>
    <div class="term"><dt>{HOLD_DEF}-year cost</dt>
      <dd>What owning for the hold costs <b>beyond getting the price back</b>: financing and opportunity cost, commission out, land transfer tax, closing, unrecovered day-one work, tax and upkeep. A total, never a monthly figure, because it is not a payment.</dd></div>
    <div class="term"><dt>Cash on closing day</dt>
      <dd>Down payment, land transfer tax net of the first-time-buyer rebate, closing extras and day-one work. <b>What has to be in the account.</b></dd></div>
    <div class="term"><dt>Band</dt>
      <dd>Where this house lands across every weight set on file, every hold of 3, 5 and 10 years, and the low and high end of its own day-one uncertainty. <b>A wide band means the rank is resting on assumptions.</b></dd></div>
    <div class="term"><dt>Project</dt>
      <dd>Expected work is more than {S.CFG["gates"].get("project_share_of_ask", 0.15):.0%} of the asking price. <b>Ranked, not excluded</b>, because you said you would take one on at the right price.</dd></div>
    <div class="term"><dt>HOLD</dt>
      <dd>An oil tank, an in-ground pool or a sitting tenant. <b>Ranked and flagged, never silently dropped</b>, and never marked "See first".</dd></div>
    <div class="term"><dt>Weights</dt>
      <dd>What each of the eight components is worth to you, out of 100. They come from <b>fifteen forced choices between real houses</b>, one set per person. Until both sets exist the page says provisional and the joint column is whoever has answered.</dd></div>
  """

# ---------- the page script ----------
V6JS = r"""
<script>
/* v6 page script. One monthlyPayment(), one settings object, and everything that shows a payment
   reads it: the rail, the money block, the table and the calculator. Nothing else carries "/mo". */
(function(){
  var CFG = __CFG__;
  var KEY = "walk-v6-settings", PKEY = "walk-v6-picks", SKEY = "walk-v6-saturday",
      CKEY = "walk-v6-compare", QKEY = "walk-v6-choices";
  function load(k, d){ try{ return JSON.parse(localStorage.getItem(k)) || d; }catch(e){ return d; } }
  function save(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
  var S = load(KEY, {dp: CFG.dp, rate: CFG.rate, amort: CFG.amort, hold: CFG.hold});
  var money = function(n){ return "$" + Math.round(n).toLocaleString("en-CA"); };

  /* the one payment function: Canadian semi-annual compounding, same as the calculator's */
  function pAndI(principal, annualPct, years){
    if(principal <= 0) return 0;
    var i = Math.pow(1 + (annualPct/100)/2, 1/6) - 1, n = years*12;
    return i === 0 ? principal/n : principal * i / (1 - Math.pow(1+i, -n));
  }
  function cmhcRate(dp){ return dp >= 20 ? 0 : dp >= 15 ? .028 : dp >= 10 ? .031 : .04; }
  function parts(el){
    var ask = +el.dataset.ask, dp = S.dp/100;
    var loan = ask * (1 - dp); loan += loan * cmhcRate(S.dp);
    return {pi: pAndI(loan, S.rate, S.amort), tax: +el.dataset.tax, up: +el.dataset.upkeep, loan: loan, ask: ask};
  }
  function monthlyPayment(el){ var p = parts(el); return p.pi + p.tax + p.up; }
  function ltt(p){
    var b = [[55000,.005],[250000,.01],[400000,.015],[2000000,.02],[Infinity,.025]], t=0, prev=0;
    for(var i=0;i<b.length;i++){ if(p<=prev) break; t += (Math.min(p,b[i][0])-prev)*b[i][1]; prev=b[i][0]; }
    return t;
  }
  function cashToClose(el){
    var ask = +el.dataset.ask, d1 = +el.dataset.day1;
    return ask*(S.dp/100) + Math.max(0, ltt(ask) - 4000) + CFG.closing + d1;
  }

  var SRC = {};                                   /* slug -> a node carrying the data attributes */
  function index(){
    document.querySelectorAll("[data-slug][data-ask]").forEach(function(el){
      if(!SRC[el.dataset.slug]) SRC[el.dataset.slug] = el;
    });
  }
  function paintPayments(){
    index();
    document.querySelectorAll("[data-pay]").forEach(function(b){
      var src = SRC[b.dataset.pay]; if(!src) return;
      b.textContent = money(monthlyPayment(src)) + " /mo";
    });
    document.querySelectorAll("[data-paysub]").forEach(function(s){
      var src = SRC[s.dataset.paysub]; if(!src) return;
      var p = parts(src);
      s.textContent = money(p.pi) + " P&I · " + money(p.tax) + " tax · " + money(p.up) + " upkeep";
    });
    document.querySelectorAll(".cashline").forEach(function(s){
      var src = SRC[s.dataset.k]; if(!src) return;
      s.textContent = money(cashToClose(src));
    });
    document.querySelectorAll(".paydiff").forEach(function(s){
      var a = SRC[s.dataset.a], b = SRC[s.dataset.b]; if(!a || !b) return;
      s.textContent = money(Math.max(0, monthlyPayment(a) - monthlyPayment(b)));
    });
    var pill = document.getElementById("sr-pill");
    if(pill) pill.textContent = "Ranked at " + CFG.rate.toFixed(2) + "%, " + CFG.dp + "% down, " +
      CFG.hold + " years" + ((S.rate !== CFG.rate || S.dp !== CFG.dp || S.hold !== CFG.hold)
        ? "; you are viewing " + S.rate.toFixed(2) + "%, " + S.dp + "% down, " + S.hold + " years. The rank does not move, it is computed offline."
        : "");
  }

  /* ---------- filters and sort ---------- */
  function num(el, k){ var v = el.dataset[k]; return v === "" || v === undefined ? null : +v; }
  function applyView(){
    var muni = (document.getElementById("g-muni")||{}).value || "";
    var maxask = +((document.getElementById("g-maxask")||{}).value || 0);
    var sort = (document.getElementById("g-sort")||{}).value || "score";
    var picksel = (document.getElementById("g-picks")||{}).value || "";
    var picks = load(PKEY, {});
    function visible(el){
      if(muni && el.dataset.muni !== muni) return false;
      if(maxask && +el.dataset.ask > maxask) return false;
      if(picksel){
        var p = picks[el.dataset.slug] || {};
        if(picksel === "mine" && !p.alex) return false;
        if(picksel === "partner" && !p.partner) return false;
        if(picksel === "both" && !(p.alex && p.partner)) return false;
        if(picksel === "either" && !(p.alex || p.partner)) return false;
      }
      return true;
    }
    function key(el){
      if(el.dataset.gated === "1") return 1e9;
      if(sort === "pay") return monthlyPayment(el);
      if(sort === "cond") return -num(el, "cond");
      if(sort === "band") return num(el, "bandlo");
      if(sort === "dom") return -num(el, "dom");
      return -(num(el, "score") || 0);
    }
    ["#lots", ".tablewrap tbody", ".minitable"].forEach(function(sel){
      var host = document.querySelector(sel); if(!host) return;
      var kids = [].slice.call(host.children).filter(function(c){ return c.dataset && c.dataset.slug; });
      kids.sort(function(a,b){ return key(a) - key(b); });
      kids.forEach(function(c){ c.hidden = !visible(c); host.appendChild(c); });
    });
    var jb = document.getElementById("jump");
    if(jb){
      var opts = [].slice.call(jb.options).slice(1);
      opts.sort(function(a,b){ var A = SRC[a.value.replace("sr-lot-","")], B = SRC[b.value.replace("sr-lot-","")];
        return (A && B) ? key(A) - key(B) : 0; });
      opts.forEach(function(o){ jb.appendChild(o); });
    }
  }

  /* ---------- Saturday plan ---------- */
  function paintSat(){
    var plan = load(SKEY, []), box = document.getElementById("satbox");
    document.querySelectorAll("[data-sat]").forEach(function(b){
      b.classList.toggle("on", plan.indexOf(b.dataset.sat) >= 0);
      b.textContent = plan.indexOf(b.dataset.sat) >= 0 ? "On the view list" : "Add to View List";
    });
    if(!box) return;
    box.hidden = plan.length === 0;
    var list = document.getElementById("sat-list"); if(!list) return;
    plan.sort(function(a,b){ return (+(SRC[a]||{dataset:{rank:99}}).dataset.rank) - (+(SRC[b]||{dataset:{rank:99}}).dataset.rank); });
    list.innerHTML = plan.map(function(k){
      var c = CFG.compare[k] || {}; return "<li><b>" + c.name + "</b> <em>" + money(c.ask||0) + "</em></li>";
    }).join("");
    var cnt = document.getElementById("sat-count");
    if(cnt) cnt.textContent = plan.length + (plan.length === 1 ? " house, in rank order." : " houses, in rank order.");
    document.querySelectorAll(".lot").forEach(function(l){
      if(plan.indexOf(l.dataset.slug) >= 0) l.setAttribute("data-sat-on", "1");
      else l.removeAttribute("data-sat-on");
    });
  }

  /* ---------- compare ---------- */
  var CROWS = [["score","Score"]].concat(CFG.order.map(function(k){ return ["c_"+k, CFG.label[k]]; }))
    .concat([["pay","Monthly payment"],["day1","Day-one work"],["wish","Wish list"],
             ["hold", CFG.hold + "-year cost"],["cash","Cash on closing day"],["band","Band"],
             ["gut","Gut scores"],["dom","Days on market"],["status","Status"],["flags","Flags"],["qs","Ask the agent"]]);
  function paintCmp(){
    var sel = load(CKEY, []), fab = document.getElementById("cmpfab"), box = document.getElementById("cmpbox");
    document.querySelectorAll("[data-cmp]").forEach(function(b){
      var on = sel.indexOf(b.dataset.cmp) >= 0;
      b.classList.toggle("on", on);
      b.textContent = on ? "Comparing, remove" : "Compare";
      b.disabled = !on && sel.length >= 4;
      b.title = b.disabled ? "Four is the most the comparison holds. Remove one first." : "";
    });
    if(fab){ fab.hidden = sel.length < 2; fab.textContent = "Compare (" + sel.length + ")"; }
    if(!box) return;
    box.hidden = sel.length < 2;
    var guts = load("walk-v6-gut", {});
    var html = "<tr><th></th>" + sel.map(function(k){
      return "<th><button type='button' class='cmpx' data-cmpx='" + k +
             "' title='Remove this house from the comparison' aria-label='Remove'>&times;</button>" +
             (CFG.compare[k]||{}).name + "<br><em>" + money((CFG.compare[k]||{}).ask||0) + "</em></th>";
    }).join("") + "</tr>";
    CROWS.forEach(function(r){
      html += "<tr><th class='vd'>" + r[1] + "</th>" + sel.map(function(k){
        var c = CFG.compare[k] || {}, src = SRC[k], v = "—";
        if(r[0] === "pay") v = src ? money(monthlyPayment(src)) + " /mo" : "—";
        else if(r[0] === "cash") v = src ? money(cashToClose(src)) : "—";
        else if(r[0].indexOf("c_") === 0){
          var ck = r[0].slice(2), val = (c.comp||{})[ck] || 0;
          v = "<span class='scorecol'><b class='v'>" + val + "</b><span class='bar'><i style='width:" +
              val + "%; background:var(--accent)'></i></span></span>";
        }
        else if(r[0] === "gut"){ var g = guts[k] || {}; v = (g.alex ? "You " + g.alex : "") + (g.partner ? " · Partner " + g.partner : "") || "—"; }
        else if(r[0] === "flags") v = (c.flags||[]).join(" · ") || "—";
        else if(["day1","wish","hold"].indexOf(r[0]) >= 0) v = money(c[r[0]]||0);
        else v = c[r[0]] === undefined ? "—" : c[r[0]];
        return "<td class='n'>" + v + "</td>";
      }).join("") + "</tr>";
    });
    document.getElementById("cmptab").innerHTML = html;
  }

  /* ---------- the fifteen pairs ---------- */
  function paintPairs(){
    var box = document.getElementById("pairbox"); if(!box) return;
    var who = (document.getElementById("pp-who")||{}).value || "alex";
    var all = load(QKEY, {}), mine = all[who] || {};
    var rows = [].slice.call(document.querySelectorAll(".pairrow"));
    var next = rows.filter(function(r){ return !mine[r.dataset.pair]; })[0];
    rows.forEach(function(r){ r.hidden = r !== next; });
    var done = Object.keys(mine).length;
    rows.forEach(function(r){
      var n = r.querySelector(".pp-n"); if(n) n.textContent = (done + 1) + " of " + CFG.npairs + " · ";
    });
    document.querySelectorAll(".pairpick").forEach(function(b){
      b.classList.toggle("on", mine[b.dataset.pair] === b.dataset.pick);
    });
    var dn = document.getElementById("pp-done");
    if(dn) dn.hidden = done < CFG.npairs;
  }
  function exportPairs(){
    var all = load(QKEY, {}), out = {preferences_patch: {choices: {}}};
    ["alex","partner"].forEach(function(w){
      var m = all[w] || {};
      if(Object.keys(m).length >= CFG.npairs)
        out.preferences_patch.choices[w] = CFG.pairids.map(function(id){ return {pair: id, pick: m[id]}; });
    });
    var t = document.getElementById("pp-text");
    t.hidden = false; t.value = JSON.stringify(out, null, 1); t.select();
  }

  /* ---------- wiring ---------- */
  function boot(){
    index();
    ["g-dp","g-rate","g-amort"].forEach(function(id){
      var el = document.getElementById(id); if(!el) return;
      el.value = id === "g-dp" ? S.dp : id === "g-rate" ? S.rate : S.amort;
      el.addEventListener("input", function(){
        S.dp = +document.getElementById("g-dp").value || CFG.dp;
        S.rate = +document.getElementById("g-rate").value || CFG.rate;
        S.amort = +document.getElementById("g-amort").value || CFG.amort;
        save(KEY, S); mirror(); paintPayments(); applyView(); paintCmp();
      });
    });
    /* the calculator's own inputs are the same settings */
    function mirror(){
      var m = {dp: "dp", rate: "rate", amort: "amort"};
      Object.keys(m).forEach(function(k){
        var el = document.getElementById(m[k]);
        if(el && +el.value !== S[k]){ el.value = S[k]; el.dispatchEvent(new Event("input", {bubbles:true})); }
      });
    }
    ["dp","rate","amort"].forEach(function(id){
      var el = document.getElementById(id); if(!el) return;
      el.addEventListener("input", function(){
        S.dp = +document.getElementById("dp").value || CFG.dp;
        S.rate = +document.getElementById("rate").value || CFG.rate;
        S.amort = +document.getElementById("amort").value || CFG.amort;
        save(KEY, S);
        ["g-dp","g-rate","g-amort"].forEach(function(g){
          var e2 = document.getElementById(g); if(e2) e2.value = g === "g-dp" ? S.dp : g === "g-rate" ? S.rate : S.amort;
        });
        paintPayments();
      });
    });
    ["g-muni","g-maxask","g-sort","g-picks"].forEach(function(id){
      var el = document.getElementById(id); if(el) el.addEventListener("change", applyView);
      if(el) el.addEventListener("input", applyView);
    });
    var hm = document.getElementById("holdmodes");
    if(hm) hm.addEventListener("click", function(e){
      var b = e.target.closest("[data-kind=hold]"); if(!b) return;
      S.hold = +b.dataset.v; save(KEY, S);
      hm.querySelectorAll("[data-kind=hold]").forEach(function(x){ x.classList.toggle("on", x === b); });
      paintPayments(); applyView();
    });
    document.addEventListener("click", function(e){
      var s = e.target.closest("[data-sat]");
      if(s){ var plan = load(SKEY, []), i = plan.indexOf(s.dataset.sat);
             if(i >= 0) plan.splice(i,1); else plan.push(s.dataset.sat);
             save(SKEY, plan); paintSat(); return; }
      var x = e.target.closest("[data-cmpx]");
      if(x){ var selx = load(CKEY, []), ix = selx.indexOf(x.dataset.cmpx);
             if(ix >= 0) selx.splice(ix,1);
             save(CKEY, selx); paintCmp(); return; }
      var c = e.target.closest("[data-cmp]");
      if(c){ var sel = load(CKEY, []), j = sel.indexOf(c.dataset.cmp);
             if(j >= 0) sel.splice(j,1); else if(sel.length < 4) sel.push(c.dataset.cmp);
             save(CKEY, sel); paintCmp(); return; }
      var pk = e.target.closest(".pairpick");
      if(pk){ var who = (document.getElementById("pp-who")||{}).value || "alex";
              var all = load(QKEY, {}); all[who] = all[who] || {};
              all[who][pk.dataset.pair] = pk.dataset.pick; save(QKEY, all); paintPairs(); return; }
      var ch = e.target.closest(".chg");
      if(ch){
        var want = ch.dataset.chg, set = (CFG.changed || {})[want] || [];
        document.querySelectorAll("[data-slug]").forEach(function(el){
          if(!el.dataset.ask) return;
          el.hidden = set.length ? set.indexOf(el.dataset.slug) < 0 : false;
        });
        document.querySelectorAll(".chg").forEach(function(x){ x.classList.toggle("on", x === ch); });
        return;
      }
    });
    var who = document.getElementById("pp-who");
    if(who) who.addEventListener("change", paintPairs);
    var px = document.getElementById("pp-export"); if(px) px.addEventListener("click", exportPairs);
    var pr = document.getElementById("pp-reset");
    if(pr) pr.addEventListener("click", function(){
      var all = load(QKEY, {}); all[(document.getElementById("pp-who")||{}).value || "alex"] = {};
      save(QKEY, all); paintPairs();
    });
    var sm = document.getElementById("sat-map");
    if(sm) sm.addEventListener("click", function(){
      var plan = load(SKEY, []); if(!plan.length) return;
      var addr = plan.map(function(k){ return encodeURIComponent((CFG.addr[k]||"")); });
      var url = "https://www.google.com/maps/dir/?api=1&origin=" + addr[0] +
                "&destination=" + addr[addr.length-1] +
                (addr.length > 2 ? "&waypoints=" + addr.slice(1,-1).join("|") : "");
      window.open(url, "_blank", "noopener");
    });
    var sp = document.getElementById("sat-print");
    if(sp) sp.addEventListener("click", function(){ document.body.classList.add("printsat"); window.print(); setTimeout(function(){ document.body.classList.remove("printsat"); }, 500); });
    var sc = document.getElementById("sat-clear");
    if(sc) sc.addEventListener("click", function(){ save(SKEY, []); paintSat(); });
    var cc = document.getElementById("cmp-clear");
    if(cc) cc.addEventListener("click", function(){ save(CKEY, []); paintCmp(); });
    var fab = document.getElementById("cmpfab");
    if(fab) fab.addEventListener("click", function(){
      var b = document.getElementById("cmpbox");
      if(b) window.scrollTo({top: b.getBoundingClientRect().top + window.pageYOffset - 58, behavior:"smooth"});
    });
    /* sticky mini-header: appears once the card's own top has scrolled off */
    var minis = [].slice.call(document.querySelectorAll(".lot"));
    function sticky(){
      minis.forEach(function(lot){
        var m = lot.querySelector(".stickymini"); if(!m) return;
        var r = lot.getBoundingClientRect();
        m.classList.toggle("on", r.top < 0 && r.bottom > 120);
      });
    }
    window.addEventListener("scroll", sticky, {passive:true}); sticky();

    /* showing mode opens the two sections that matter in a hallway, and closes the rest */
    function showMode(on){
      document.querySelectorAll(".lot details.v6sec").forEach(function(d){
        if(d.classList.contains("showopen")) d.open = on; else if(on) d.open = false;
      });
    }
    var modes = document.querySelector("#sr-ctl .sr-modes");
    if(modes) modes.addEventListener("click", function(e){
      var b = e.target.closest("[data-kind=mode]"); if(!b) return;
      showMode(b.dataset.v !== "all");
    });

    paintPayments(); applyView(); paintSat(); paintCmp(); paintPairs(); calibration();
    if("serviceWorker" in navigator){
      try{
        navigator.serviceWorker.register("sw.js", {updateViaCache: "none"}).then(function(reg){
          reg.update();
          setInterval(function(){ reg.update(); }, 60 * 60 * 1000);
        }).catch(function(){});
        var reloaded = false;
        navigator.serviceWorker.addEventListener("controllerchange", function(){
          if(reloaded) return;              /* once, never a loop */
          reloaded = true; location.reload();
        });
      }catch(e){}
    }
  }

  /* ---------- calibration: gut against model, once five gut scores exist ---------- */
  function calibration(){
    var guts = load("walk-v6-gut", {}), box = document.getElementById("calbox");
    if(!box) return;
    var pts = [];
    Object.keys(guts).forEach(function(k){
      ["alex","partner"].forEach(function(w){
        var g = +(guts[k]||{})[w]; var src = SRC[k];
        if(g && src && src.dataset.score) pts.push({k:k, who:w, g:g, m:+src.dataset.score});
      });
    });
    box.hidden = pts.length < 5;
    if(pts.length < 5) return;
    var W = 640, H = 200, L = 40, B = 28;
    function X(v){ return L + (W-L-12) * (v-1)/9; }
    function Y(v){ return (H-B) - (H-B-12) * (v-30)/50; }
    var mg = pts.reduce(function(a,p){ return a+p.g; },0)/pts.length;
    var mm = pts.reduce(function(a,p){ return a+p.m; },0)/pts.length;
    var sxy = 0, sxx = 0;
    pts.forEach(function(p){ sxy += (p.g-mg)*(p.m-mm); sxx += (p.g-mg)*(p.g-mg); });
    var b1 = sxx ? sxy/sxx : 0, b0 = mm - b1*mg;
    var dots = pts.map(function(p){
      return '<circle cx="'+X(p.g).toFixed(1)+'" cy="'+Y(p.m).toFixed(1)+'" r="5" fill="'+
        (p.who === "alex" ? "var(--accent)" : "var(--clear)")+'"><title>'+
        ((CFG.compare[p.k]||{}).name||p.k)+' · gut '+p.g+' · score '+p.m+'</title></circle>';
    }).join("");
    var line = '<line x1="'+X(1)+'" y1="'+Y(b0+b1).toFixed(1)+'" x2="'+X(10)+'" y2="'+Y(b0+b1*10).toFixed(1)+
               '" stroke="var(--muted)" stroke-dasharray="3 3"/>';
    var sent = CFG.order.map(function(k){
      var num = 0, den = 0;
      pts.forEach(function(p){
        var c = (CFG.compare[p.k]||{}).comp||{}, r = p.m - (b0 + b1*p.g);
        num += (c[k]-50) * r; den += Math.abs(c[k]-50);
      });
      var v = den ? num/den : 0;
      return "<li>" + CFG.label[k] + ": your gut runs " + (v > 0 ? "behind" : "ahead of") +
             " the model by " + Math.abs(v).toFixed(1) + "</li>";
    }).join("");
    var bars = CFG.order.map(function(k){
      return '<div class="sp"><em>'+CFG.label[k]+'</em><span><i style="width:'+
        Math.round(CFG.weights[k])+'%"></i></span><b>'+Math.round(CFG.weights[k])+'</b></div>';
    }).join("");
    document.getElementById("cal-body").innerHTML =
      '<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="200" role="img" aria-label="Gut score against model score">'+
      line+dots+'<text x="'+(W-12)+'" y="'+(H-4)+'" text-anchor="end" font-size="9.5" fill="var(--muted)">GUT SCORE →</text>'+
      '<text x="'+(L-8)+'" y="12" text-anchor="end" font-size="9.5" fill="var(--muted)">↑ SCORE</text></svg>'+
      '<ul class="callist">'+sent+'</ul><div class="sp-parts">'+bars+'</div>'+
      '<p class="maybe"><i>i</i>To act on this, answer the fifteen choices above, or edit <code>weights.alex</code> in <code>costs.yaml</code> and rebuild.</p>';
  }

  if(document.readyState !== "loading") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
</script>
<style>
/* additive only: no CSS variable, font size, colour or card section order is changed here */
.v6sec{border-top:1px solid var(--rule-soft); margin-top:10px}
.v6sec>summary{cursor:pointer; font-family:var(--mono); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); padding:8px 0}
.stickymini{display:none}
.lot .stickymini.on{display:flex; gap:10px; align-items:baseline; position:sticky; top:0; z-index:5;
  background:var(--card); border-bottom:1px solid var(--rule); padding:6px 0}
.pairbox,.satbox,.cmpbox,.calbox{border:1px solid var(--rule); border-radius:8px; padding:10px 14px; margin:12px 0}
.pairbox>summary{cursor:pointer; font-family:var(--mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase}
.pp-two{display:flex; gap:12px; flex-wrap:wrap}
.pairpick{flex:1 1 260px; text-align:left; background:var(--card); border:1px solid var(--rule);
  border-radius:8px; padding:10px; cursor:pointer; font:inherit; color:inherit}
.pairpick.on{border-color:var(--accent)}
.pp-head{display:flex; flex-direction:column; gap:2px; margin-bottom:6px}
.pp-line{display:block; margin-top:6px; color:var(--muted); font-size:12px}
.pp-q{font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted)}
.cmpfab{position:fixed; right:14px; bottom:14px; z-index:40; border:1px solid var(--rule);
  background:var(--card); border-radius:999px; padding:8px 14px; font:inherit; cursor:pointer}
.cmpscroll{overflow-x:auto}
.cmpx{display:inline-block; margin-right:6px; vertical-align:1px; background:none; border:1px solid var(--rule); border-radius:4px;
  line-height:1; padding:1px 5px; cursor:pointer; color:var(--muted); font:inherit; font-size:12px}
.cmpx:hover{color:var(--flag); border-color:var(--flag)}
.stamp.cmp[disabled]{opacity:.45; cursor:not-allowed}
#cmptab{table-layout:fixed; width:100%}
#cmptab th:first-child{width:120px}
#cmptab td,#cmptab th{white-space:normal; vertical-align:top; word-break:normal}
#cmptab td.n{text-align:right}
#cmptab td,#cmptab td:last-child{color:var(--ink); font-size:11.5px; max-width:none; line-height:1.4}
#cmptab th.vd{color:var(--muted)}
@media (max-width:700px){ #cmptab{min-width:520px} }
.satlist{margin:6px 0; padding-left:20px}
.changes{margin:6px 0 0; font-size:12.5px; color:var(--muted)}
.changes .chg{background:none; border:none; padding:0 2px; font:inherit; color:var(--accent); cursor:pointer; text-decoration:underline}
.byo{margin-top:10px; border-top:1px solid var(--rule-soft); padding-top:8px}
.byo h4{margin:0 0 4px; font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted)}
.byo ul{margin:0; padding-left:18px}
.callist{margin:6px 0; padding-left:18px; font-size:12.5px; color:var(--muted)}
.lot[data-grey="1"]{opacity:.55}
[hidden]{display:none !important}
.stamp.sat,.stamp.cmp{cursor:pointer; font:inherit; background:none; border:1px solid var(--rule)}
.payhero,.pay{white-space:nowrap}
.tablewrap table.big td.n,.tablewrap table.big th.n{text-align:center}
.tablewrap table.big td.n .pay{font-weight:400}
.money .hero{grid-column:span 2}
@media (max-width:520px){ .money .hero{grid-column:span 1} }
.money .hero dd{color:var(--ink)}
.money .hero dd .pay,.money .hero dd .payhero{font-weight:500; color:var(--ink)}
.money .hero dd.paysub{display:block; font-family:var(--mono); font-size:11px; font-weight:400;
  color:#1a1a1a; line-height:1.5; letter-spacing:0; margin-top:4px}
.sp em{line-height:1.15}
.sp em .spw{display:block; font-family:var(--mono); font-size:8px; letter-spacing:.04em;
  color:var(--muted); text-decoration:none; opacity:.85}
.renofigs{display:flex; gap:26px; flex-wrap:wrap; margin:2px 0 10px}
.renofigs div{display:flex; flex-direction:column; gap:1px}
.renofigs .rf-lab{font-family:var(--mono); font-size:8.5px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--muted)}
.renofigs .rf-val{font-size:20px; font-variant-numeric:tabular-nums}
.renofigs .rf-note{font-size:11px; color:var(--muted)}
.roomscore{grid-template-columns:minmax(230px,340px) minmax(240px,420px) !important;
  justify-content:start; align-items:center; gap:12px 34px !important}
.roomscore .sp-parts{width:100%}
@media (max-width:700px){ .roomscore{grid-template-columns:1fr !important} }
.term dt{font-size:12px !important; letter-spacing:.085em !important}
.live-row{grid-template-columns:repeat(auto-fit,minmax(128px,1fr)) !important; gap:8px 14px !important}
.live-row dd.livenote{font-family:inherit; font-size:10.5px; font-weight:400; color:var(--muted);
  letter-spacing:0; line-height:1.35; margin-top:1px}
.whylist{margin:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:12px 26px}
.whylist div{display:flex; flex-direction:column; gap:3px; padding-bottom:10px;
  border-bottom:1px solid var(--rule-soft)}
.whylist dt{display:flex; align-items:baseline; gap:8px; flex-wrap:wrap;
  font-family:var(--mono); font-size:10px; letter-spacing:.09em; text-transform:uppercase; color:var(--muted)}
.whylist dt b{font-size:13px; letter-spacing:0; color:var(--ink); font-weight:500}
.whylist dt u{text-decoration:none; font-size:9px; color:var(--muted)}
.whylist dd{margin:0; font-size:12.5px; line-height:1.5; color:var(--ink)}
.rooms>summary{cursor:pointer; font-family:var(--mono); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); padding:8px 0}
.stamp.sat.on,.stamp.cmp.on{border-color:var(--accent); color:var(--accent)}
@media print{ body.printsat .lot:not([data-sat-on]){display:none} }

/* ---------- cohesion pass, 13 September ----------
   No new content and no colour variable. What changes is that the card had six label sizes
   (8, 8.5, 9, 9.5, 10, 10.5), four figure sizes and four different shapes for what are
   really peer sections. This collapses each of those to one scale. */

/* One label scale: every eyebrow, summary and dt on the card is the same mono size. */
.body .money dt,.body .live-row dt,.body .renofigs .rf-lab,.body .split h3,
.body .reno h3,.body .v6sec>summary,.body .byo h4,.body .rooms>summary,
.body .ask span,.body .whylist dt,.body .reno h3 b{
  font-family:var(--mono); font-size:9.5px; letter-spacing:.09em;
  text-transform:uppercase; font-weight:500}
.body .whylist dt b{font-size:13px; letter-spacing:0; text-transform:none}
.body .whylist dt u{font-size:9.5px; letter-spacing:.09em; text-transform:uppercase}
.body .reno h3 b{color:var(--ink)}
.body .check h3 .ck-prog{font-size:9.5px; letter-spacing:.09em}

/* One figure scale: 17px for every money figure on the card, whatever panel it sits in. */
.body .money dd,.body .live-row dd,.body .renofigs .rf-val{
  font-family:var(--mono); font-size:17px; font-weight:500;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; line-height:1.2}
.body .live-row dd.livenote,.body .renofigs .rf-note{
  font-family:inherit; font-size:10.5px; font-weight:400; letter-spacing:0;
  line-height:1.4; color:var(--muted); margin-top:2px}

/* One body size for prose inside a card. */
.body .whylist dd,.body .known li,.body .check li label,.body .ask,
.body .reno .maybe,.body .byo li,.body .reno .none{font-size:13.5px; line-height:1.55}
.body .take{font-size:15px; line-height:1.62}

/* One panel shape. Tinted panels are derived numbers, bordered panels are the record. */
.body .live-row,.body .ask,.body .reno{border-radius:10px; padding:14px 16px}
.body .live-row{row-gap:12px !important}
.body .live-row::before{content:"Price and financing"; grid-column:1/-1;
  font-family:var(--mono); font-size:9.5px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--accent); opacity:.75; margin-bottom:-2px}

/* One disclosure treatment: same caret, same colour, on every collapsible section. */
.body .v6sec>summary,.body .rooms>summary,.body details.costs>summary{
  color:var(--accent); list-style:none; display:flex; align-items:center; gap:7px}
.body .v6sec>summary::-webkit-details-marker,
.body .rooms>summary::-webkit-details-marker{display:none}
.body .v6sec>summary::before,.body .rooms>summary::before{
  content:"▸"; font-size:11px; line-height:1; transition:transform .15s}
.body .v6sec[open]>summary::before,.body .rooms[open]>summary::before{transform:rotate(90deg)}
.body .v6sec>summary:focus-visible{outline:2px solid var(--accent); outline-offset:3px}

/* The caveat under "Before you offer" had no styling of its own and rendered as a bare
   exclamation mark against the text. Same treatment as the one inside Renovations. */
.body .byo .maybe{display:flex; gap:8px; align-items:baseline; margin:8px 0 0;
  font-size:12.5px; line-height:1.5; color:var(--muted)}
.body .byo .maybe i{flex:none; font-style:normal; font-family:var(--mono); font-size:9px;
  letter-spacing:.1em; color:var(--muted); padding:2px 6px; border:1px solid var(--rule);
  border-radius:4px; background:var(--accent-soft); position:relative; top:-1px}
.body .byo ul{display:flex; flex-direction:column; gap:4px}
.body .sr-head h3{font-size:9.5px; letter-spacing:.09em; font-weight:500}
/* "100 / 100" was wrapping to two lines in the score panel on a phone. */
.sp b{white-space:nowrap}
@media (max-width:520px){ .sp{grid-template-columns:58px minmax(0,1fr) 58px} }
</style>"""

def v6js():
    cfg = {"dp": DOWN_PCT, "rate": MORT_RATE, "amort": AMORT, "hold": HOLD_DEF,
           "closing": S.CFG["hold"]["closing_extras"],
           "order": COMP_ORDER, "label": COMP_LABEL, "weights": W_JOINT,
           "compare": compare_js,
           "addr": {SLUG_SHORT[r["address"]]: r["address"] for r in ROWS},
           "changed": CHANGED,
           "npairs": (PAIRS or {}).get("n", 15),
           "pairids": [p["id"] for p in (PAIRS or {}).get("pairs", [])]}
    return V6JS.replace("__CFG__", json.dumps(cfg))

# ---------- offline: manifest and a service worker at the repo root ----------
def write_offline(version):
    """A page the buyers open in a basement with no signal, that is still the page that was last
    deployed.

    The first version of this was cache-first against a fixed cache name, which is the classic
    trap: the worker served whatever it cached on the first visit and never checked again, and
    because `sw.js` itself never changed byte for byte the browser never installed a replacement.
    A deploy could not reach anybody who had already opened the page.

    So: the cache name carries the build, install skips waiting and activate claims the open pages,
    and the fetch rule is network first with a cache fallback. Online you always get the deploy;
    offline you get the last build you saw. The page reloads itself once when a new worker takes
    over, so a rebuild reaches a phone that is already open."""
    json.dump({"name": "Walking the Shortlist", "short_name": "Shortlist", "start_url": "index.html",
               "display": "standalone", "background_color": "#ffffff", "theme_color": "#ffffff",
               "icons": []}, open(os.path.join(ROOT, "manifest.json"), "w"), indent=1)
    open(os.path.join(ROOT, "sw.js"), "w", encoding="utf-8").write(
        'var VERSION = "%s";\n' % version +
        'var C = "walk-" + VERSION;\n'
        'var FILES = ["index.html", "full.html", "mobile.html", "manifest.json"];\n'
        '\n'
        'self.addEventListener("install", function(e){\n'
        '  self.skipWaiting();\n'
        '  e.waitUntil(caches.open(C).then(function(c){ return c.addAll(FILES); }).catch(function(){}));\n'
        '});\n'
        '\n'
        'self.addEventListener("activate", function(e){\n'
        '  e.waitUntil(caches.keys().then(function(ks){\n'
        '    return Promise.all(ks.filter(function(k){ return k !== C; }).map(function(k){ return caches.delete(k); }));\n'
        '  }).then(function(){ return self.clients.claim(); }));\n'
        '});\n'
        '\n'
        '/* Network first. The deployed page always wins when there is a network; the cache is the\n'
        '   fallback for a basement, not the source of truth. */\n'
        'self.addEventListener("fetch", function(e){\n'
        '  var r = e.request;\n'
        '  if (r.method !== "GET" || new URL(r.url).origin !== self.location.origin) return;\n'
        '  e.respondWith(\n'
        '    fetch(r).then(function(resp){\n'
        '      if (resp && resp.ok) {\n'
        '        var copy = resp.clone();\n'
        '        caches.open(C).then(function(c){ c.put(r, copy); }).catch(function(){});\n'
        '      }\n'
        '      return resp;\n'
        '    }).catch(function(){\n'
        '      return caches.match(r).then(function(hit){\n'
        '        return hit || caches.match("index.html");\n'
        '      });\n'
        '    })\n'
        '  );\n'
        '});\n')

# ---------- sold comps ----------
def write_sold():
    import csv as _csv
    with open(os.path.join(R, "out", "sold.csv"), "w", newline="") as f:
        w = _csv.writer(f); w.writerow(["address", "municipality", "usable_sqft", "sold_price", "status_date"])
        for r in ROWS:
            o = OBS[SLUG_OF[r["address"]]]
            if o.get("sold_price"):
                w.writerow([r["address"], o.get("municipality"), r["usable_sqft"],
                            o["sold_price"], o.get("status_date") or ""])

FIELDS = {
  "KICKER": f"Halton search · walk-through companion · rebuilt {BUILD_DATE} · ranked at "
            f"{MORT_RATE:.2f}%, {DOWN_PCT:.0f}% down, {HOLD_DEF} years · {n} listings, "
            f"{N_RANKED} ranked, {n - N_RANKED} gated",
  "CHANGES": changes_line(),
  "STANDFIRST": f"""Every house on both saved searches, {n} in all, on one score out of 100 built from eight things about the house and the weights the two of you set.
      Every one has had its photos read at full resolution. Each card lists what the photos settled, what only a person standing in the room can
      settle, every room with its real dimensions, and every renovation line with what it costs and how likely it is to be needed.""",
  "MASTMETA": f"""
      <span>{n} of {n} photo-graded</span>
      <span>{len(see_first)} marked See First</span>
      <span>One score, eight components</span>
      <span>Weights {"provisional" if PROVISIONAL else "set from fifteen choices each"}</span>
      <span>{HOLD_DEF}-year hold</span>
      <span>Model v3.4 · rank v6</span>
    """,
  "HOWTO": f"""<b>How the order works.</b> Four steps, and no step knows about the next one.<br>
    <b>1. Rules first, before any scoring.</b> A house that fails one is not ranked: confirmed basement
    moisture, fewer bedrooms above grade than you set, over a budget or cash ceiling if you set one, or a
    project if you had said no projects. {n - N_RANKED} of {n} fail one. They sit at the end with the reason on the card.<br>
    <b>2. Eight things about the house, each out of 100.</b> Space, layout, baths, parking, lot, location,
    condition and price. Every one is an absolute scale, so a house scored today is comparable to one
    scored in March, and none of them moves when the batch changes.<br>
    <b>3. Your weights.</b> Fifteen forced choices between two real houses from this batch, one set each.
    The weights are fitted from what you pick, not from numbers you are asked to invent.
    {"They are provisional until both of you have answered." if PROVISIONAL else ""}<br>
    <b>4. One score, sorted descending.</b> Weighted mean of the eight, docked
    {round(100*(1-S.CFG["split_dock"]))}% for a split-level plan. That is the whole rule. The band beside
    it is where the house lands across every weight set, every hold and the two ends of its own day-one
    uncertainty.<br>
    <b>One rule underneath all of it:</b> photographs can only ever count against a house, except through
    condition, where a clean full-resolution read can lower a finish line toward a floor of 15%, never to
    zero. No photograph moves a panel, roof, furnace or window, and none can raise the grade. Photographs
    alone cannot push condition past about 77 of 100; the rest needs somebody standing in the house.""",
  "GLOSSARY": GLOSSARY,
  "TABLEINTRO": f"""All {n}, in score order. Score is the composite out of 100 and it is what the list is sorted on; Grade is the facts letter and it is not.{{{{RENOSENT}}}} Band is where the house lands across every weight set on file, holds of 3, 5 and 10 years, and the low and high end of its own day-one uncertainty. A wide band means the rank is resting on assumptions rather than evidence.""",
  "CARDSINTRO": """In score order, with the score broken into its eight components on every card, heaviest weight first. Everything below the money block is closed until you open it. Open "Renovation cost, line by line" on any card for the full cost build-up.""",
  "FRONTIERCHART": "",
  "FILTERS": FILTERS,
  "SATURDAY": SATURDAY,
  "PAIRS": pairs_section(),
  "COMPARE": COMPARE,
  "CALIBRATION": CALIBRATION,
  "V6JS": v6js(),
  "HOLDTOGGLE": HOLD_BTNS,
  "COLOPHON": f"""One score out of 100: eight components on absolute scales, weighted by
    {"provisional weights pending fifteen pairwise choices from each buyer" if PROVISIONAL else "weights fitted from fifteen pairwise choices per buyer"} ·
    condition is the cost-weighted share of this house's work that is not expected, two-sided at full
    resolution, capped for photographs · price is the {HOLD_DEF}-year cost of the hold against a fixed
    $270,000 to $420,000 search band · cost of capital {S.COST_OF_CAPITAL:.1%}, derived from
    {MORT_RATE:.2f}% on {100-DOWN_PCT:.0f}% and {S.CFG["hold"]["opportunity_rate"]:.1%} on the down payment ·
    exit commission {S.CFG["hold"]["exit_commission"]:.1%} · no appreciation assumed ·
    Model v3.4, rank v6, {BUILD_DATE} · {n} listings, all photo-graded · Nothing here is an offer price""",
  "LOTS": "\n" + "".join(cards),
  "MINITABLE": minitable(),
  "THEAD": THEAD,
  "TBODY": table_rows(),
  "HOUSES": json.dumps(houses_js),
  "RESERVE": json.dumps(reserve_js),
  "SHOW_DATA": json.dumps({"houses": show_js, "walk": SH.WALK,
                           "qs": {k: {"opts": [{"v": x["v"], "patch": x["patch"]} for x in q["opts"] if "patch" in x]}
                                  for k, q in SH.QS.items()}}),
}

write_sold()

for variant in ("full", "mobile"):
    tpl = open(os.path.join(R, f"page_{variant}.tpl.html"), encoding="utf-8").read()
    out = tpl
    extra = [("JUMPOPTS", jumpopts(variant)),
             ("RENOSENT", " Renovation lines are on each card, with their odds." if variant == "full" else "")]
    for key, val in list(FIELDS.items()) + extra:
        out = out.replace("{{" + key + "}}", val)
    left = re.findall(r"\{\{(\w+)\}\}", out)
    if left: print("  UNFILLED placeholders:", sorted(set(left)), file=sys.stderr)
    path = os.path.join(ROOT, f"{variant}.html")
    open(path, "w", encoding="utf-8").write(out)
    print(f"wrote {variant}.html {len(out):,} bytes; {n} cards")

import hashlib
_v = hashlib.md5(b"".join(open(os.path.join(ROOT, f"{v}.html"), "rb").read()
                          for v in ("full", "mobile"))).hexdigest()[:12]
write_offline(_v)
print(f"wrote manifest.json and sw.js; cache name walk-{_v}")

# the one thing the spec forbids anywhere but Monthly payment
for variant in ("full", "mobile"):
    txt = open(os.path.join(ROOT, f"{variant}.html"), encoding="utf-8").read()
    bad = [w for w in ("true cost", "own /mo", "cost to own", "overpay", "frontier",
                       "best value", "needs-work", "Reserve /") if w.lower() in txt.lower()]
    if bad: print(f"  RETIRED WORDS still in {variant}.html: {bad}", file=sys.stderr)
