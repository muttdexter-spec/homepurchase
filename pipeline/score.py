#!/usr/bin/env python3
"""First House v3.4 cost model, rank v6 (2026-09-12 review patch: Unfinished/Partial basement text, Walk-Up vs Walk-Out, concealed floors, unknown-year electrical, oil furnace double count) on v3.2 (2026-09-12: v3.1 + evidence grade, rank band, cash-to-close, HDR/tiny-bedroom rules, duplicate check). Costs by WHEN you pay, p80 on the sum, no ceilings, no gut band.
Usage: python3 score.py observations.json out/"""
import json, csv, os, sys, random, statistics as st
import yaml

R = os.path.dirname(os.path.abspath(__file__))
CFG = yaml.safe_load(open(os.path.join(R, "costs.yaml")))
CAT, NOW, N = CFG["catalog"], 2026, 4000
random.seed(7)

# ---------------------------------------------------------------- v6.1 §2: geocode cache
# pipeline/geo.json holds one entry per slug: lat, lon, the straight-line distance in metres to
# the nearest GO station, to the QEW / 403 / 407 / rail corridor, to the nearest park of 5 ha or
# more and to Lake Ontario, plus the street name and type. Its _meta block records the geocoder,
# the Overpass queries and the caveats. Built once; a rebuild does not re-query the web.
try:
    GEO = json.load(open(os.path.join(R, "geo.json")))
except Exception as _e:
    print(f"WARNING geo.json unreadable ({_e}); location falls back to v6", file=sys.stderr)
    GEO = {}

def pert(lo, ml, hi):
    """Beta-PERT draw. Standard construction-estimating distribution."""
    if hi <= lo: return ml
    u = random.random(); a, b = 1 + 4*(ml-lo)/(hi-lo), 1 + 4*(hi-ml)/(hi-lo)
    x = random.betavariate(a, b)
    return lo + x*(hi-lo)

def eff_year(o):
    """v3.1: year_built > year_built_est (neighbourhood/subdivision estimate, source noted in the
    record) > TRREB age band, taken at its OLDER end. Returns None only when nothing is known."""
    if o.get("year_built"): return o["year_built"]
    if o.get("year_built_est"): return o["year_built_est"]
    b = str(o.get("year_built_details") or "")
    import re
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)", b)
    if m: return NOW - int(m.group(2))
    m = re.match(r"\s*(\d+)\+", b)
    if m: return NOW - int(m.group(1))
    return None

STOREYS = {"Bungalow":1, "Bungalow-Raised":1, "Bungalow Raised":1, "Raised Bungalow":1, "1 1/2 Storey":1.5, "1.5 Storey":1.5, "Sidesplit":1.5,
           "Backsplit":1.5, "Two Storey":2, "2-Storey":2, "3-Storey":3}
def below_grade(o):
    """v3.1: stated below-grade area, else an ESTIMATE for a finished basement: 70% of the
    footprint (above grade / storeys). Marked so the report can say it is estimated."""
    if o.get("sqft_below"): return o["sqft_below"], False
    b = str(o.get("basement",""))
    # v3.4: "Unfinished" contains "inish"; match the word, and scale a partial finish down.
    if "Unfinished" in b or "Finished" not in b: return 0, False
    ag = o.get("sqft_above") or 0
    st = STOREYS.get(str(o.get("style","")).strip(), 1.5)
    f = CFG.get("below_grade_estimate_factor_partial", 0.35) if "Partially" in b else CFG.get("below_grade_estimate_factor", 0.70)
    if not f: return 0, False
    return round(f * ag / st), True

def era(yb): return "pre_1990" if not yb or yb < 1990 else ("y1990_2004" if yb < 2005 else "y2005_plus")
def cont(yb):
    c = CFG["contingency"]
    return c["pre_1980"] if (not yb or yb < 1980) else (c["y1980_1999"] if yb < 2000 else c["y2000_plus"])

FINISH_FIELDS = ["kitchen_sink_mount","kitchen_counter_edge","kitchen_soffit","kitchen_door_profile",
                 "bath_tub_type","bath_tile_scale","bath_vanity_top","floor_condition","ceiling_main",
                 "window_frame","basement_ceiling","basement_walls","basement_moisture","driveway"]
def normalise(o):
    """v3.2: rules that used to live only in the brief. (a) hdr_blowout: severe voids every finish
    read. (b) beds_effective: a bedroom under 60 sqft in the room table is not a bedroom for the
    layout score. Mutates a copy; the record on disk keeps what was observed."""
    o = dict(o)
    if o.get("hdr_blowout") == "severe":
        for f in FINISH_FIELDS:
            if o.get(f) not in (None, ""): o[f] = "not_shown"
        o["_hdr_voided"] = True
    if o.get("beds_effective") is None:
        tiny = 0
        for r in (o.get("rooms_raw") or []):
            try:
                lvl, name, sq = r[0], r[1], (r[2] if len(r) > 2 else None)
                if sq and sq < 60 and "bed" in str(name).lower() and not any(k in str(lvl).lower() for k in ("base","lower")): tiny += 1
            except Exception: pass
        o["beds_effective"] = max(0, (o.get("beds_ag") or 0) - tiny)
    return o

PHOTOS_MAY_LOWER_P = bool(CFG.get("condition", {}).get("photos_may_lower_p", True))

def prob(o, tells_seen, tells_total, defect, from_showing=False):
    """P(this job is needed). 1.0 if a defect was confirmed. Otherwise the era prior,
    pulled toward the floor by how much was actually observed at full resolution.

    v6 §3: with condition.photos_may_lower_p false, a photographic read no longer pulls the
    prior down at all and the rule is demote-only again, as v5 had it. A read taken at a
    showing (from_showing) always counts: a person standing in the room is not a photograph."""
    if defect: return 1.0
    p = CFG["p_not_done"][era(eff_year(o))]
    if not PHOTOS_MAY_LOWER_P and not from_showing: return p
    f = (tells_seen / tells_total) if tells_total else 0
    return p - (p - CFG["observed_floor"]) * f

def p_hold(age, life, H, confirmed_original=False):
    """v6 §3. P(this component is replaced during a hold of H years), from house age and
    component life. Younger than the life: original, remaining life known. Between one and one
    and a half lives: original and past due. Older: replaced at least once at an unknown date,
    so uniform over the cycle. A component confirmed original is 1.0 regardless.

    life <= 1 is an annual carry (the pool), not a component: it is paid H times over the hold."""
    if life <= 1: return float(H)
    if confirmed_original: return 1.0
    if age <= life: return min(1.0, H / max(1, life - age))
    if age <= 1.5 * life: return 1.0
    return min(1.0, H / life)

SEEN_FIELD = {"roof": "roof_seen", "furnace": "furnace_seen", "A/C": "ac_seen",
              "water heater": "water_heater_seen", "panel": "panel_seen"}
def parse_seen(v):
    """v6 §7 item 3. The showing record writes 'original', 'replaced_<year>' or 'new'.
    Anything else in these fields is free text from an earlier pass: ignored, never guessed at.
    Returns (kind, year) or None."""
    import re as _re
    s = str(v or "").strip().lower()
    if s == "original": return ("original", None)
    if s == "new": return ("new", None)
    m = _re.match(r"replaced[_ -]?(\d{4})$", s)
    if m: return ("replaced", int(m.group(1)))
    return None

def _floor_concealed(o):
    """v3.4: concealed_surfaces mentions a floor covering. Photos may not pull the floor line to the observed floor."""
    import re
    return bool(re.search(r"floor|rug|carpet|\bmat\b|runner", " ".join(o.get("concealed_surfaces") or []), re.I))

def pool_kind(o):
    """v6. One pool reading, shared by cost() and verdict(). The listing's own remarks win over
    the stage-2 `pool` field when they say in-ground and the field does not: Oxlow's field reads
    'above-ground' while its remarks read 'in-ground pool (new liner 2025)'. Recorded as a data
    conflict in QA-PASS-2026-09-14; the field should be corrected at the next stage-2 pass."""
    import re as _re
    if _re.search(r"in-?ground (swimming )?pool", str(o.get("remarks", "")).lower()):
        return "in-ground"
    return o.get("pool")

