#!/usr/bin/env python3
"""Build the 'Walking the Shortlist' page from the model outputs.
Reads: observations.json, out/decision.csv, out/detail.json, rooms_legacy.json, live_2026-09-12.json
Writes: ../deliverables/walking-the-shortlist.artifact-src.html (body-only, for the Artifact tool)
        ../deliverables/Walking-the-Shortlist.html (standalone, offline)
Style block, calculator JS and the 'Under the hood' tail are lifted from walkthrough_template.html (the v3.0 hand-built page)
so the design stays identical; every card is generated."""
import json, csv, os, re, html, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as S
import showing as SH

R = os.path.dirname(os.path.abspath(__file__))
DEL = os.path.join(R, "..", "deliverables")
OBS = {o["slug"]: o for o in json.load(open(os.path.join(R, "observations.json")))}
DET = json.load(open(os.path.join(R, "out", "detail.json")))
ROWS = list(csv.DictReader(open(os.path.join(R, "out", "decision.csv"))))
LEGROOMS = json.load(open(os.path.join(R, "rooms_legacy.json")))
LIVE = json.load(open(os.path.join(R, "live_2026-09-12.json")))
URLT = LIVE["url_template"]
LIVE_IDS = {l[0] for l in LIVE["live"]}
OLD = open(os.path.join(R, "walkthrough_template.html"), encoding="utf-8").read()   # the v3.0 hand-built page, kept as the style/JS template

def esc(s): return html.escape(str(s if s is not None else ""))
def money(n): return "${:,.0f}".format(n)
def short(slug): return slug.split("-", 2)[-1]          # bur-3205-tania -> tania
def addr_short(a): return a.split(",")[0].replace(" Crescent", " Cres").replace(" Avenue", " Ave").replace(" Drive", " Dr").replace(" Court", " Ct").replace(" Road", " Rd").replace(" Boulevard", " Blvd").replace(" Place", " Pl")

# ---------- pieces lifted from the old page ----------
STYLE = OLD[: OLD.index('<div class="wrap">')]
RENO_CSS = """<style>
  .reno{border:1px solid var(--rule); border-radius:4px; padding:12px 14px 10px; background:var(--card)}
  .reno h3{font-family:var(--mono); font-size:10px; letter-spacing:.11em; text-transform:uppercase; margin:0 0 8px; font-weight:500; color:var(--accent); display:flex; justify-content:space-between; gap:12px}
  .reno h3 b{font-family:var(--mono); font-weight:500; color:var(--ink); letter-spacing:0; text-transform:none; font-size:11px}
  .reno ul{margin:0; padding:0; list-style:none; display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:5px 18px}
  .reno li{display:flex; justify-content:space-between; gap:10px; font-size:14px; line-height:1.4; border-bottom:1px dotted var(--rule-soft); padding-bottom:3px}
  .reno li .amt{font-family:var(--mono); font-variant-numeric:tabular-nums; white-space:nowrap}
  .reno li.unseen{color:var(--muted)}
  .reno li.unseen .amt::after{content:" ?"; color:var(--flag)}
  .reno li.conf .amt{font-weight:600}
  .reno .maybe{margin:8px 0 0; font-size:12.5px; color:var(--muted); line-height:1.45}
  .reno .maybe i{font-style:normal; font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase; margin-right:6px}
  .reno .none{margin:0; font-size:14px; color:var(--muted)}
  td.reno-col{font-size:12px; line-height:1.35; max-width:260px}
</style>
"""
RENO_CSS = RENO_CSS + SH.CSS
STYLE = STYLE.replace('</head>', RENO_CSS + '</head>') if '</head>' in STYLE else STYLE + RENO_CSS
SHOW_JS = open(os.path.join(R, "showing.js"), encoding="utf-8").read()
_uh = OLD.index("<h2>Under the hood</h2>")
TAIL_START = OLD.rfind('<div class="section-head">', 0, _uh)
TAIL_END = OLD.index('<p class="colophon">')
TAIL = OLD[TAIL_START:TAIL_END]
TAIL = TAIL.replace("it\n        is why <b>three houses here with no photo pass at all carry the largest wish lists.</b>",
                    "it\n        is why the houses whose tells came back original carry the largest wish lists.")
