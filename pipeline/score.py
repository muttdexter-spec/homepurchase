#!/usr/bin/env python3
"""First House v3.2 (2026-09-12: v3.1 + evidence grade, rank band, cash-to-close, HDR/tiny-bedroom rules, duplicate check). Costs by WHEN you pay, p80 on the sum, no ceilings, no gut band.
Usage: python3 score.py observations.json out/"""
import json, csv, os, sys, random, statistics as st
import yaml

R = os.path.dirname(os.path.abspath(__file__))
CFG = yaml.safe_load(open(os.path.join(R, "costs.yaml")))
CAT, NOW, N = CFG["catalog"], 2026, 4000
random.seed(7)

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
    if "inish" not in str(o.get("basement","")): return 0, False
    ag = o.get("sqft_above") or 0
    st = STOREYS.get(str(o.get("style","")).strip(), 1.5)
    f = CFG.get("below_grade_estimate_factor", 0.70)
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

def prob(o, tells_seen, tells_total, defect):
    """P(this job is needed). 1.0 if a defect was confirmed. Otherwise the era prior,
    pulled toward the floor by how much was actually observed at full resolution."""
    if defect: return 1.0
    p = CFG["p_not_done"][era(eff_year(o))]
    f = (tells_seen / tells_total) if tells_total else 0
    return p - (p - CFG["observed_floor"]) * f

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
        prob(o,kseen,4,kbad), f"{kseen}/4 tells seen, defect={kbad}" + ksrc)

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
    if nf: add("main bath","bath_main_full", prob(o,bseen,3,bbad), f"{bseen}/3 tells seen" + bsrc)
    for i in range(max(0,nf-1)):
        # v3.1: a secondary bath CONFIRMED original in the photo pass is priced at p=1.0
        sec_bad = bool(o.get("secondary_bath_original")) and i == 0
        if o.get("secondary_bath_seen") == "done":
            add(f"bath {i+2}","bath_secondary", prob(o,3,3,False), "seen done at the showing")
        else:
            add(f"bath {i+2}","bath_secondary", prob(o,0,3,sec_bad), "confirmed original" if sec_bad else "unobserved")
    if nh: add("powder","bath_powder", prob(o,0,3,False), f"{nh} half", mult=nh)

    # ---- flooring + ceilings (day1) -----------------------------------------
    fc = o.get("floor_condition")
    add("flooring","flooring_per_sqft",
        prob(o,1 if fc=="no_defect_seen" else 0,1, fc in ("uneven_stain","patch_visible","gaps_at_base")),
        f"floor={fc}", mult=ag)
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
        add("basement","basement_per_sqft", prob(o,seen,2,bdef), f"{bg} sqft bg" + bsrc, mult=min(bg,900))

    # ---- reserve components (age-driven, NOT a purchase cost) ---------------
    metal_roof = "metal" in (str(o.get("roof_material",""))+str(o.get("roof_visual",""))).lower()
    for nm,key in [("roof","roof"),("furnace","furnace"),("A/C","ac"),("water heater","water_heater")]:
        p_res = 0.3 if (nm=="roof" and metal_roof) else 1.0   # v3.1: metal roof, 50y life
        items.append((nm,"reserve",p_res,CAT[key]["low"],CAT[key]["likely"],CAT[key]["high"],
                      "metal roof in MLS/photo, long life" if p_res<1 else f"life {CAT[key]['life']}y, age unstated"))
    wf = o.get("window_frame")
    if wf in ("aluminum_original","wood_original","original"):
        items.append(("windows","reserve",1.0,*[CAT["windows_full"][k] for k in("low","likely","high")],
                      f"{wf} CONFIRMED — near term"))
    elif wf != "vinyl":
        items.append(("windows","reserve",CFG["p_not_done"][era(yb)],
                      *[CAT["windows_full"][k] for k in("low","likely","high")],"frame not shown"))

    # ---- day1 hazards -------------------------------------------------------
    if yb and yb < 1970:
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
    res_yr = sum(p*((lo+4*ml+hi)/6)/CAT_life(nm) for nm,b,p,lo,ml,hi,_ in items if b=="reserve")
    near = sum(p*((lo+4*ml+hi)/6) for nm,b,p,lo,ml,hi,_ in items
               if b=="reserve" and age > CAT_life(nm))
    return {
        "items": items,
        "day1_p50": round(pc(sims["day1"],.50)), "day1_p80": round(pc(sims["day1"],.80)),
        "wish_p50": round(pc(sims["wishlist"],.50)), "wish_p80": round(pc(sims["wishlist"],.80)),
        "naive_sum_of_p80s": round(sum(p*hi for _,b,p,lo,ml,hi,_x in items if b!="reserve")*k*(1+CFG["meta"]["hst"])),
        "reserve_monthly": round(res_yr*(1+CFG["meta"]["hst"])/12),
        "near_term_5yr": round(near*(1+CFG["meta"]["hst"])),
        "moisture_confirmed": moist,
    }