def cost(o):
    # Seed per listing so decision.csv, detail.json and the page all show the same draw,
    # whatever order the callers run in.
    random.seed(sum(ord(c) for c in o.get("slug","")) * 7919 + 7)
    yb, ag = eff_year(o), o.get("sqft_above") or 0
    age = NOW - yb if yb else 60
    items = []   # (name, bucket, p_needed, lo, ml, hi, basis)

    def add(name, key, p, basis, mult=1.0):
        c = CAT[key]
        items.append((name, c["bucket"], p, c["low"]*mult, c["likely"]*mult, c["high"]*mult, basis))

    # ---- kitchen (wishlist) -------------------------------------------------
    kt = ["kitchen_sink_mount","kitchen_counter_edge","kitchen_soffit","kitchen_door_profile"]
    kseen = sum(1 for f in kt if o.get(f) not in (None,"","not_shown"))
    boxes_new = bool(o.get("kitchen_boxes_new"))
    soffit_bad = o.get("kitchen_soffit")=="present" and not boxes_new
    kbad  = (o.get("kitchen_verdict")=="defect_confirmed" or o.get("kitchen_sink_mount")=="topmount"
             or o.get("kitchen_counter_edge")=="rolled_bullnose" or soffit_bad
             or o.get("kitchen_door_profile")=="soft_raised_panel")
    # v3.3 SHOWING RECORD. An in-person read may PROMOTE as well as demote. The photos-demote rule
    # stands for photos, which are unreliable evidence; a person standing in the room is not.
    ksrc = ""
    if o.get("kitchen_seen") == "done":   kseen, kbad, ksrc = 4, False, " (seen done at the showing)"
    elif o.get("kitchen_seen") == "redo": kbad, ksrc = True, " (seen original at the showing)"
    # A dated-but-functional kitchen is a COSMETIC job unless the boxes are shot.
    # v3.1: a retained bulkhead over NEW boxes (kitchen_boxes_new) is not a gut signal.
    add("kitchen","kitchen_full" if (kbad and soffit_bad) else "kitchen_cosmetic",
        prob(o,kseen,4,kbad,from_showing=bool(o.get("kitchen_seen"))), f"{kseen}/4 tells seen, defect={kbad}" + ksrc)

    # ---- baths (wishlist) ---------------------------------------------------
    nf, nh = o.get("baths_full") or 0, o.get("baths_half") or 0
    bt = ["bath_tub_type","bath_tile_scale","bath_vanity_top"]
    bseen = sum(1 for f in bt if o.get(f) not in (None,"","not_shown"))
    bbad = (o.get("bath_verdict")=="defect_confirmed" or o.get("bath_tub_type")=="corner_garden_platform"
            or o.get("bath_tile_scale") in ("small_4x4","12x12_wide_grout")
            or o.get("bath_vanity_top") in ("integrated_cultured_marble","laminate_dropin"))
    bsrc = ""
    if o.get("bath_seen") == "done":   bseen, bbad, bsrc = 3, False, " (seen done at the showing)"
    elif o.get("bath_seen") == "redo": bbad, bsrc = True, " (seen original at the showing)"
    if nf: add("main bath","bath_main_full", prob(o,bseen,3,bbad,from_showing=bool(o.get("bath_seen"))), f"{bseen}/3 tells seen" + bsrc)
    for i in range(max(0,nf-1)):
        # v3.1: a secondary bath CONFIRMED original in the photo pass is priced at p=1.0
        sec_bad = bool(o.get("secondary_bath_original")) and i == 0
        if o.get("secondary_bath_seen") == "done":
            add(f"bath {i+2}","bath_secondary", prob(o,3,3,False,from_showing=True), "seen done at the showing")
        else:
            add(f"bath {i+2}","bath_secondary", prob(o,0,3,sec_bad), "confirmed original" if sec_bad else "unobserved")
    if nh: add("powder","bath_powder", prob(o,0,3,False), f"{nh} half", mult=nh)

    # ---- flooring + ceilings (day1) -----------------------------------------
    fc = o.get("floor_condition")
    fseen = 1.0 if fc=="no_defect_seen" else 0.0
    if fseen and _floor_concealed(o): fseen = CFG.get("concealed_floor_read", 0.5)     # v3.4: rug / mat / runner noted over the floor: a partial read only
    add("flooring","flooring_per_sqft",
        prob(o,fseen,1, fc in ("uneven_stain","patch_visible","gaps_at_base")),
        f"floor={fc}" + (" (partly concealed)" if fseen==0.5 else ""), mult=ag)
    cm = o.get("ceiling_main")
    add("ceilings","ceilings_per_sqft",
        prob(o,1 if cm=="flat_painted" else 0,1, cm in ("stipple_popcorn","drop_tile")),
        f"ceiling={cm}", mult=ag)

    # ---- basement (wishlist) ------------------------------------------------
    bg, _bg_est = below_grade(o)
    if bg:
        bdef = o.get("basement_ceiling")=="drop_tile" or o.get("basement_walls") in ("bare_block","panelling")
        seen = sum(1 for f in ("basement_ceiling","basement_walls") if o.get(f) not in (None,"","not_shown"))
        bsrc = ""
        if o.get("basement_seen") == "done":   seen, bdef, bsrc = 2, False, " (seen finished at the showing)"
        elif o.get("basement_seen") == "redo": bdef, bsrc = True, " (seen needing work at the showing)"
        add("basement","basement_per_sqft", prob(o,seen,2,bdef,from_showing=bool(o.get("basement_seen"))), f"{bg} sqft bg" + bsrc, mult=min(bg,900))

    # ---- reserve components (age-driven, NOT a purchase cost) ---------------
    # v6: every reserve line now carries its own (age, life, confirmed_original) so that p_hold()
    # can say how likely it is to be replaced DURING the hold. Before v6 the reserve was a flat
    # annuity, which charged a confirmed-original window 1/30 of its cost a year for thirty years.
    res_meta = {}                      # name -> (age, life, confirmed_original)
    metal_roof = "metal" in (str(o.get("roof_material",""))+str(o.get("roof_visual",""))).lower()
    oil_heat = "oil" in str(o.get("heating","")).lower()
    for nm,key in [("roof","roof"),("furnace","furnace"),("A/C","ac"),("water heater","water_heater")]:
        if nm=="furnace" and oil_heat: continue                 # v3.4: oil_to_gas already includes the furnace
        p_res = 0.3 if (nm=="roof" and metal_roof) else 1.0   # v3.1: metal roof, 50y life
        life = CAT[key]["life"]; a = age; conf = False
        basis = "metal roof in MLS/photo, long life" if p_res<1 else f"life {life}y, age unstated"
        sn = parse_seen(o.get(SEEN_FIELD[nm]))
        if sn:                                                  # v6 §7 item 3: the showing record wins
            kind, yr = sn
            if kind == "replaced": a, basis = max(0, NOW - yr), f"life {life}y, replaced {yr} (showing record)"
            elif kind == "new":    a, basis = 0, f"life {life}y, new (showing record)"
            else:                  conf, basis = True, f"life {life}y, ORIGINAL confirmed at the showing"
        res_meta[nm] = (a, life, conf)
        items.append((nm,"reserve",p_res,CAT[key]["low"],CAT[key]["likely"],CAT[key]["high"],basis))
    wf = o.get("window_frame")
    if wf in ("aluminum_original","wood_original","original"):
        res_meta["windows"] = (age, CAT["windows_full"]["life"], True)
        items.append(("windows","reserve",1.0,*[CAT["windows_full"][k] for k in("low","likely","high")],
                      f"{wf} CONFIRMED — near term"))
    elif wf != "vinyl":
        res_meta["windows"] = (age, CAT["windows_full"]["life"], False)
        items.append(("windows","reserve",CFG["p_not_done"][era(yb)],
                      *[CAT["windows_full"][k] for k in("low","likely","high")],"frame not shown"))

    # v6 §7 item 4: an in-ground pool has an annual carry. Priced, not only flagged. The POOL
    # HOLD stamp is unaffected: this line is the money, the stamp is the warning.
    if pool_kind(o) == "in-ground":
        pc = CFG["reserve"]["pool_carry_annual"]
        res_meta["pool carry"] = (1, pc.get("life", 1), False)
        items.append(("pool carry","reserve",1.0,pc["low"],pc["likely"],pc["high"],"in-ground pool, annual carry"))

    # ---- day1 hazards -------------------------------------------------------
    # v6 §7 item 3: panel_seen from the showing record overrides the era block entirely.
    # 'new' or 'replaced_<year>' means somebody looked at the service and it is not a fuse box.
    _panel_seen = parse_seen(o.get("panel_seen"))
    if _panel_seen and _panel_seen[0] in ("new", "replaced"):
        pass
    elif _panel_seen and _panel_seen[0] == "original" and (not yb or yb < 1970):
        add("panel","panel_upgrade",1.0,"original service confirmed at the showing")
        add("rewire","rewire_knob_tube",1.0,"original pre-1970 service implies K&T")
    elif not yb or yb < 1970:   # v3.4: unknown year is worst case here as everywhere else
        pt = o.get("panel_type")
        if pt == "fuse":
            add("panel","panel_upgrade",1.0,"fuse panel confirmed")
            add("rewire","rewire_knob_tube",1.0,"fuse panel implies K&T")
        elif pt in (None,"","not_shown"):
            add("panel","panel_upgrade",0.5,"pre-1970, panel not shown")
            add("partial rewire","rewire_knob_tube",0.25,"pre-1970 risk", mult=0.4)
    if "oil" in str(o.get("heating","")).lower():
        add("oil→gas","oil_to_gas",1.0,"oil heat in MLS")
        add("tank removal","oil_tank_removal",1.0,"LIABILITY IF BURIED — uncapped")
    if o.get("asbestos_suspect") and (yb or 9999) < 1990:
        add("asbestos","asbestos_abatement",0.6,"suspect material, only if disturbed")
    bm, mc = o.get("basement_moisture"), o.get("moisture_confidence","medium")
    moist = bm in ("efflorescence","staining") and mc in ("medium","high")
    if moist: add("waterproofing","waterproofing",1.0,"moisture CONFIRMED")
    elif bm in ("efflorescence","staining"): add("waterproofing","waterproofing",0.4,"moisture suspected, low conf")
    elif bg: add("waterproofing","waterproofing",0.12,"below-grade base rate")
    if o.get("driveway")=="cracked": add("driveway","driveway",1.0,"cracked, confirmed")

    # ---- SIMULATE. p80 of the SUM, not the sum of p80s. ---------------------
    k = 1 + cont(yb)
    sims = {"day1": [], "wishlist": []}
    for _ in range(N):
        acc = {"day1":0.0,"wishlist":0.0}
        nrooms = 0
        for nm,b,p,lo,ml,hi,_bs in items:
            if b == "reserve": continue
            if random.random() < p:
                acc[b] += pert(lo,ml,hi); nrooms += 1
        acc["day1"] += pert(*[CFG["soft_costs_day1"][x] for x in ("low","likely","high")])
        prem = 1 + (CFG["multi_room_premium"] if nrooms >= CFG["multi_room_threshold"] else 0)
        sims["day1"].append(acc["day1"] * k * prem * (1+CFG["meta"]["hst"]))
        sims["wishlist"].append(acc["wishlist"] * k * prem * (1+CFG["meta"]["hst"]))

    def pc(v,q): s=sorted(v); return s[int(q*len(s))]
    # reserve: true long-run cost of ownership, annualised
    res_yr = sum(p*((lo+4*ml+hi)/6)/max(1, res_meta.get(nm,(age,20,False))[1]) for nm,b,p,lo,ml,hi,_ in items if b=="reserve")
    near = sum(p*((lo+4*ml+hi)/6) for nm,b,p,lo,ml,hi,_ in items
               if b=="reserve" and res_meta.get(nm,(age,20,False))[0] > res_meta.get(nm,(age,20,False))[1])
    return {
        "items": items,
        "reserve_meta": res_meta,
        "day1_p50": round(pc(sims["day1"],.50)), "day1_p80": round(pc(sims["day1"],.80)),
        "wish_p50": round(pc(sims["wishlist"],.50)), "wish_p80": round(pc(sims["wishlist"],.80)),
        "naive_sum_of_p80s": round(sum(p*hi for _,b,p,lo,ml,hi,_x in items if b!="reserve")*k*(1+CFG["meta"]["hst"])),
        "reserve_monthly": round(res_yr*(1+CFG["meta"]["hst"])/12),
        "near_term_5yr": round(near*(1+CFG["meta"]["hst"])),
        "moisture_confirmed": moist,
    }

def usable(o):
    ag=o.get("sqft_above") or 0; bg,_=below_grade(o)
    b=str(o.get("basement",""))
    w=CFG["below_grade_weight_walkout"] if ("Walk-Out" in b or "Walkout" in b) else CFG["below_grade_weight"]   # v3.4: a Walk-Up is stairs, not daylight
    return ag + w*bg

REC = {"kitchen":"kitchen","main bath":"bath","powder":"bath","flooring":"flooring",
       "ceilings":"paint","basement":"basement","driveway":"driveway","panel":"remediation",
       "rewire":"remediation","partial rewire":"remediation","oil\u2192gas":"hvac",
       "tank removal":"remediation","asbestos":"remediation","waterproofing":"remediation"}
def rec_key(nm):
    if nm.startswith("bath "): return "bath"
    return REC.get(nm,"flooring")