TAIL = TAIL.replace("Because <b class=\"hot\">not one\n        listing showed a panel, furnace or water heater</b>, every house here is charged the full reserve.",
                    "Because <b class=\"hot\">only four of the 37 listings showed anything mechanical</b> (a tankless water heater at Barberry, a tank at Pallatine, a furnace cabinet at Samford, PEX lines at Kent) and none showed a panel, every house here is charged the full reserve.")
TAIL = TAIL.replace("Not one of these 24 listings contains a\n      single photograph of an electrical panel, a furnace or a water heater. Across houses built between\n      1954 and 1999, that is the largest gap in everything above, and the first question closes most of it.",
                    "Not one of these 37 listings contains a photograph of an electrical panel, and only four show any\n      mechanical equipment at all. Across houses built between 1950 and 2008, that is the largest gap in everything\n      above, and the first question closes most of it. Two listings were caught overstating: Oxlow calls an\n      above-ground pool in-ground, and Tania has at least one virtually staged basement frame.")
JS_START = OLD.index("const CLOSING_EXTRAS")
JS_END = OLD.index("function PSF(c)")
CALC_JS = OLD[JS_START:JS_END]

GR_CLASS = lambda g: "g-a" if g.startswith("A") else ("g-b" if g.startswith("B") else "g-c")
GRADE_TXT = lambda g: g.replace("-", "−")

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

def rooms_html(o):
    k = short(o["slug"])
    rows = LEGROOMS.get(k)
    if not rows and o.get("rooms_raw"):
        rows = []
        for r in o["rooms_raw"]:
            lvl, name = r[0], r[1]; sq = r[2] if len(r) > 2 else None; ft = r[3] if len(r) > 3 else ""
            rows.append([lvl, name, None, sq, ft])
    if not rows: return ""
    h = ['<details class="rooms"><summary>Every room, as entered on MLS</summary><div class="roomtab"><table>',
         '<thead><tr><th>Level</th><th>Room</th><th>Feet</th><th style="text-align:right;padding-right:14px">Sq ft</th><th>Notes</th></tr></thead><tbody>']
    last = None
    for r in rows:
        lvl = "" if r[0] == last else r[0]; last = r[0]
        small = " small" if (r[3] and r[3] < 100 and re.search("bed", str(r[1]), re.I)) else ""
        h.append(f"<tr><td class='lvl'>{esc(lvl)}</td><td>{esc(r[1])}</td><td class='dim'>{esc(r[2] or '—')}</td>"
                 f"<td class='sq{small}'>{esc(r[3] or '—')}</td><td class='ft'>{esc(r[4] or '')}</td></tr>")
    h.append("</tbody></table></div></details>")
    return "\n".join(h)