def usable(o):
    ag=o.get("sqft_above") or 0; bg,_=below_grade(o)
    w=CFG["below_grade_weight_walkout"] if "alk" in str(o.get("basement","")) else CFG["below_grade_weight"]
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
def CAT_life(nm): return CAT[_LIFE[nm]]["life"]

# ------------------------------------------------------------------ facts
def facts(o):
    w, p = CFG["fact_weights"], {}
    ag = o.get("sqft_above") or 0
    p["size"] = w["size"]["pts"] * max(0,min(1,(ag-w["size"]["floor_sqft"])/(w["size"]["ceiling_sqft"]-w["size"]["floor_sqft"])))
    b = o.get("beds_effective") if o.get("beds_effective") is not None else (o.get("beds_ag") or 0)
    lay = {0:0,1:2,2:6,3:13,4:19}.get(b,20)
    if (o.get("beds_under_100sqft") or 0) > 0: lay -= 4
    if (o.get("primary_bed_sqft") or 0) >= 150: lay += 2
    p["layout"] = max(0,min(w["layout"]["pts"],lay))
    nf,nh = o.get("baths_full") or 0, o.get("baths_half") or 0
    p["baths"] = min(w["baths"]["pts"], {0:0,1:5,2:13,3:18}.get(nf,20) + (2 if nh else 0))
    lot = (o.get("lot_frontage_ft") or 0)*(o.get("lot_depth_ft") or 0)
    p["lot"] = w["lot"]["pts"]*max(0,min(1,(lot-w["lot"]["floor_sqft"])/(w["lot"]["ceiling_sqft"]-w["lot"]["floor_sqft"])))
    p["location"] = min(w["location"]["pts"], ((o.get("walk") or 0)+(o.get("transit") or 0))/15
                        + (4 if (o.get("nearest_school_km") or 9) < .5 else 2))
    p["parking"] = min(w["parking"]["pts"], (o.get("garage_spaces") or 0)*3 + (o.get("parking_spots") or 0))
    s = sum(p.values())
    if "plit" in str(o.get("style","")): s *= CFG["split_dock"]
    return round(s,1), p

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
    pool = o.get("pool") or ("in-ground" if _re.search(r"in-?ground (swimming )?pool", rm) else None)
    if pool == "in-ground": warns.append("POOL — in-ground, not priced")
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
    if not o.get("sqft_below") and "inish" in str(o.get("basement","")): why.append("basement area estimated")
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

def run(obs_path,out):
    obs = [normalise(o) for o in json.load(open(obs_path))]; rows=[]
    for w in dedupe_warnings(obs): print("WARNING", w, file=sys.stderr)
    for o in obs:
        c = cost(o); fs,parts = facts(o); v,notes = verdict(o,c,fs); rs = resale(o,c)
        u = usable(o) or 1
        mo = round((o.get("annual_taxes") or 0)/12) + c["reserve_monthly"]
        rows.append({"o":o,"c":c,"fs":fs,"parts":parts,"v":v,"notes":notes,"rs":rs,"mo":mo,
                     "true_cost": o["list_price"]+c["day1_p80"],
                     "ppsf": round((o["list_price"]+c["day1_p80"])/u)})
    rows.sort(key=lambda r:(r["ppsf"]))
    os.makedirs(out,exist_ok=True)
    with open(os.path.join(out,"decision.csv"),"w",newline="") as f:
        wr=csv.writer(f); wr.writerow(["rank","grade","address","ask","day1_p80","true_cost",
            "usable_sqft","all_in_psf","monthly_carry","wishlist_p80","total_spend",
            "resale_after_reno","resale_lo","resale_hi","recovered_pct","sunk","breakeven",
            "peer_norm","second_bath_op","verdict","notes",
            "year_used","year_src","bg_sqft_est","tells_seen_of_15","photos_total","stage2_date",
            "evidence","evidence_notes","cash_to_close_20pct","rank_low","rank_high",
            "renovations_needed","reno_if_all_done"])
        sens = SENS if "SENS" in globals() else {}
        for i,r in enumerate(rows,1):
            rs=r["rs"]; sp=r["c"]["day1_p80"]+r["c"]["wish_p80"]
            bo=f'spend ${rs["bath_op"][0]:,} -> +${rs["bath_op"][1]:,}..${rs["bath_op"][2]:,}' if rs["bath_op"] else "-"
            wr.writerow([i,grade(r["fs"]),r["o"]["address"],r["o"]["list_price"],r["c"]["day1_p80"],
                r["true_cost"],rs["usable"],r["ppsf"],r["mo"],r["c"]["wish_p80"],sp,
                rs["arv_mid"],rs["arv_lo"],rs["arv_hi"],rs["recovered_pct"],rs["sunk"],
                rs["breakeven"],rs["norm"],bo,r["v"]," | ".join(r["notes"]) or "-",
                eff_year(r["o"]), ("mls" if r["o"].get("year_built") else "est" if r["o"].get("year_built_est") else "band" if r["o"].get("year_built_details") else "none"),
                ("est" if below_grade(r["o"])[1] else "mls" if r["o"].get("sqft_below") else "-"),
                sum(1 for f in TELLS if r["o"].get(f) not in (None,"","not_shown")),
                r["o"].get("photos_total") or (r["o"].get("coverage") or {}).get("photos_total") or 0,
                r["o"].get("stage2_date",""),
                evidence(r["o"])[0], evidence(r["o"])[2], cash_to_close(r["o"]["list_price"], r["c"]["day1_p80"]),
                sens.get(r["o"]["slug"],("","",""))[1], sens.get(r["o"]["slug"],("","",""))[2],
                *reno_text(reno_list(r["o"], r["c"]))])
    return rows