def resale(o,c):
    """ARV = list + value added by the work, capped at what a RENOVATED house of this
    size trades for in the pocket. Returns a BAND, because recovery is a band."""
    R=CFG["recovery"]; K=CFG["conformity"]
    muni=o.get("municipality") or "Burlington"
    psf=CFG["arv_psf_renovated"].get(muni,CFG["arv_psf_renovated"]["Burlington"])["value"]
    norm = psf*usable(o)                       # renovated peer value
    headroom = max(0.0, norm - o["list_price"])
    # scale line-item means up to the p80 planning number so ARV uses planning dollars
    means={}
    for nm,b,p,lo,ml,hi,_ in c["items"]:
        if b=="reserve": continue
        means[nm]=means.get(nm,0)+p*((lo+4*ml+hi)/6)
    tot=sum(means.values()) or 1
    scale=(c["day1_p80"]+c["wish_p80"])/(tot*(1+CFG["meta"]["hst"]))
    lo_add=hi_add=spent=0.0
    for nm,amt in sorted(means.items(), key=lambda kv:-R[rec_key(kv[0])]["high"]):
        a=amt*scale
        w=max(0.0,min(a,headroom-spent)); byd=a-w; r=R[rec_key(nm)]
        lo_add += w*r["low"]*K["within_norm"] + byd*r["low"]*K["past_norm"]
        hi_add += w*r["high"]*K["within_norm"] + byd*r["high"]*K["past_norm"]
        spent += a
    # the one intervention that can exceed 100%: a 2nd full bath in a 3+ bed, 1-bath home
    bath_op=None
    if (o.get("baths_full") or 0)<=1 and (o.get("beds_ag") or 0)>=3:
        cost2=CAT["bath_secondary"]["likely"]*(1+CFG["meta"]["hst"])
        r=R["second_bath"]; bath_op=(round(cost2), round(cost2*r["low"]), round(cost2*r["high"]))
    spend=c["day1_p80"]+c["wish_p80"]
    mid=(lo_add+hi_add)/2
    return {"arv_lo":round(min(o["list_price"]+lo_add,norm)),
            "arv_mid":round(min(o["list_price"]+mid,norm)),
            "arv_hi":round(min(o["list_price"]+hi_add,norm)),
            "norm":round(norm),"headroom":round(headroom),
            "recovered_pct":round(100*mid/spend) if spend else 0,
            "sunk":round(spend-mid),"breakeven":round(o["list_price"]+spend),
            "bath_op":bath_op,"usable":round(usable(o))}

TELLS = ["kitchen_sink_mount","kitchen_counter_edge","kitchen_soffit","kitchen_door_profile","bath_tub_type",
         "bath_tile_scale","bath_vanity_top","floor_condition","ceiling_main","window_frame","panel_type",
         "basement_ceiling","basement_walls","basement_moisture","driveway"]
_LIFE = {"roof":"roof","furnace":"furnace","A/C":"ac","water heater":"water_heater","windows":"windows_full"}
def CAT_life(nm, default=20):
    """v6: reserve lines are no longer only the five catalog components; the pool carry is one too."""
    if nm in _LIFE: return CAT[_LIFE[nm]]["life"]
    if nm == "pool carry": return CFG["reserve"]["pool_carry_annual"].get("life", 1)
    return default

# ------------------------------------------------------------------ fit (v5)
def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))

def basement_flags(o):
    """MLS basement text only. No estimated area enters the fit score (review 2.3)."""
    b = str(o.get("basement") or "")
    finished = ("Finished" in b) and ("Unfinished" not in b) and ("Partially" not in b)
    partial = "Partially" in b
    sep = any(k in b for k in ("Separate","Walk-Out","Walkout","Walk-Up","Apartment"))   # exterior access = suite potential
    return finished, partial, sep

def space_pts(o):
    """v5: above-grade area saturating at the knee, plus the basement as a discrete amenity."""
    sp = CFG["fit_weights"]["space"]
    ag = o.get("sqft_above") or 0
    pts  = sp["pts_to_knee"] * clamp((ag - sp["floor_sqft"]) / (sp["knee_sqft"] - sp["floor_sqft"]))
    pts += sp["pts_knee_to_cap"] * clamp((ag - sp["knee_sqft"]) / (sp["cap_sqft"] - sp["knee_sqft"]))
    fin, part, sep = basement_flags(o)
    pts += sp["basement_finished"] if fin else (sp["basement_partial"] if part else 0)
    pts += sp["basement_exterior_access"] if sep else 0
    return min(sp["pts"], pts)

def _kitchen_full(o):
    boxes_new = bool(o.get("kitchen_boxes_new"))
    soffit_bad = o.get("kitchen_soffit") == "present" and not boxes_new
    kbad = (o.get("kitchen_verdict") == "defect_confirmed" or o.get("kitchen_sink_mount") == "topmount"
            or o.get("kitchen_counter_edge") == "rolled_bullnose" or soffit_bad
            or o.get("kitchen_door_profile") == "soft_raised_panel")
    return bool(kbad and soffit_bad)

def condition_demote(o, c):
    """v5: demote only, and only on a line the cost model puts at p >= 0.95 (CONFIRMED at full
    resolution). A clean photo or an unseen surface is 0. Scaled by era. Returns (points, why)."""
    cd = CFG["fit_weights"]["condition_demote"]; dem = 0; why = []
    items = {nm: (b, p, bs) for nm, b, p, lo, ml, hi, bs in c["items"]}
    if "kitchen" in items and items["kitchen"][1] >= 0.95:
        d = cd["kitchen_full"] if _kitchen_full(o) else cd["kitchen_cosmetic"]
        dem += d; why.append(f"kitchen original -{d}")
    if "main bath" in items and items["main bath"][1] >= 0.95:
        dem += cd["main_bath"]; why.append(f"main bath original -{cd['main_bath']}")
    if "bath 2" in items and items["bath 2"][1] >= 0.95:
        dem += cd["secondary_bath"]; why.append(f"2nd bath original -{cd['secondary_bath']}")
    dem = min(dem, cd["cap"]) * cd["era_scale"][era(eff_year(o))]
    return round(dem, 1), why

def _ramp(v, zero, full):
    """0 at `zero`, 1 at `full`, linear between, clamped. Works in either direction."""
    if zero == full: return 1.0
    return clamp((v - zero) / (full - zero))

def location_parts(o):
    """v6.1 §2. Five parts on absolute anchors, each 0 to 1, returned with their point values so
    the card can show the breakdown. Returns (parts, total_0_100, estimated_flags).

    Every distance is straight line, from pipeline/geo.json. Where a part cannot be computed it
    scores its midpoint and names itself in the returned flags, which is what puts the
    `Location partly estimated` stamp on the card."""
    L = CFG["location"]; P = L["parts"]
    g = GEO.get(o.get("slug")) or {}
    parts, flags = {}, []

    def part(key, frac, detail):
        parts[key] = {"frac": round(frac, 4), "pts": round(P[key]["pts"] * frac, 2),
                      "max": P[key]["pts"], "detail": detail}

    # --- commute: nearest of the five Lakeshore West GO stations
    if g.get("go_m") is not None:
        f = _ramp(g["go_m"], P["commute"]["zero_m"], P["commute"]["full_m"])
        part("commute", f, f"{g['go_m']/1000:.1f} km to {g.get('go')} GO")
    else:
        part("commute", 0.5, "GO distance unknown, midpoint"); flags.append("commute")

    # --- quiet: distance to the NEAREST of the QEW, 403, 407 and the rail corridor, then the
    #     street type, then the arterial cap. Minimum over the line features, not a sum: what
    #     makes a street loud is the nearest source of noise, not how many there are.
    ds = [g.get(k) for k in ("qew_m", "h403_m", "h407_m", "rail_m") if g.get(k) is not None]
    if ds:
        near = min(ds)
        f = _ramp(near, P["quiet"]["zero_m"], P["quiet"]["full_m"])
        st_type = (g.get("street_type") or "")
        calm = st_type in L["quiet_street_types_calm"]
        if calm: f = min(1.0, f + L["quiet_street_bonus"])
        arterial = (g.get("street") or "") in set(L.get("arterials") or [])
        if arterial: f = min(f, L["quiet_arterial_cap"])
        bits = [f"{near}m to the nearest of the QEW, 403, 407 or the rail"]
        if calm: bits.append(st_type.lower())
        if arterial: bits.append("on an arterial")
        part("quiet", f, ", ".join(bits))
    else:
        part("quiet", 0.5, "highway and rail distances unknown, midpoint"); flags.append("quiet")

    # --- walk and transit: unchanged from v6
    wt = (o.get("walk") or 0) + (o.get("transit") or 0)
    part("walk", _ramp(wt, P["walk"]["zero"], P["walk"]["full"]), f"walk {o.get('walk')} + transit {o.get('transit')} = {wt}")

    # --- school: distance half from the record; the assigned school and its Fraser rating have
    #     not been looked up, so the rating half sits at its midpoint.
    km = o.get("nearest_school_km")
    if km is None:
        part("school", 0.5, "no school distance on file, midpoint"); flags.append("school")
    else:
        d = _ramp(km, P["school"]["zero_km"], P["school"]["full_km"])
        if L.get("assigned_school_done"):
            part("school", d, f"nearest school {km} km")
        else:
            m = L["school_rating_midpoint"]
            part("school", 0.5*d + 0.5*m, f"nearest school {km} km, rating not looked up")

    # --- green and lake: the NEARER of the shore and any park of 5 ha or more. "Shore" is
    #     Lake Ontario including Burlington Bay; see geo.json _meta.features.lake_m.
    gs = [g.get("lake_m"), g.get("park_m")]
    gs = [x for x in gs if x is not None]
    if gs:
        near = min(gs)
        which = "the water" if g.get("lake_m") == near else (g.get("park") or "a park")
        part("green", _ramp(near, P["green"]["zero_m"], P["green"]["full_m"]), f"{near}m to {which}")
    else:
        part("green", 0.5, "lake and park distances unknown, midpoint"); flags.append("green")

    total = sum(p["pts"] for p in parts.values())
    return parts, round(min(100.0, max(0.0, total)), 1), flags

def facts(o, c=None):
    """v5 fit: absolute 0-100, facts only, no price. Same component maxima as v3
    (25/20/20/15/12/8) so the grade bands stay comparable. Condition subtracts, never adds."""
    w, p = CFG["fact_weights"], {}
    p["space"] = space_pts(o)
    p["layout"], _lay_est = layout_pts(o)             # v6.1 §5 Q4
    nf,nh = o.get("baths_full") or 0, o.get("baths_half") or 0
    p["baths"] = min(w["baths"]["pts"], {0:0,1:5,2:13,3:18}.get(nf,20) + (2 if nh else 0))
    lot = (o.get("lot_frontage_ft") or 0)*(o.get("lot_depth_ft") or 0)
    _L = CFG.get("lot") or {}                          # v6.1 §5 Q3
    if _L and not _L.get("matters", True):
        p["lot"] = w["lot"]["pts"] * 0.50              # yard does not matter: fixed at 50 for every house
    else:
        _f = _L.get("floor_sqft", w["lot"]["floor_sqft"]); _c = _L.get("cap_sqft", w["lot"]["ceiling_sqft"])
        p["lot"] = w["lot"]["pts"]*max(0,min(1,(lot-_f)/(_c-_f)))
    if (CFG.get("location") or {}).get("version") == "v61":
        _lp, _l100, _lflags = location_parts(o)          # v6.1 §2
        p["location"] = w["location"]["pts"] * _l100 / 100.0
    else:
        p["location"] = min(w["location"]["pts"], ((o.get("walk") or 0)+(o.get("transit") or 0))/15
                            + (4 if (o.get("nearest_school_km") or 9) < .5 else 2))
    p["parking"] = min(w["parking"]["pts"], (o.get("garage_spaces") or 0)*3 + (o.get("parking_spots") or 0))
    s = sum(p.values())
    if "plit" in str(o.get("style","")): s *= CFG["split_dock"]
    dem, why = condition_demote(o, c if c is not None else cost(o))
    p["condition"] = -dem
    return round(max(0.0, s - dem), 1), p

def grade(s):
    for L,f in sorted(CFG["grade_bands"].items(), key=lambda kv:-kv[1]):
        if s >= f: return L
    return "D"