def costs_html(o, d):
    def row(i):
        pct = round(i["p"] * 100)
        return (f"<tr><td class='odds'><i>{pct}%</i><u><s style='width:{pct}%'></s></u></td>"
                f"<td>{esc(i['name'])}<span class='why'>{esc(i['basis'])}</span></td><td class='amt'>{money(i['exp'])}</td></tr>")
    d1 = "".join(row(i) for i in d["items"] if i["bucket"] == "day1")
    wl = "".join(row(i) for i in d["items"] if i["bucket"] == "wishlist")
    rs = "".join(f"<tr><td>{esc(i['name'])}<span class='why'>{i['life']} yr life" + (f", charged at {round(i['p']*100)}%" if i['p'] < 1 else "") +
                 f"</span></td><td class='amt'>{money(i['exp']/max(i['p'],0.01))}</td><td class='amt'>{money(i['per_yr'])}/yr</td></tr>"
                 for i in d["items"] if i["bucket"] == "reserve")
    gparts = [("size", "Size", 25), ("layout", "Layout", 20), ("baths", "Baths", 20), ("lot", "Lot", 15), ("location", "Location", 12), ("parking", "Parking", 8)]
    gb = "".join(f"<div class='gp'><em>{lab}</em><span><i style='width:{round(100*d['fact_parts'].get(k,0)/mx)}%'></i></span><b>{d['fact_parts'].get(k,0):.0f} / {mx}</b></div>" for k, lab, mx in gparts)
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
<section class="cb rs"><h4>Reserve <b>{money(d['reserve_monthly'])}/mo</b></h4><table><tbody>{rs}</tbody></table>
<p class="foot">Replacement cost and expected life, annualised. {money(d['near_term_5yr'])} of this sits in components already past their rated life if the house is as old as it looks. Every date you get from the agent shrinks it.</p></section>
</div>
<div class="valuebox"><dl class="valuerow">
<div><dt>Peer benchmark</dt><dd>{money(d['norm'])}</dd></div><div><dt>Room to spend</dt><dd>{money(d['headroom'])}</dd></div>
<div><dt>Worth after the work</dt><dd>{money(d['arv_mid'])}</dd></div><div><dt>Recovered</dt><dd>{d['recovered_pct']}%</dd></div>
<div class="neg"><dt>Never comes back</dt><dd>{money(d['sunk'])}</dd></div><div><dt>Break-even</dt><dd>{money(d['breakeven'])}</dd></div>
</dl><p class="valuenote">Spend the full {money(d['day1_p80']+d['wish_p80'])} and the house is worth roughly {money(d['arv_lo'])} to {money(d['arv_hi'])}, against {money(d['breakeven'])} all in. <b>{money(d['sunk'])} of that spend does not come back</b> on resale, which is normal and is the price of living in it. The peer benchmark is {d['usable']:,} usable sq ft at a flat ${psf} a foot, so there is {money(d['headroom'])} of headroom before the work starts over-improving for the street.{big} Property tax {money(d['taxes'] or 0)} a year. {era[0].upper()+era[1:]}, so an unseen job is priced at {round(d['era_p']*100)}% likely.{bgnote}</p></div>
<div class="gradebox"><span class="gl">Grade {d['fact_score']:.0f} / 100</span>{gb}</div>
</div></details>"""

def kmoney(n): return f"${round(n/1000):,}k"
def reno_html(d):
    items = d.get("reno") or []
    needed = [i for i in items if i["status"] != "possible"]
    maybe = [i for i in items if i["status"] == "possible"]
    if not needed and not maybe:
        return '<section class="reno"><h3>Renovations needed</h3><p class="none">Nothing the photos or the era point at. Reserve items (roof, furnace, A/C) sit in the monthly figure.</p></section>'
    li = "".join(f'<li class="{"conf" if i["status"]=="confirmed" else "unseen" if i["status"]=="likely, unseen" else ""}" title="{i["status"]}, {round(i["p"]*100)}% likely, {i["bucket"]}">'
                 f'<span>{esc(i["name"])}</span><span class="amt">{kmoney(i["cost"])}</span></li>' for i in needed)
    tot = sum(i["cost"] for i in needed)
    head = f'<h3>Renovations needed<b>{kmoney(tot)} if you do all of it</b></h3>' if needed else '<h3>Renovations needed</h3>'
    mb = ""
    if maybe:
        mb = '<p class="maybe"><i>Possible</i>' + ", ".join(f"{esc(i['name'])} {kmoney(i['cost'])} ({round(i['p']*100)}%)" for i in maybe) + "</p>"
    if any(i["status"] == "likely, unseen" for i in needed):
        mb += '<p class="maybe"><i>?</i>never shown in the photos, so priced at the base rate for a house this age. Reserve items (roof, furnace, A/C, tank) are in the monthly figure, not here.</p>'
    return f'<section class="reno">{head}<ul>{li}</ul>{mb}</section>'

def card(rank, row, o, d):
    slug = o["slug"]; k = short(slug)
    url = URLT.replace("{ID}", o["listing_id"])
    grade = row["grade"]; v = row["verdict"]
    tells = int(row["tells_seen_of_15"]); photos = int(row["photos_total"] or 0)
    live = o["listing_id"] in LIVE_IDS
    ev = row["evidence"]
    stamps = [f'<span class="stamp seen">Photos reviewed · {photos} · {tells}/15 tells settled</span>',
              f'<span class="stamp {"seen" if ev=="high" else "unseen"}" title="{esc(row["evidence_notes"])}">Evidence {ev}</span>']
    if v == "STOP": stamps.append('<span class="stamp unseen">STOP</span>')
    elif v == "SEE FIRST": stamps.append('<span class="stamp seen">See first</span>')
    if not live: stamps.append('<span class="stamp unseen">Off the saved search</span>')
    for n in (d.get("verdict_notes") or []):
        if n.startswith("POOL") or n.startswith("TENANTED") or "virtually" in n or n.startswith("OIL"): stamps.append(f'<span class="stamp unseen">{esc(n.split(" — ")[0])}</span>')
    stamps.append(f'<a class="stamp link" href="{esc(url)}" target="_blank" rel="noopener">Open listing ↗</a>')
    mo = int(row["monthly_carry"])
    warn = " warn" if mo > 780 else ""
    known = known_lines(o)
    def kl(t, b): return "<li>" + ('<span class="bad">' + esc(t) + "</span>" if b else esc(t)) + "</li>"
    known_html = "".join(kl(t, b) for t, b in known) or "<li>Nothing settled: no readable tells in the photo set</li>"
    checks = check_lines(o)
    check_html = "".join(f'<li>{esc(t)}</li>' for t in checks)
    take = esc(o.get("notes") or "")
    d1_txt = ""
    if o.get("stage2_pass") == "re-read": d1_txt = " Re-read on 12 September; the earlier pass had most tells unresolved."
    return f"""
    <article class="lot" id="lot-{k}" data-slug="{k}">
      <div class="rail"><div class="rank">{rank}</div><div class="grade {GR_CLASS(grade)}">{GRADE_TXT(grade)}</div>
        <div class="psf"><b>${row['all_in_psf']}</b><span>per usable sq ft</span></div>
        <div class="psf"><b>{row['rank_low']}–{row['rank_high']}</b><span>rank if unknowns flip</span></div></div>
      <div class="body">
        <div class="lot-head">
          <h2><a href="{esc(url)}" target="_blank" rel="noopener">{esc(o['address'].split(',')[0].title().replace("Mls","MLS"))}</a></h2>
          <p class="where">{where_line(o, d)}</p>
          <div class="tags">{''.join(stamps)}</div>
        </div>
        <dl class="money">
          <div><dt>Ask</dt><dd>{money(o['list_price'])}</dd></div>
          <div class="hero"><dt>Day-one cash</dt><dd>{money(d['day1_p80'])}</dd></div>
          <div><dt>True cost</dt><dd>{money(o['list_price']+d['day1_p80'])}</dd></div>
          <div class="{warn.strip()}"><dt>Taxes + reserve</dt><dd>{money(mo)}<span class="per">/mo</span></dd></div>
          <div><dt>Wish list</dt><dd>{money(d['wish_p80'])}</dd></div>
        </dl>
        <dl class="live-row" data-live="{k}"></dl>
        <p class="take">{take}{d1_txt}</p>
        {reno_html(d)}
        <div class="split">
          <section class="known"><h3>Settled by the photos</h3><ul>{known_html}</ul></section>
          <section class="check"><h3>Check when you're there</h3><ul>{check_html}</ul></section>
        </div>
        <p class="ask"><span>Ask before you go</span>{esc(ask_line(o))}</p>
        {SH.record_html(k, o, d, checks)}
        {rooms_html(o)}
        {costs_html(o, d)}
      </div>
    </article>"""

# ---------- assemble ----------
n = len(ROWS)
see_first = [r for r in ROWS if r["verdict"] == "SEE FIRST"]
cards = []; houses_js = []; reserve_js = {}; show_js = {}
for r in ROWS:
    slug = next(s for s, o in OBS.items() if o["address"] == r["address"])
    o = OBS[slug]; d = DET[slug]
    cards.append(card(int(r["rank"]), r, o, d))
    houses_js.append({"k": short(slug), "n": addr_short(o["address"]), "p": o["list_price"], "d": d["day1_p80"], "t": round(o.get("annual_taxes") or 0)})
    reserve_js[short(slug)] = d["reserve_monthly"]
    show_js[short(slug)] = {"slug": slug, "name": addr_short(o["address"]), "psf": int(r["all_in_psf"]),
                            "rank": int(r["rank"]), "verdict": r["verdict"],
                            "open_q": len(SH.unresolved(o))}

def table_rows():
    out = []
    for r in ROWS:
        cls = ' class="stop"' if r["verdict"] == "STOP" else ""
        out.append(f"<tr{cls}><td class='n'>{r['rank']}</td><td>{esc(r['address'].split(',')[0].title())}</td><td class='vd'>{GRADE_TXT(r['grade'])}</td>"
                   f"<td class='n'>{money(int(r['ask']))}</td><td class='n'>{money(int(r['day1_p80']))}</td><td class='n'>${r['all_in_psf']}</td>"
                   f"<td class='n'>{money(int(r['monthly_carry']))}</td><td class='n'>{money(int(r['wishlist_p80']))}</td><td class='n'>{r['tells_seen_of_15']}/15</td><td class='vd'>{r['evidence']}</td><td class='n'>{r['rank_low']}–{r['rank_high']}</td><td class='n'>{money(int(r['cash_to_close_20pct']))}</td>"
                   f"<td class='vd'>{esc(r['verdict'])}</td><td class='reno-col'>{esc(r['renovations_needed']) if r['renovations_needed'] != '-' else ''}</td><td>{esc(r['notes']) if r['notes'] != '-' else ''}</td></tr>")
    return "".join(out)

BODY = f"""<div class="wrap">

  <header class="mast">
    <p class="kicker">Halton search · walk-through companion · rebuilt 12 September 2026</p>
    <h1>Walking the Shortlist</h1>
    <p class="standfirst">Every house on both saved searches, {n} in all, ranked by what it actually costs rather than what it asks.
      Every one has now had its photos read at full resolution. Each card lists what the photos settled, what only a person standing in the room can
      settle, every room with its real dimensions, and every renovation line with what it costs and how likely it is to be needed.
      Each card also carries a <b>showing record</b>: open it in the house and answer the questions the model is still guessing at. Export when you get home and the ranking rebuilds on what you saw rather than what the era implies.</p>
    <div class="mast-meta">
      <span>{n} of {n} photo-graded</span>
      <span>{len(see_first)} marked See First</span>
      <span>Ranked by cost per usable sq ft</span>
      <span>Model v3.2</span>
    </div>
  </header>

  <div class="bar" id="whos">
    <div class="modes">
      <button type="button" class="m on" data-kind="mode" data-v="all">All {n}</button>
      <button type="button" class="m" data-kind="mode" data-v="todo">Not walked</button>
      <button type="button" class="m" data-kind="mode" data-v="seen">Walked</button>
      <button type="button" class="m" data-kind="mode" data-v="short">Shortlist</button>
    </div>
    <button type="button" class="exp" data-kind="export">Export notes</button>
    <span class="pill" id="syncpill"></span>
    <div class="who" id="whosw">
      <input type="text" id="who-a" data-kind="person" data-who="a" aria-label="First name">
      <input type="text" id="who-b" data-kind="person" data-who="b" aria-label="Second name">
      <button type="button" class="sw on" data-kind="who" data-who="a">Alex</button>
      <button type="button" class="sw" data-kind="who" data-who="b">Her</button>
    </div>
  </div>
  <div class="strip" id="strip"></div>
  <div class="expbox" id="expbox">
    <p style="margin:0;font-size:13.5px;color:var(--muted)">Everything you have recorded. Paste it back into the chat, or into
      <code>observations.json</code> via the <code>observations_patch</code> block, then run <code>refresh.sh</code> to re-rank on what you
      actually saw.</p>
    <textarea id="exptext" readonly></textarea>
  </div>

  <dl class="glossary">
    <div class="term"><dt>Day-one cash</dt>
      <dd>What has to be spent <b>before or at move-in</b>. Safety, insurability, and work that costs twice as much once the furniture is in.</dd></div>
    <div class="term"><dt>True cost</dt>
      <dd>Asking price <b>plus day-one cash</b>. Not the asking price plus everything you might ever want to do.</dd></div>
    <div class="term"><dt>Reserve / month</dt>
      <dd>The monthly set-aside for the <b>roof, furnace, A/C, water heater and windows</b>. Not a purchase cost, a running one. On the cards it is shown added to property tax.</dd></div>
    <div class="term"><dt>Wish list</dt>
      <dd>Kitchen, baths, basement, deck. <b>Your choice, your timing.</b> Deliberately kept out of the ranking.</dd></div>
  </dl>

  <p class="howto"><b>One rule behind all of this:</b> photos can only ever count against a house,
    never for it. A kitchen that looks immaculate in forty photos scores exactly the same as a kitchen
    with no photos at all. So the green column is only ever "no problem found", and the red column is
    the real agenda for the visit. <b>What changed on 12 September:</b> all {n} listings now have a full photo pass
    (only 11 did before), 13 listings from the second saved search were added, and the model now uses a build-year
    estimate when MLS gives none and counts a finished basement toward usable area even when MLS gives no size for it.</p>

  <div class="section-head">
    <h2>The whole table</h2>
    <p>All {n}, in rank order. Tells settled is how many of the 15 condition fields the photos actually answered. Rank band is where the house lands if the things nobody could see flip the other way (the basement estimate switched off, windows turning out original, a kitchen turning out to be a gut, floors needing replacing). A wide band means the rank is resting on assumptions rather than evidence; Enfield's 3 to 17 is the clearest case.</p>
  </div>
  <div class="tablewrap">
    <table class="big"><thead><tr><th class="n">#</th><th>House</th><th>Grade</th><th class="n">Ask</th><th class="n">Day one</th>
      <th class="n">$/sq ft</th><th class="n">Tax+res/mo</th><th class="n">Wish list</th><th class="n">Tells</th><th>Evidence</th><th class="n">Rank band</th><th class="n">Cash to close (20%)</th><th>Verdict</th><th>Renovations needed</th><th>Flags</th></tr></thead>
      <tbody>{table_rows()}</tbody></table>
  </div>

  <section class="calc">
    <div class="calc-head">
      <h2>What each one actually costs you</h2>
      <p>Put your own numbers in. Everything below recalculates, including Ontario land transfer tax and
        the first-time buyer rebate. Payments use the Canadian semi-annual compounding convention.</p>
    </div>
    <div class="controls">
      <div class="ctrl"><label for="dp">Down payment %</label>
        <input type="number" id="dp" value="20" min="5" max="100" step="1"></div>
      <div class="ctrl"><label for="rate">Interest rate %</label>
        <input type="number" id="rate" value="4.25" min="0.5" max="12" step="0.05"></div>
      <div class="ctrl"><label for="amort">Amortization yrs</label>
        <input type="number" id="amort" value="25" min="5" max="30" step="1"></div>
      <div class="ctrl ftb"><input type="checkbox" id="ftb" checked>
        <label for="ftb">First-time buyers</label></div>
    </div>
    <p id="cmhc-note">Under 20% down, mortgage default insurance applies and gets added to the loan.
      Confirm the premium and the maximum purchase price with your lender.</p>
    <div class="tablewrap">
      <table class="big" id="calctab">
        <thead><tr><th>House</th><th class="n">Ask</th><th class="n">Mortgage</th>
          <th class="n">Mortgage / mo</th><th class="n">Tax / mo</th><th class="n">Reserve / mo</th>
          <th class="n">Total / mo</th><th class="n">Land transfer</th><th class="n">Cash on closing day</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <div class="section-head">
    <h2>House by house</h2>
    <p>In rank order. Open "Renovation cost, line by line" on any card for the full build-up.</p>
  </div>

  <div class="lots" id="lots">
{''.join(cards)}
  </div>

  {TAIL}
  <p class="colophon">Ranked on true cost per usable square foot · usable = above grade + half the basement, 65% if it walks out; estimated at 70% of the footprint when MLS gives no basement size · Model v3.2, 12 September 2026 · {n} listings, all photo-graded · Nothing here is an offer price</p>