def sensitivity(obs_path):
    """Which listings are actually ranked, and which are just noise? Re-rank under
    plausible flips of the inputs we have not verified."""
    import copy
    base=[r["o"]["slug"] for r in run(obs_path,"/tmp/_s")]
    pos={s:i for i,s in enumerate(base)}
    lo={s:i for i,s in enumerate(base)}; hi=dict(lo)
    flips={
      "basement estimate disabled":  lambda o: o.update({"sqft_below": o.get("sqft_below") or 0, "basement": "" if not o.get("sqft_below") else o.get("basement")}),
      "windows turn out original":   lambda o: o.update({"window_frame": "wood_original"}) if o.get("window_frame") != "vinyl" else None,
      "kitchen is a full gut":       lambda o: o.update({"kitchen_soffit":"present","kitchen_verdict":"defect_confirmed"}),
      "floors need replacing":       lambda o: o.update({"floor_condition":"uneven_stain"}),
      "unobserved all turns out ok": lambda o: o.update({"floor_condition":"no_defect_seen","ceiling_main":"flat_painted",
                                                          "window_frame":"vinyl","basement_walls":"drywall","basement_ceiling":"drywall"}),
    }
    for lab,fn in flips.items():
        obs=json.load(open(obs_path))
        for o in obs: fn(o)
        p="/tmp/_f.json"; json.dump(obs,open(p,"w"))
        order=[r["o"]["slug"] for r in run(p,"/tmp/_s")]
        for i,s in enumerate(order):
            lo[s]=min(lo[s],i); hi[s]=max(hi[s],i)
    return {s:(pos[s]+1,lo[s]+1,hi[s]+1) for s in base}

if __name__=="__main__":
    SENS=sensitivity(sys.argv[1])
    rows=run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else "out")
    sens=SENS
    print(f'{"#":2} {"GR":3} {"HOUSE":21} {"ASK":>10} {"DAY-1":>8} {"$/SF":>5} {"SPEND":>9} {"RESALE":>11} {"REC%":>5} {"SUNK":>9} {"RANK":>6}  VERDICT')
    for i,r in enumerate(rows,1):
        o=r["o"]; rs=r["rs"]; nm=o["address"].split(",")[0][:21]
        lo_,hi_=sens[o["slug"]][1],sens[o["slug"]][2]
        print(f'{i:<2} {grade(r["fs"]):3} {nm:21} ${o["list_price"]:>9,} ${r["c"]["day1_p80"]:>7,} '
              f'{r["ppsf"]:>5} ${r["c"]["day1_p80"]+r["c"]["wish_p80"]:>8,} ${rs["arv_mid"]:>10,} '
              f'{rs["recovered_pct"]:>4}% ${rs["sunk"]:>8,} {str(lo_)+"-"+str(hi_):>6}  {r["v"]:<10} {"; ".join(r["notes"])[:34]}')
    print("\nSECOND-BATH OPPORTUNITY (the only intervention that can exceed 100%)")
    for r in rows:
        if r["rs"]["bath_op"]:
            c_,l_,h_=r["rs"]["bath_op"]
            print(f'  {r["o"]["address"].split(",")[0]:24} spend ${c_:,} -> value +${l_:,} to ${h_:,}')
    print("\nSENSITIVITY OF THE ARV BENCHMARK (currently $720/sf Bur, $790/sf Oak)")
    for r in rows[:4]:
        rs=r["rs"]; d=CFG["sensitivity_psf_delta"]*rs["usable"]
        print(f'  {r["o"]["address"].split(",")[0]:24} resale ${rs["arv_mid"]:,}  +/-${d:,.0f} if the benchmark is off by ${CFG["sensitivity_psf_delta"]}/sf')