def verdict(o,c,fs):
    stops,warns = [],[]
    if c["moisture_confirmed"]: stops.append("basement moisture confirmed")
    if any(n=="rewire" and p==1.0 for n,b,p,*_ in c["items"]): stops.append("knob-and-tube implied")
    if any(n=="tank removal" for n,*_ in c["items"]): warns.append("OIL TANK — buried? uncapped liability")
    if c["day1_p80"] > CFG["verdict"]["day1_share_warn"]*o["list_price"]:
        warns.append(f'day-1 cash {c["day1_p80"]/o["list_price"]:.0%} of list')
    import re as _re
    rm = str(o.get("remarks","")).lower()
    if pool_kind(o) == "in-ground": warns.append("POOL — in-ground, annual carry priced in the reserve")
    if o.get("tenanted") or _re.search(r"\btenant|currently rented", rm): warns.append("TENANTED")
    if o.get("staging")=="virtually_staged": warns.append("virtually staged frames")
    if any(n=="rewire" and p==1.0 for n,b,p,*_ in c["items"]): pass
    if stops: return "STOP", stops+warns
    if grade(fs) in ("A","A-","B+","B") and not warns: return "SEE FIRST", warns
    return "SEE", warns

def evidence(o):
    """v3.2: how much of this row rests on observation. Returns (label, tells, reason)."""
    tells = sum(1 for f in TELLS if o.get(f) not in (None,"","not_shown"))
    photos = o.get("photos_total") or (o.get("coverage") or {}).get("photos_total") or 0
    why = []
    if o.get("_hdr_voided"): why.append("HDR severe, finish reads voided")
    if photos and photos < 25: why.append(f"only {photos} photos")
    if o.get("basement_ceiling") == "not_shown" and o.get("basement_walls") == "not_shown": why.append("no basement frame")
    if o.get("staging") == "virtually_staged": why.append("virtual staging")
    if not o.get("year_built"): why.append("build year estimated")
    if not o.get("sqft_below") and below_grade(o)[1]: why.append("basement area estimated")
    label = "high" if tells >= 12 and len(why) <= 1 else ("medium" if tells >= 9 and len(why) <= 3 else "low")
    return label, tells, "; ".join(why)

def cash_to_close(price, day1, dp=0.20, extras=3500):
    """Mirrors the page calculator at 20% down, first-time-buyer rebate, $3,500 closing extras."""
    bands=[(55000,.005),(250000,.01),(400000,.015),(2000000,.02),(10**12,.025)]
    t=0; prev=0
    for cap,rate in bands:
        if price<=prev: break
        t += (min(price,cap)-prev)*rate; prev=cap
    ltt = t - min(4000, t)
    return round(price*dp + ltt + extras + day1)

# ---- RENOVATION LIST: the plain-English "what needs doing and roughly what it costs" -----
# One line per job that is confirmed (p>=0.95) or likely (p>=0.5; 'unseen' when the p is the era base rate), priced at the cost IF DONE
# (PERT mean x era contingency x HST), rounded to the nearest $1k. Possible jobs (0.15<p<0.5)
# are listed separately. Reserve items (roof, furnace...) are excluded: they are the monthly figure.
def reno_list(o, c):
    k = 1 + cont(eff_year(o)); hst = 1 + CFG["meta"]["hst"]
    out = []
    for nm,b,p,lo,ml,hi,bs in c["items"]:
        if b == "reserve" or p < 0.2: continue
        cost = round(((lo+4*ml+hi)/6)*k*hst/1000)*1000
        seen = any(x in bs for x in ("tells seen","=","confirmed","sqft"))
        st = "confirmed" if p >= 0.95 else ("likely" if seen else "likely, unseen") if p >= 0.5 else "possible"
        out.append({"name": nm, "bucket": b, "p": round(p,2), "cost": cost, "status": st})
    out.sort(key=lambda i: (0 if i["status"]=="confirmed" else 1 if i["status"].startswith("likely") else 2, -i["cost"]))
    return out

def reno_text(items):
    needed = [i for i in items if i["status"] != "possible"]
    txt = "; ".join(f"{i['name']} ${i['cost']//1000}k" + (" (unseen)" if i["status"]=="likely, unseen" else "") for i in needed)
    return txt or "-", sum(i["cost"] for i in needed)

def dedupe_warnings(obs):
    import re
    seen = {}; warns = []
    for o in obs:
        k = re.sub(r"[^a-z0-9]", "", str(o.get("address","")).lower().split(",")[0])
        if k in seen: warns.append(f"DUPLICATE: {o['slug']} and {seen[k]} share an address; keep one record and note the other board's ID in alt_listing_ids")
        seen[k] = o["slug"]
    return warns

# ================================================== rank v5: money, gates, frontier
# Review 2026-09-12 sections 3.1 to 3.4. Config lives in costs.yaml under hold / gates /
# fit_weights / rank. Nothing here uses an ask-derived resale number.

def day1_recovery(o, c):
    """Expected-spend-weighted AIC mid recovery over the day-1 lines, with NO conformity cap
    (the cap is the ask-derived part of resale()). Fraction in [0,1], typically 0.45 to 0.55."""
    Rr = CFG["recovery"]; num = den = 0.0
    for nm,b,p,lo,ml,hi,_ in c["items"]:
        if b != "day1": continue
        m = p*(lo + 4*ml + hi)/6; r = Rr[rec_key(nm)]
        num += m*(r["low"] + r["high"])/2; den += m
    return (num/den) if den else 0.5

def ltt_net(price):
    """Land transfer tax net of the first-time-buyer rebate, no down payment, no extras."""
    return cash_to_close(price, 0, dp=0.0, extras=0)

def cost_of_capital():
    """v6, USABILITY-SPEC §2. Derived, never a free key: the ranking's price component and the
    page's monthly payment now come from one rate by construction. At 20% down, 4.25% and 3%
    this is 0.040, the number v5 asserted."""
    HH = CFG["hold"]; d = HH["down_payment"]
    return (1 - d)*HH["mortgage_rate"] + d*HH["opportunity_rate"]

COST_OF_CAPITAL = cost_of_capital()

def reserve_over_hold(c, H):
    """v6 §3. The reserve term of the hold cost, component by component, at p_hold. Replaces the
    flat annuity, which charged a confirmed-original window 1/30 of its cost a year for thirty
    years and so never let it reach the money (review 5.7)."""
    hst = 1 + CFG["meta"]["hst"]; meta = c.get("reserve_meta", {}); tot = 0.0
    for nm,b,p,lo,ml,hi,_ in c["items"]:
        if b != "reserve": continue
        a, life, conf = meta.get(nm, (60, CAT_life(nm), False))
        tot += p * p_hold(a, life, H, conf) * ((lo + 4*ml + hi)/6) * hst
    return tot

def own_cost(o, c, day1, H):
    """Hold-period cost of ownership: zero appreciation, price back at exit (the neutral
    assumption when resale is not trusted). Returns (total over H years, parts)."""
    HH = CFG["hold"]; r, comm = COST_OF_CAPITAL, HH["exit_commission"]
    ask = o["list_price"]; taxes = o.get("annual_taxes") or 0
    rec = day1_recovery(o, c)
    parts = {
      "day1_sunk": (1 - rec)*day1,
      "capital":   (r*H)*(ask + day1) + comm*ask,
      "taxes":     H*taxes,
      "reserve":   reserve_over_hold(c, H),
      "closing":   ltt_net(ask) + HH["closing_extras"],
    }
    return sum(parts.values()), parts

def day1_draws(o):
    """The day-1 simulation exactly as cost() runs it (same seed, same order of random calls),
    returning the vector of draws so the rank band uses the model's own uncertainty."""
    c = cost(o)                                     # sets the per-listing seed, builds items
    random.seed(sum(ord(ch) for ch in o.get("slug","")) * 7919 + 7)
    yb = eff_year(o); k = 1 + cont(yb); out = []
    for _ in range(N):
        acc = {"day1":0.0,"wishlist":0.0}; nrooms = 0
        for nm,b,p,lo,ml,hi,_bs in c["items"]:
            if b == "reserve": continue
            if random.random() < p: acc[b] += pert(lo,ml,hi); nrooms += 1
        acc["day1"] += pert(*[CFG["soft_costs_day1"][x] for x in ("low","likely","high")])
        prem = 1 + (CFG["multi_room_premium"] if nrooms >= CFG["multi_room_threshold"] else 0)
        out.append(acc["day1"] * k * prem * (1+CFG["meta"]["hst"]))
    return c, out

def monthly_payment(o, c):
    """v6.1 §3. The page's Monthly payment at the costs.yaml financing defaults: principal and
    interest on the mortgage, plus property tax, plus the upkeep reserve. This is the ONE "/mo"
    number, and the price component, the page calculator and the ceiling all read it, so they
    agree by construction."""
    HH = CFG["hold"]
    principal = o["list_price"] * (1 - HH["down_payment"])
    # Canadian mortgages compound SEMI-ANNUALLY, not monthly. This is the page's own pAndI()
    # formula, character for character, because the model's payment and the page's payment must
    # be the same number: the cost penalty, the calculator and the ceiling all read it. A simple
    # monthly rate was 0.4% high, which put $20 a month between the two generators on Barberry.
    i = (1 + HH["mortgage_rate"] / 2.0) ** (1.0/6.0) - 1.0
    n = HH["amortization"] * 12
    pi = principal * i / (1 - (1 + i) ** (-n)) if i else principal / n
    tax = (o.get("annual_taxes") or 0) / 12.0
    upkeep = c["reserve_monthly"]
    return pi + tax + upkeep, {"pi": pi, "tax": tax, "upkeep": upkeep}

def price_component(o, c):
    """v6.1 §3, refined 2026-09-15. 100 at or below the comfortable payment, falling linearly to
    0 at the maximum, clamped at 0 above it.

    Alex asked on 2026-09-15 that houses above the maximum still be ranked, so max_mo is a soft
    ceiling (price.gate_at_max: false) rather than a G3 gate. The clamp means every house above
    the maximum ties at 0 on price and the other seven components order them; that is a real loss
    and it is the price of keeping the scale absolute. Returns (0-100, payment, over_by)."""
    P = CFG["price"]; pay, _parts = monthly_payment(o, c)
    comf, mx = float(P["comfortable_mo"]), float(P["max_mo"])
    if pay <= comf: v = 100.0
    elif mx > comf: v = 100.0 * (mx - pay) / (mx - comf)
    else:           v = 0.0
    return max(0.0, min(100.0, v)), pay, max(0.0, pay - mx)

def over_maximum(o, c):
    """The `Over your maximum` stamp: the fact that replaced the gate."""
    _v, pay, over = price_component(o, c)
    if over <= 0: return None
    return f"Over your maximum: ${pay:,.0f}/mo, ${over:,.0f} over ${CFG['price']['max_mo']:,}"