</div>

<script>
const HOUSES = {json.dumps(houses_js)};
const RESERVE = {json.dumps(reserve_js)};
{CALC_JS}
(function init(){{
  try{{
    const s = JSON.parse(localStorage.getItem("walk-shortlist-calc") || "null");
    if(s){{
      document.getElementById("dp").value = s.dp;
      document.getElementById("rate").value = s.rate;
      document.getElementById("amort").value = s.yrs;
      document.getElementById("ftb").checked = !!s.ftb;
    }}
  }}catch(e){{}}
  recalc();
  ["dp","rate","amort","ftb"].forEach(function(id){{
    document.getElementById(id).addEventListener("input", recalc);
    document.getElementById(id).addEventListener("change", recalc);
  }});
}})();
</script>
<script>
const SHOW_DATA = {{"houses": {json.dumps(show_js)}, "walk": {SH.tri_js()}}};
{SHOW_JS}
</script>
"""

src = STYLE + BODY
open(os.path.join(DEL, "walking-the-shortlist.artifact-src.html"), "w", encoding="utf-8").write(src)
standalone = "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n" + STYLE.replace("<title>", "<title>") + "</head><body style=\"margin:0;font:14px system-ui\">" + BODY + "</body></html>"
open(os.path.join(DEL, "Walking-the-Shortlist.html"), "w", encoding="utf-8").write(standalone)
print("wrote", len(src), "bytes;", n, "cards")