def ensuite_state(o):
    """v6.1 §5 Q4. Returns True, False or None (unknown -> `Layout partly estimated`).

    An MLS room table does not label an ensuite. The rule: find the level the Primary is on; if
    that level carries two or more bathrooms, one of them is the primary's; if it carries exactly
    one bathroom and two or more bedrooms, that bath is shared and there is no ensuite. Anything
    else is unknown and says so rather than guessing."""
    if o.get("ensuite") is not None: return bool(o["ensuite"])
    rooms = o.get("rooms_raw") or []
    if not rooms: return None
    lvl = None
    for r in rooms:
        if len(r) >= 2 and str(r[1]).lower().startswith("primary"): lvl = r[0]; break
    if lvl is None: return None
    baths = sum(1 for r in rooms if r[0] == lvl and "bath" in str(r[1]).lower())
    beds  = sum(1 for r in rooms if r[0] == lvl and str(r[1]).lower().startswith(("bedroom", "primary")))
    if baths >= 2: return True
    if baths == 1 and beds >= 2: return False
    return None

def ensuite_with_basis(o):
    """ensuite_state, then a second-tier fallback on the bath count for the 23 records that carry
    no room table. Returns (True/False/None, basis string). The two tiers are kept apart on
    purpose: tier 1 is read off the room table, tier 2 is an INFERENCE from how many full baths a
    three-or-more-bedroom house of this stock has, and the card says which one it used."""
    v = ensuite_state(o)
    if v is not None:
        return v, ("stated in the record" if o.get("ensuite") is not None else "read from the room table")
    nf = o.get("baths_full") or 0
    beds = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
    if nf <= 1: return False, f"inferred: {nf} full bath in the house, so nothing is private to the primary"
    if nf >= 3 and beds >= 3: return True, f"inferred: {nf} full baths on {beds} bedrooms"
    return None, "no room table and the bath count does not settle it"

def layout_pts(o):
    """v6.1 §5 Q4. bedrooms 0-80, primary over 150 sq ft +10, ensuite +10, on a 0-100 scale, then
    rescaled to fact_weights.layout.pts. The tiny-bedroom rule survives from v5 as a 20-point
    penalty on the 100 scale (it was 4 of 20). Returns (points_on_fact_scale, estimated)."""
    L = CFG.get("layout") or {}
    W = CFG["fact_weights"]["layout"]["pts"]
    if not L.get("ensuite_matters"):
        b = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
        lay = {0:0,1:2,2:6,3:13,4:19}.get(b,20)
        if (o.get("beds_under_100sqft") or 0) > 0: lay -= 4
        if (o.get("primary_bed_sqft") or 0) >= 150: lay += 2
        return max(0, min(W, lay)), False
    b = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
    bed_scale = {0:0.0, 1:0.12, 2:0.38, 3:0.81, 4:1.0}
    v = L["bedroom_pts"] * bed_scale.get(b, 1.0)
    if (o.get("primary_bed_sqft") or 0) >= 150: v += L["primary_over_150_pts"]
    ens, _basis = ensuite_with_basis(o)
    if ens: v += L["ensuite_pts"]
    if (o.get("beds_under_100sqft") or 0) > 0: v -= 20
    v = max(0.0, min(100.0, v))
    return W * v / 100.0, (ens is None)

def is_project(o, work_exp):
    """G4. Expected work above project_share_of_ask of the ask. Ranked with a Project stamp
    unless the buyer said no projects, in which case it is a gate."""
    return work_exp > CFG["gates"].get("project_share_of_ask", 0.15) * o["list_price"]

def gates(o, c, fs, v, work_exp=None):
    """G0 to G4, non-compensatory, in order. A gated listing is not ranked; it is shown at the
    bottom with rank '-'. HOLD (oil / pool / tenanted) is not a gate: it is a stamp."""
    g = CFG["gates"]; out = []
    if v == "STOP": out.append("STOP")
    beds = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
    if g["min_beds_ag"] and beds < g["min_beds_ag"]: out.append(f"{beds} bed AG < {g['min_beds_ag']}")
    if g["min_baths_full"] and (o.get("baths_full") or 0) < g["min_baths_full"]: out.append("no full bath")
    if g["max_all_in"] and o["list_price"] + c["day1_p80"] > g["max_all_in"]: out.append("over budget")
    if g["max_cash_to_close"] and cash_to_close(o["list_price"], c["day1_p80"]) > g["max_cash_to_close"]: out.append("cash to close")
    if g.get("no_projects") and work_exp is not None and is_project(o, work_exp):
        out.append(f"project: work is {work_exp/o['list_price']:.0%} of ask")
    # v6.1 §3, G3 on the monthly payment. OFF by default since 2026-09-15: Alex asked that houses
    # above his maximum still be ranked, so the ceiling is a stamp (over_maximum) not a gate.
    P = CFG.get("price") or {}
    if P.get("gate_at_max"):
        _v, pay, over = price_component(o, c)
        if over > 0: out.append(f"payment ${pay:,.0f}/mo over the ${P['max_mo']:,} maximum")
    return out

def hold_flags(notes):
    """OIL / POOL / TENANTED: ranked and flagged, never a silent exclusion."""
    return [n.split(" — ")[0].split(" ")[0] for n in notes if n.startswith(("OIL","POOL","TENANTED"))]

def frontier_overpay(rows, key="own"):
    """For each row, the cheapest own-cost among rows whose fit is within the tolerance.
    overpay = own - that minimum; 0 means nothing as good is cheaper.

    v6 keeps this computed and keeps it OFF the card. Its one surviving use is the first of the
    three "Before you offer" lines in the showing record (USABILITY-SPEC §4.3). It no longer
    sets the order, there is no Frontier stamp, and no group header refers to it."""
    ranked = [r for r in rows if not r["gated"]]; tol = CFG["rank"]["dominance_tolerance_pts"]
    for r in ranked:
        peers = [x for x in ranked if x["fs"] >= r["fs"] - tol]
        best = min(peers, key=lambda x: x[key])
        r["overpay"] = r[key] - best[key]; r["dominated_by"] = None if best is r else best["slug"]
    return ranked

# ================================================== rank v6: one score, elicited weights
# RANK-V6-DECISION.md §2 to §5. Eight components, each 0 to 100 on ABSOLUTE anchors, combined
# with swing weights elicited from the buyers. Nothing in the batch sets a weight or an anchor.

COMP_KEYS = ("space", "layout", "baths", "parking", "lot", "location", "condition", "price")
SHOWING_YEAR_FIELDS = ("roof_year", "furnace_year", "ac_year", "water_heater_year")

def has_showing_evidence(o):
    """True when somebody stood in this house and recorded a mechanical. v6 §3 bound 4: the last
    stretch of the condition range is only reachable this way."""
    return (any(parse_seen(o.get(f)) for f in SEEN_FIELD.values())
            or any(o.get(f) for f in SHOWING_YEAR_FIELDS))

def work_expected(o, c, H):
    """v6 §3. (expected work, work if every job were needed, the day-one part of the expected sum),
    in planning dollars.

    Day-one and wishlist lines carry the cost model's own probability. Reserve lines carry that
    probability times p_hold, the chance the component is replaced during the hold. `full` is the
    same sums WITH EVERY PROBABILITY AT 1, and that means p_hold too: keeping p_hold in the
    denominator made it cancel on exactly the lines it was added for, so a 1972 furnace read as
    fully expected in the hold, the same as a 2008 one (correction of 14 September, item 3).

    The one carve-out is a line whose life is 1: the pool carry is an annual cost, not a component
    with a replacement probability, so its H multiplier is a count and stays on both sides."""
    k = 1 + cont(eff_year(o)); hst = 1 + CFG["meta"]["hst"]
    meta = c.get("reserve_meta", {}); exp = full = exp_day1 = 0.0
    for nm, b, p, lo, ml, hi, _ in c["items"]:
        mean = (lo + 4*ml + hi) / 6
        if b == "reserve":
            a, life, conf = meta.get(nm, (60, CAT_life(nm), False))
            ph = p_hold(a, life, H, conf)
            exp += p * ph * mean * hst
            full += (ph if life <= 1 else 1.0) * mean * hst
        else:
            exp += p * mean * k * hst;  full += mean * k * hst
            if b == "day1": exp_day1 += p * mean * k * hst
    return exp, full, exp_day1

def condition_from(exp, full):
    return 100 * clamp(1 - exp/full) if full else 50.0

def condition_band(o, c, H, draws, exp, full, exp_day1):
    """v6 correction item 3. The band's condition axis: the model's own day-one uncertainty, from
    the 4,000 draws cost() already makes. The draws carry the contingency, the multi-room premium,
    HST and soft costs, which the line-by-line expected sum does not, so the draws enter as a
    RATIO against their own median rather than as a level. Returns (low, point, high) condition,
    low being the one with more work."""
    if not draws: return (condition_from(exp, full),)*3
    ds = sorted(draws); n = len(ds)
    p10, p50, p90 = ds[int(0.10*n)], ds[int(0.50*n)], ds[int(0.90*n)-1]
    if p50 <= 0: return (condition_from(exp, full),)*3
    hi_work = exp - exp_day1 + exp_day1*(p90/p50)      # more day-one work: condition falls
    lo_work = exp - exp_day1 + exp_day1*(p10/p50)
    return (condition_from(hi_work, full), condition_from(exp, full), condition_from(lo_work, full))

def muni_bonus(o):
    """location.municipality_bonus, elicited. Zero is the expected answer and the default."""
    b = (CFG.get("location") or {}).get("municipality_bonus") or {}
    try: return float(b.get(o.get("municipality") or "", 0) or 0)
    except (TypeError, ValueError): return 0.0

def components(o, c, H):
    """The eight components, each 0 to 100. Six are the v5 fit parts rescaled; condition and
    price are new. Returns (comp, fact_score, fact_parts, extras)."""
    fs, parts = facts(o, c)
    w = CFG["fact_weights"]; fw = CFG["fit_weights"]
    comp = {
        "space":    100 * parts["space"]    / fw["space"]["pts"],
        "layout":   100 * parts["layout"]   / w["layout"]["pts"],
        "baths":    100 * parts["baths"]    / w["baths"]["pts"],
        "parking":  100 * parts["parking"]  / w["parking"]["pts"],
        "lot":      100 * parts["lot"]      / w["lot"]["pts"],
        "location": min(100.0, 100 * parts["location"] / w["location"]["pts"] + muni_bonus(o)),
    }
    exp, full, exp_day1 = work_expected(o, c, H)
    comp["condition"] = condition_from(exp, full)
    own, op = own_cost(o, c, c["day1_p80"], H)
    per_yr = (own - op["day1_sunk"]) / H          # day-one lives in condition, never counted twice
    if CFG.get("price"):                          # v6.1 §3: buyer-anchored, on the monthly payment
        comp["price"], _pay, _over = price_component(o, c)
    else:
        a = CFG["hold"]["price_anchor_per_year"]
        comp["price"] = 100 * clamp((a["worst"] - per_yr) / (a["worst"] - a["best"]))
    for k in comp: comp[k] = max(0.0, min(100.0, comp[k]))
    return comp, fs, parts, {"work_exp": exp, "work_full": full, "work_exp_day1": exp_day1,
                             "own": own, "oparts": op,
                             "cost_hold": own - op["day1_sunk"], "per_yr": per_yr}

def norm_weights(w):
    t = sum(float(v) for v in w.values()) or 1.0
    return {k: float(w.get(k, 0))/t for k in COMP_KEYS}

def weight_sets():
    """{'alex': …, 'partner': …, 'joint': …} normalised to sum 1. A person recorded as `pending`
    is absent, and joint falls back to whoever is present."""
    W = CFG.get("weights") or {}
    out = {}
    for who in ("alex", "partner"):
        f = fitted_weights(who)               # fifteen pairwise choices beat the provisional prior
        if f: out[who] = norm_weights(f["weights"]); continue
        v = W.get(who)
        if isinstance(v, dict): out[who] = norm_weights(v)
    if not out:
        raise SystemExit("score.py: costs.yaml has no elicited weights. Run ELICITATION.md first.")
    j = W.get("joint")
    if isinstance(j, dict):
        out["joint"] = norm_weights(j)
    elif len(out) == 2:
        out["joint"] = norm_weights({k: (out["alex"][k] + out["partner"][k])/2 for k in COMP_KEYS})
    else:
        out["joint"] = dict(next(iter(out.values())))
    return out

_FITTED = {}
def fitted_weights(who):
    """The weights fitted from this person's fifteen pairwise choices, or None. Computed once."""
    if who in _FITTED: return _FITTED[who]
    try:
        import fit_choices
        _FITTED[who] = fit_choices.fit(who, CFG)
    except Exception as e:                    # a missing scipy must not break the whole pipeline
        print(f"WARNING fit_choices unavailable for {who}: {e}", file=sys.stderr)
        _FITTED[who] = None
    return _FITTED[who]

def is_provisional(who):
    """A person's weights are provisional until fifteen pairwise choices have been fitted for
    them. A person not on file at all is provisional by definition."""
    if fitted_weights(who): return False
    W = CFG.get("weights") or {}
    if not isinstance(W.get(who), dict): return True
    return bool((W.get("provisional") or {}).get(who, True))

# The page stamps every card and the mast while EITHER person is provisional.
PROVISIONAL = any(is_provisional(w) for w in ("alex", "partner"))

def v6_score(comp, wn, split):
    s = sum(wn[k]*comp[k] for k in COMP_KEYS)
    return s * (CFG["split_dock"] if split else 1.0)

# ====================================== SCORING-EXPLANATION-FINAL.md §1, 2026-09-15
# ONE SOURCE for every number and every sentence about a scale.
#
# The bug this closes: the 14 September build printed Barberry at price 100 under a sentence
# saying $84,000 scores 0 and $54,000 scores 100 (which gives 37), and lot 23 under a sentence
# saying 4,000 sq ft scores 0 (which gives 0). Two generators, one of them stale.
#
# Rule: every component returns (score, fact, scale) from ONE function that reads costs.yaml.
# The card prints `fact`. The glossary prints `scale`. Nothing about a scale is typed into a
# template, ever. test_model.py recomputes each component from the facts the page prints and
# fails the build on any drift.

def _fmt(n, p=0):
    return f"{n:,.{p}f}"

def explain_space(o, cfg=None):
    cfg = cfg or CFG; sp = cfg["fit_weights"]["space"]
    pts = space_pts(o); score = 100.0 * pts / sp["pts"]
    ag = o.get("sqft_above") or 0
    fin, part, sep = basement_flags(o)
    bits = [f"{_fmt(ag)} sq ft above grade"]
    if fin: bits.append("finished basement")
    elif part: bits.append("part-finished basement")
    if sep: bits.append("separate entrance")
    scale = (f"0 below {_fmt(sp['floor_sqft'])} sq ft above grade, most of the points by "
             f"{_fmt(sp['knee_sqft'])}, the rest to {_fmt(sp['cap_sqft'])}. "
             f"A finished basement adds {sp['basement_finished']} of {sp['pts']}, "
             f"a separate entrance {sp['basement_exterior_access']}.")
    return round(score, 1), ", ".join(bits), scale

def explain_layout(o, cfg=None):
    cfg = cfg or CFG; L = cfg.get("layout") or {}
    pts, est = layout_pts(o); score = 100.0 * pts / cfg["fact_weights"]["layout"]["pts"]
    b = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
    ens, basis = ensuite_with_basis(o)
    bits = [f"{b} bedrooms above grade"]
    pb = o.get("primary_bed_sqft") or 0
    if pb: bits.append(f"primary {_fmt(pb)} sq ft")
    bits.append("ensuite" if ens else ("no ensuite" if ens is False else "ensuite unknown"))
    if (o.get("beds_under_100sqft") or 0) > 0:
        bits.append(f"{o['beds_under_100sqft']} bedroom under 100 sq ft")
    if L.get("ensuite_matters"):
        scale = (f"Bedrooms carry {L['bedroom_pts']} of 100, a primary over 150 sq ft adds "
                 f"{L['primary_over_150_pts']}, an ensuite adds {L['ensuite_pts']}, and any bedroom "
                 f"under 100 sq ft costs 20. The ensuite is read from the room table where there is "
                 f"one and inferred from the bath count where there is not; the card says which.")
    else:
        scale = "Bedroom count, with a small bonus for a primary over 150 sq ft and a penalty for a bedroom under 100."
    return round(score, 1), ", ".join(bits), scale

def explain_baths(o, cfg=None):
    cfg = cfg or CFG; w = cfg["fact_weights"]["baths"]["pts"]
    nf, nh = o.get("baths_full") or 0, o.get("baths_half") or 0
    pts = min(w, {0:0,1:5,2:13,3:18}.get(nf,20) + (2 if nh else 0))
    fact = f"{nf} full" + (f" and {nh} powder" if nh else ", no powder")
    scale = ("One full bath scores 25, two 65, three 90, four or more 100, and a powder room adds 10. "
             "Counts only; nothing here is about condition.")
    return round(100.0*pts/w, 1), fact, scale

def explain_parking(o, cfg=None):
    cfg = cfg or CFG; w = cfg["fact_weights"]["parking"]["pts"]
    g, s = o.get("garage_spaces") or 0, o.get("parking_spots") or 0
    pts = min(w, g*3 + s)
    fact = f"{g} garage, {s} on the drive"
    scale = f"Each garage space counts 3 and each driveway spot 1, capped at {w}, so {w} or more scores 100."
    return round(100.0*pts/w, 1), fact, scale

def explain_lot(o, cfg=None):
    cfg = cfg or CFG; w = cfg["fact_weights"]["lot"]["pts"]; L = cfg.get("lot") or {}
    lot = (o.get("lot_frontage_ft") or 0)*(o.get("lot_depth_ft") or 0)
    if L and not L.get("matters", True):
        return 50.0, f"{_fmt(lot)} sq ft lot", "A yard does not matter to you, so every house scores 50 and the pairs will give lot a low weight."
    f_, c_ = L.get("floor_sqft", cfg["fact_weights"]["lot"]["floor_sqft"]), L.get("cap_sqft", cfg["fact_weights"]["lot"]["ceiling_sqft"])
    pts = w*max(0, min(1, (lot-f_)/(c_-f_)))
    fr, dp = o.get("lot_frontage_ft") or 0, o.get("lot_depth_ft") or 0
    fact = f"{_fmt(fr,0)} x {_fmt(dp,0)} ft, {_fmt(lot)} sq ft"
    scale = f"{_fmt(f_)} sq ft scores 0 and {_fmt(c_)} scores 100, straight line between. Your numbers for small and plenty."
    return round(100.0*pts/w, 1), fact, scale

def explain_location(o, cfg=None):
    cfg = cfg or CFG
    parts, total, flags = location_parts(o)
    P = cfg["location"]["parts"]
    fact = " · ".join(f"{k.capitalize()} {p['pts']:.0f} of {p['max']}" for k, p in parts.items())
    scale = ("Five parts out of 100. "
             f"Commute {P['commute']['pts']}: 0 at {P['commute']['zero_m']/1000:.0f} km from the nearest GO station, 100 at {P['commute']['full_m']/1000:.1f} km. "
             f"Quiet {P['quiet']['pts']}: 0 within {P['quiet']['zero_m']} m of the QEW, 403, 407 or the rail corridor, 100 beyond {P['quiet']['full_m']} m, "
             "with a bonus for a court or crescent and a cap for a named arterial. "
             f"Walk and transit {P['walk']['pts']}: 0 at {P['walk']['zero']} between them, 100 at {P['walk']['full']}. "
             f"School {P['school']['pts']}: 0 with none within {P['school']['zero_km']} km, 100 within {P['school']['full_km']} km. "
             f"Green and water {P['green']['pts']}: 0 beyond {P['green']['zero_m']/1000:.0f} km from the shore and every park over 5 ha, 100 within {P['green']['full_m']} m of either.")
    return round(total, 1), fact, scale, parts, flags

def explain_condition(o, c=None, H=None, cfg=None):
    cfg = cfg or CFG; c = c if c is not None else cost(o); H = H or cfg["hold"]["years_default"]
    exp, full, exp_day1 = work_expected(o, c, H)
    score = condition_from(exp, full)
    fact = f"${_fmt(exp/1000,0)}k of ${_fmt(full/1000,0)}k of possible work expected"
    scale = ("The cost-weighted share of this house's possible work that is NOT expected, from the "
             "cost model's own probabilities. 100 means nothing is expected; 0 means every line "
             "lands. Mechanicals are aged, so a component at the end of its life counts more. "
             "Nobody has stood in any of these houses, so photographs alone cannot take a house "
             "much above 80.")
    return round(score, 1), fact, scale

def explain_price(o, c=None, cfg=None):
    """Under the reframe this is the COST side, not a component. Returned in the same shape so
    one loop can render all of them."""
    cfg = cfg or CFG; c = c if c is not None else cost(o)
    P = cfg["price"]; pay, parts = monthly_payment(o, c)
    pen = cost_penalty(o, c)
    fact = f"${_fmt(pay)} /mo, made of ${_fmt(parts['pi'])} P&I, ${_fmt(parts['tax'])} tax and ${_fmt(parts['upkeep'])} upkeep"
    scale = (f"No penalty at or under ${_fmt(P['comfortable_mo'])} a month, your comfortable payment, "
             f"rising in a straight line to the full penalty at ${_fmt(P['max_mo'])}, your maximum. "
             f"Above the maximum it holds at the full penalty. At the dial the page is set to, the "
             f"full penalty costs {dial():.0f} quality points.")
    return round(100.0 - pen, 1), fact, scale

# ------------------------------- SCORING-EXPLANATION-FINAL.md §2: say what the work is
# "$65,042 expected against $228,302" is right and tells the reader nothing to act on. These are
# the cost model's own three buckets, the unseen tells, and what a showing is worth in the score's
# own units. No new model: the scenarios are two more runs of cost().

CLEAN_READ = {"kitchen_sink_mount":"undermount", "kitchen_counter_edge":"square_eased",
  "kitchen_soffit":"removed", "kitchen_door_profile":"crisp_shaker", "bath_tub_type":"alcove_tiled",
  "bath_tile_scale":"large_format", "bath_vanity_top":"undermount_stone",
  "floor_condition":"no_defect_seen", "ceiling_main":"flat_painted", "window_frame":"vinyl",
  "panel_type":"breaker_200", "basement_ceiling":"drywall", "basement_walls":"drywall",
  "basement_moisture":"none_visible", "driveway":"sound"}
# The defect read deliberately uses `fresh_paint_low_only` rather than `efflorescence` for
# moisture: efflorescence is a hard STOP, and a scenario must not manufacture one.
DEFECT_READ = {"kitchen_sink_mount":"topmount", "kitchen_counter_edge":"rolled_bullnose",
  "kitchen_soffit":"present", "kitchen_door_profile":"soft_raised_panel",
  "bath_tub_type":"corner_garden_platform", "bath_tile_scale":"small_4x4",
  "bath_vanity_top":"integrated_cultured_marble", "floor_condition":"uneven_stain",
  "ceiling_main":"stipple_popcorn", "window_frame":"aluminum_original", "panel_type":"fuse",
  "basement_ceiling":"drop_tile", "basement_walls":"bare_block",
  "basement_moisture":"fresh_paint_low_only", "driveway":"cracked"}

def _resolved_condition(o, table, H, full_today=None):
    """Condition with every unseen tell resolved the same way. Two runs of cost(), no new model.

    The denominator is HELD AT TODAY'S `full`, and that choice is load-bearing. Resolving a tell
    can remove a line from the cost model altogether (a pre-1970 house with an unseen panel
    carries panel at p=0.5 and a partial rewire at p=0.25; read the panel as a modern breaker and
    both lines vanish). A vanished line leaves the numerator AND the denominator, and because
    condition is 1 - exp/full, dropping a line whose probability was below the house's overall
    ratio makes the ratio worse and the score fall. Four houses did exactly that before this fix:
    Centennial, Weir, Cherrywood and Samford all scored LOWER after a perfectly clean read.

    That is an artefact of the denominator, not a fact about the house, and it makes the line
    unreadable ("a showing could move this to 58 if everything reads clean" when it is 60 today).
    Holding `full` fixed answers the question the reader is actually asking: of the work this
    house might need today, how much would the visit rule in or out. It also makes the two ends
    monotone by construction, which test_model.py asserts."""
    o2 = dict(o)
    for f in TELLS:
        if o2.get(f) in (None, "", "not_shown"): o2[f] = table.get(f, o2.get(f))
    c2 = cost(o2)
    exp, full, _d = work_expected(o2, c2, H)
    return round(condition_from(exp, full_today if full_today else full), 1)

def condition_block(o, c=None, H=None):
    """The four-line condition block: three buckets with their two largest expected lines, the
    unseen tells, and the two showing scenarios."""
    c = c if c is not None else cost(o); H = H or CFG["hold"]["years_default"]
    exp, full, _d = work_expected(o, c, H)
    hst = 1 + CFG["meta"]["hst"]; k = 1 + cont(eff_year(o))
    buckets = {"must do": [], "optional": [], "mechanicals": []}
    for nm, b, p, lo, ml, hi, _bs in c["items"]:
        mean = (lo + 4*ml + hi)/6
        if b == "reserve":
            life = CAT_life(nm)
            a, life2, conf = (c.get("reserve_meta") or {}).get(nm, (60, life, False))
            e = p * p_hold(a, life2, H, conf) * mean * hst
            buckets["mechanicals"].append((nm, e))
        elif b == "day1":
            buckets["must do"].append((nm, p*mean*k*hst))
        else:
            buckets["optional"].append((nm, p*mean*k*hst))
    out = []
    for name in ("must do", "optional", "mechanicals"):
        rows = sorted(buckets[name], key=lambda t: -t[1])
        tot = sum(e for _n, e in rows)
        top = ", ".join(n for n, _e in rows[:2] if _e > 0) or "nothing expected"
        out.append({"bucket": name, "total": round(tot), "top": top})
    unseen = [f for f in TELLS if o.get(f) in (None, "", "not_shown")]
    return {"score": round(condition_from(exp, full), 1),
            "expected": round(exp), "full": round(full),
            "buckets": out, "unseen": unseen,
            "if_clean": _resolved_condition(o, CLEAN_READ, H, full),
            "if_defect": _resolved_condition(o, DEFECT_READ, H, full),
            "denominator": "held at today's possible work; see _resolved_condition",
            "photo_cap": not has_showing_evidence(o)}

EXPLAINERS = {"space": explain_space, "layout": explain_layout, "baths": explain_baths,
              "parking": explain_parking, "lot": explain_lot}

def explain_all(o, c=None, H=None, cfg=None):
    """{component: {score, fact, scale}} for all eight, from one place."""
    cfg = cfg or CFG; c = c if c is not None else cost(o)
    out = {}
    for k, fn in EXPLAINERS.items():
        s_, f_, sc = fn(o, cfg); out[k] = {"score": s_, "fact": f_, "scale": sc}
    s_, f_, sc, parts, flags = explain_location(o, cfg)
    out["location"] = {"score": s_, "fact": f_, "scale": sc,
                       "parts": {k: {"pts": p["pts"], "max": p["max"], "detail": p["detail"]} for k, p in parts.items()},
                       "estimated": flags}
    s_, f_, sc = explain_condition(o, c, H, cfg); out["condition"] = {"score": s_, "fact": f_, "scale": sc}
    s_, f_, sc = explain_price(o, c, cfg);        out["price"]     = {"score": s_, "fact": f_, "scale": sc}
    return out

# ============================================================ PRICE-REFRAME.md, 2026-09-15
# Quality is the seven non-price components. Cost is a penalty in quality points through a dial.
QUAL_KEYS = tuple(k for k in COMP_KEYS if k != "price")

def reframed():
    return bool((CFG.get("price") or {}).get("reframe"))

def dial():
    """Quality points taken off by a full cost swing. Fitted from the pairs when they exist;
    otherwise the provisional value in costs.yaml, which is derived from the provisional price
    weight so the reframe alone does not move the order."""
    return float((CFG.get("price") or {}).get("dial", 0.0))

def quality(comp, wn, split):
    """0 to 100 on the seven non-price components, renormalised over those seven so the number
    keeps the same meaning whatever weight price carries."""
    t = sum(wn[k] for k in QUAL_KEYS) or 1.0
    s = sum(wn[k]*comp[k] for k in QUAL_KEYS) / t
    return s * (CFG["split_dock"] if split else 1.0)

def cost_penalty(o, c):
    """0 at or under the comfortable payment, 100 at the maximum, clamped above it.
    Clamping is what keeps the scale absolute; the cost of it is that every house above the
    maximum ties at 100 and the seven quality components order them."""
    P = CFG["price"]; pay, _ = monthly_payment(o, c)
    comf, mx = float(P["comfortable_mo"]), float(P["max_mo"])
    if pay <= comf: return 0.0
    if mx <= comf:  return 100.0
    return max(0.0, min(100.0, 100.0 * (pay - comf) / (mx - comf)))

def value_of(comp, wn, split, pen, d=None):
    """quality minus the dial's share of the cost penalty. This is what the rank sorts on."""
    q = quality(comp, wn, split)
    return q - (dial() if d is None else d) * pen / 100.0

def is_split(o): return "plit" in str(o.get("style", ""))

HOLDS = (3, 5, 10)      # the three holds the page toggles between

def short_street(addr):
    """'3217 Hazelwood Avenue, Burlington, ON' -> 'Hazelwood'. Used in the reason line."""
    return addr.split(",")[0].split(" ", 1)[1].split(" ")[0]

def prepare(obs_path):
    """Cost, components at all three holds, fit, verdict, resale and gates for every listing,
    once. No ranking yet. G4 needs the expected work, so gates are evaluated after it."""
    obs = [normalise(o) for o in json.load(open(obs_path))]; rows = []
    for w in dedupe_warnings(obs): print("WARNING", w, file=sys.stderr)
    HD = CFG["hold"]["years_default"]
    for o in obs:
        c, draws = day1_draws(o)
        comps = {H: components(o, c, H) for H in HOLDS}
        comp, fs, parts, extra = comps[HD]
        v, notes = verdict(o, c, fs); rs = resale(o, c)
        dem, cwhy = condition_demote(o, c)
        u = usable(o) or 1
        mo = round((o.get("annual_taxes") or 0)/12) + c["reserve_monthly"]
        rows.append({"o": o, "c": c, "fs": fs, "parts": parts, "v": v, "notes": notes, "rs": rs, "mo": mo,
                     "slug": o["slug"], "ask": o["list_price"], "d1": c["day1_p80"], "draws": draws,
                     "grade": grade(fs), "cond_why": "; ".join(cwhy) or "-",
                     "comps": {H: comps[H][0] for H in HOLDS},
                     "extras": {H: comps[H][3] for H in HOLDS},
                     # (low, point, high) condition at each hold, from this house's own day-one draws
                     "cond_var": {H: condition_band(o, c, H, draws, comps[H][3]["work_exp"],
                                                    comps[H][3]["work_full"], comps[H][3]["work_exp_day1"])
                                  for H in HOLDS},
                     "comp": comp, "work_exp": extra["work_exp"], "work_full": extra["work_full"],
                     "own": extra["own"], "oparts": extra["oparts"], "H": HD,
                     "project": is_project(o, extra["work_exp"]),
                     "seen_evidence": has_showing_evidence(o),
                     "split": is_split(o),
                     "gated": gates(o, c, fs, v, extra["work_exp"]), "hold": hold_flags(notes),
                     "true_cost": o["list_price"] + c["day1_p80"],
                     "cost_pen": cost_penalty(o, c),              # PRICE-REFRAME
                     "pay_mo": monthly_payment(o, c)[0],
                     "pay_parts": monthly_payment(o, c)[1],
                     "ppsf": round((o["list_price"] + c["day1_p80"])/u)})
    return rows

CVAR = {"low": 0, "point": 1, "high": 2}

def comp_at(r, H, cvar):
    """This house's eight components at hold H, with condition taken at the low, point or high
    end of its own day-one uncertainty."""
    comp = dict(r["comps"][H])
    comp["condition"] = r["cond_var"][H][CVAR[cvar]]
    return comp

def order_under(rows, wn, H, cvar="point"):
    """{slug: position} for the ungated rows under one weight set, one hold, one condition end."""
    live = [r for r in rows if not r["gated"]]
    if reframed():
        key = lambda r: (-value_of(comp_at(r, H, cvar), wn, r["split"], r["cost_pen"]), r["slug"])
    else:
        key = lambda r: (-v6_score(comp_at(r, H, cvar), wn, r["split"]), r["slug"])
    scored = sorted(live, key=key)
    return {r["slug"]: i for i, r in enumerate(scored, 1)}

def run(obs_path, out):
    """v3.4 cost model + rank v6. One score, sorted descending on weights.joint at the default
    hold. Gated listings are written at the bottom with rank '-' and no numeric rank anywhere."""
    rows = prepare(obs_path)
    HD = CFG["hold"]["years_default"]
    WS = weight_sets()
    people = [w for w in ("alex", "partner") if w in WS]

    # the nine (or six) rankings the band is taken over
    # The band, correction item 3: every weight set on file x every hold x every end of this
    # house's own day-one uncertainty. With one weight set that is nine rankings, not three.
    orders = {(who, H, cv): order_under(rows, WS[who], H, cv)
              for who in list(WS) for H in HOLDS for cv in CVAR}
    for r in rows:
        if r["gated"]:
            r["rank"] = "-"; r["band_lo"] = r["band_hi"] = "-"
            for who in WS: r[f"rank_{who}"] = "-"
            for H in HOLDS: r[f"rank_{H}"] = "-"
            continue
        # PRICE-REFRAME: `quality` is the seven-component number the panel shows, `cost_pts` is
        # what the payment takes off at the current dial, and `score` is what the rank sorts on.
        r["quality"] = round(quality(r["comp"], WS["joint"], r["split"]), 1)
        r["cost_pts"] = round(dial() * r["cost_pen"] / 100.0, 1) if reframed() else 0.0
        r["score"] = (round(value_of(r["comp"], WS["joint"], r["split"], r["cost_pen"]), 1)
                      if reframed() else round(v6_score(r["comp"], WS["joint"], r["split"]), 1))
        for who in WS:
            r[f"quality_{who}"] = round(quality(r["comp"], WS[who], r["split"]), 1)
            r[f"score_{who}"] = (round(value_of(r["comp"], WS[who], r["split"], r["cost_pen"]), 1)
                                 if reframed() else round(v6_score(r["comp"], WS[who], r["split"]), 1))
            r[f"rank_{who}"] = orders[(who, HD, "point")][r["slug"]]
        for H in HOLDS:
            r[f"rank_{H}"] = orders[("joint", H, "point")][r["slug"]]
            r[f"score_{H}"] = round(v6_score(r["comps"][H], WS["joint"], r["split"]), 1)
        pos = [orders[k][r["slug"]] for k in orders]
        r["band_lo"], r["band_hi"] = min(pos), max(pos)
        r["disagree"] = (len(people) == 2 and
                         abs(r["rank_alex"] - r["rank_partner"]) > 5)

    # The order IS orders[("joint", HD)]. Taking it from there rather than re-sorting on the
    # rounded score keeps the printed rank inside the printed band on near-ties.
    joint_order = orders[("joint", HD, "point")]
    ranked = sorted([r for r in rows if not r["gated"]], key=lambda r: joint_order[r["slug"]])
    for r in ranked: r["rank"] = joint_order[r["slug"]]
    gated = [r for r in rows if r["gated"]]
    frontier_overpay(rows)                      # overpay, for the "Before you offer" line only
    for r in gated: r["overpay"] = 0; r["dominated_by"] = None
    by = {r["slug"]: r for r in ranked}

    os.makedirs(out, exist_ok=True)
    partner_in = "partner" in people
    with open(os.path.join(out, "decision.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["rank","score","grade","address","ask","day1_p80","true_cost",
            "usable_sqft","all_in_psf","monthly_carry","wishlist_p80","total_spend",
            "resale_after_reno","resale_lo","resale_hi","recovered_pct","sunk","breakeven",
            "peer_norm","second_bath_op","verdict","notes",
            "year_used","year_src","bg_sqft_est","tells_seen_of_15","photos_total","stage2_date",
            "evidence","evidence_notes","cash_to_close_20pct",
            "renovations_needed","reno_if_all_done",
            # ---- rank v6 ----
            "c_space","c_layout","c_baths","c_parking","c_lot","c_location","c_condition","c_price",
            "work_expected","work_full","cost_hold","cost_hold_per_year",
            "c_condition_low","c_condition_high","weights_provisional",
            "rank_alex","rank_partner","score_alex","score_partner","band_lo","band_hi","disagree",
            "quality","cost_pen","cost_pts","pay_mo","pay_pi","pay_tax","pay_upkeep","dial",
            "project","hold_flags","seen_evidence","split_docked",
            "fit_score","space","layout","baths","lot","location","parking","condition",
            "condition_why",
            "own_mo","own_day1_sunk","own_capital","own_taxes","own_reserve","own_closing","hold_years",
            "overpay_total","overpay_mo","dominated_by",
            "rank_3","rank_10","score_3","score_10"])
        DASH = "-"
        for r in ranked + gated:
            gate = bool(r["gated"]); rs = r["rs"]; sp = r["c"]["day1_p80"] + r["c"]["wish_p80"]
            ex = r["extras"][HD]
            bo = (f'spend ${rs["bath_op"][0]:,} -> +${rs["bath_op"][1]:,}..${rs["bath_op"][2]:,}'
                  if rs["bath_op"] else DASH)
            comp = r["comp"]; op = r["oparts"]
            wr.writerow([
                (DASH if gate else r["rank"]), (DASH if gate else r["score"]), r["grade"],
                r["o"]["address"], r["o"]["list_price"], r["c"]["day1_p80"], r["true_cost"],
                rs["usable"], r["ppsf"], r["mo"], r["c"]["wish_p80"], sp,
                rs["arv_mid"], rs["arv_lo"], rs["arv_hi"], rs["recovered_pct"], rs["sunk"],
                rs["breakeven"], rs["norm"], bo, r["v"], " | ".join(r["notes"]) or DASH,
                eff_year(r["o"]),
                ("mls" if r["o"].get("year_built") else "est" if r["o"].get("year_built_est")
                 else "band" if r["o"].get("year_built_details") else "none"),
                ("est" if below_grade(r["o"])[1] else "mls" if r["o"].get("sqft_below") else DASH),
                sum(1 for x in TELLS if r["o"].get(x) not in (None, "", "not_shown")),
                r["o"].get("photos_total") or (r["o"].get("coverage") or {}).get("photos_total") or 0,
                r["o"].get("stage2_date", ""),
                evidence(r["o"])[0], evidence(r["o"])[2],
                cash_to_close(r["o"]["list_price"], r["c"]["day1_p80"]),
                *reno_text(reno_list(r["o"], r["c"])),
                *[round(comp[k], 1) for k in COMP_KEYS],
                round(r["work_exp"]), round(r["work_full"]), round(ex["cost_hold"]), round(ex["per_yr"]),
                round(r["cond_var"][HD][0], 1), round(r["cond_var"][HD][2], 1),
                ("yes" if PROVISIONAL else DASH),
                (DASH if gate else r["rank_alex"]),
                (DASH if gate or not partner_in else r["rank_partner"]),
                (DASH if gate else r["score_alex"]),
                (DASH if gate or not partner_in else r["score_partner"]),
                (DASH if gate else r["band_lo"]), (DASH if gate else r["band_hi"]),
                ("yes" if (not gate and r.get("disagree")) else DASH),
                # PRICE-REFRAME: quality, the cost penalty, what it costs at the dial, and the
                # payment broken into the three parts the money block prints.
                (DASH if gate else r.get("quality", DASH)), round(r["cost_pen"], 1),
                (DASH if gate else r.get("cost_pts", DASH)),
                round(r["pay_mo"]), round(r["pay_parts"]["pi"]), round(r["pay_parts"]["tax"]),
                round(r["pay_parts"]["upkeep"]), (dial() if reframed() else 0),
                ("yes" if r["project"] else DASH), "; ".join(r["hold"]) or DASH,
                ("yes" if r["seen_evidence"] else DASH), ("yes" if r["split"] else DASH),
                r["fs"], *[round(r["parts"][k], 1) for k in
                           ("space","layout","baths","lot","location","parking","condition")],
                r["cond_why"],
                round(r["own"]/(12*HD)),
                *[round(op[k]) for k in ("day1_sunk","capital","taxes","reserve","closing")], HD,
                round(r["overpay"]), round(r["overpay"]/(12*HD)), r["dominated_by"] or DASH,
                (DASH if gate else r["rank_3"]), (DASH if gate else r["rank_10"]),
                (DASH if gate else r["score_3"]), (DASH if gate else r["score_10"]),
            ])
    return ranked + gated

def sensitivity(rows):
    """v6: the band is rank under each weight set at each hold, min to max. Returned in the old
    {slug: (rank, lo, hi)} shape for callers."""
    return {r["slug"]: (r.get("rank", "-"), r.get("band_lo", "-"), r.get("band_hi", "-"))
            for r in rows if not r["gated"]}

if __name__ == "__main__":
    rows = run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "out")
    ranked = [r for r in rows if not r["gated"]]; gated = [r for r in rows if r["gated"]]
    HD = CFG["hold"]["years_default"]; WS = weight_sets()
    people = [w for w in ("alex", "partner") if w in WS]
    wj = WS["joint"]
    print(f'RANK v6: gates G0-G4 -> one score 0-100 from eight components on elicited swing weights, '
          f'sorted descending. Hold {HD}y, cost of capital {COST_OF_CAPITAL:.1%} derived from '
          f'{CFG["hold"]["mortgage_rate"]:.2%} / {CFG["hold"]["opportunity_rate"]:.1%} at '
          f'{CFG["hold"]["down_payment"]:.0%} down.')
    print('WEIGHTS ' + ("; ".join(f"{w}: " + " ".join(f"{k[:4]} {WS[w][k]*100:.0f}" for k in COMP_KEYS)
                                  for w in list(WS))))
    if "partner" not in people:
        print('NOTE: weights.partner is pending. joint = alex, the band is six rankings not nine, '
              'and no Disagree stamp can be set.')
    hdr = " ".join(f"{k[:5]:>5}" for k in COMP_KEYS)
    print(f'{"#":>2} {"SCORE":>5} {"GR":3} {"HOUSE":22} {hdr} {"BAND":>7} {"ASK":>10} {"WORK exp":>9}')
    for r in ranked:
        c = r["comp"]
        print(f'{r["rank"]:>2} {r["score"]:>5} {r["grade"]:3} {r["o"]["address"].split(",")[0][:22]:22} '
              + " ".join(f'{c[k]:>5.0f}' for k in COMP_KEYS)
              + f' {str(r["band_lo"])+"-"+str(r["band_hi"]):>7} ${r["ask"]:>9,} ${r["work_exp"]:>8,.0f}'
              + ("  [Project]" if r["project"] else "")
              + (f'  [HOLD: {", ".join(r["hold"])}]' if r["hold"] else ""))
    for r in gated:
        print(f' - {"":>5} {r["grade"]:3} {r["o"]["address"].split(",")[0][:22]:22} '
              + " ".join(f'{r["comp"][k]:>5.0f}' for k in COMP_KEYS)
              + f' {"":>7} ${r["ask"]:>9,} ${r["work_exp"]:>8,.0f}  GATED: {"; ".join(r["gated"])}')
    print("\nCONDITION, and the photo cap (v6 §3 bound 4)")
    over = [r for r in rows if r["comp"]["condition"] > 80 and not r["seen_evidence"]]
    lo = min(rows, key=lambda r: r["comp"]["condition"]); hi = max(rows, key=lambda r: r["comp"]["condition"])
    print(f'  range {lo["comp"]["condition"]:.0f} ({short_street(lo["o"]["address"])}) to '
          f'{hi["comp"]["condition"]:.0f} ({short_street(hi["o"]["address"])}); '
          f'{len(over)} listing(s) above 80 with no showing evidence')
    for r in over:
        print(f'  PHOTO CAP BROKEN: {short_street(r["o"]["address"])} condition {r["comp"]["condition"]:.0f}')
    print("\nCOST OF THE HOLD, COMPOSITION (mean over the ranked set, total over the hold)")
    import statistics as _st
    for k in ("capital", "taxes", "closing", "day1_sunk", "reserve"):
        v = [r["oparts"][k] for r in ranked]
        print(f'  {k:10} ${_st.mean(v):>9,.0f}   sd ${_st.pstdev(v):>8,.0f}')
    print("\nSECOND-BATH OPPORTUNITY (the only intervention that can exceed 100%)")
    for r in rows:
        if r["rs"]["bath_op"]:
            c_, l_, h_ = r["rs"]["bath_op"]
            print(f'  {r["o"]["address"].split(",")[0]:24} spend ${c_:,} -> value +${l_:,} to ${h_:,}')
