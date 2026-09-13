#!/usr/bin/env python3
"""Invariants the model must hold. Run after any change: python3 test_model.py
v3.4 + rank v5: the second block is the invariants from the 2026-09-12 review, section 5.13,
each one written so that it would have failed before the bug it guards was fixed."""
import json, csv, os, sys
R=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,R)
import score as S
obs=[S.normalise(o) for o in json.load(open(os.path.join(R,'observations.json')))]
rows=list(csv.DictReader(open(os.path.join(R,'out','decision.csv'))))
fails=[]
def chk(c,msg):
    if not c: fails.append(msg)
chk(len(rows)==len(obs), "decision.csv row count != observations")
for o in obs:
    c=S.cost(o); fs,_=S.facts(o,c); v,notes=S.verdict(o,c,fs); rs=S.resale(o,c)
    chk(c['day1_p80']>=c['day1_p50'], f"{o['slug']}: p80 < p50")
    k=1+S.cont(S.eff_year(o)); hst=1+S.CFG['meta']['hst']; prem=1+S.CFG['multi_room_premium']
    ceiling=(sum(hi for _,b,_,lo,ml,hi,_ in c['items'] if b!='reserve')+S.CFG['soft_costs_day1']['high'])*k*prem*hst
    chk(c['day1_p80']+c['wish_p80']<=ceiling, f"{o['slug']}: p80 sum exceeds the every-job-at-its-high ceiling")
    chk(S.usable(o)>0, f"{o['slug']}: usable area zero")
    chk(rs['arv_mid']<=rs['norm']+1, f"{o['slug']}: ARV above peer norm")
    chk((v=='STOP')==c['moisture_confirmed'] or any('knob' in n for n in notes), f"{o['slug']}: STOP without a stop condition")
    chk(0<=fs<=100, f"{o['slug']}: fact score out of range")
    for f in S.TELLS:
        chk(f in o, f"{o['slug']}: missing tell field {f}")
    # photos never promote: no field value that lowers p below the floor
    chk(all(p>=0.0 for _,_,p,*x in c['items']), f"{o['slug']}: negative probability")
chk(not S.dedupe_warnings(obs), "duplicate address across records")
# the 20 listings with stated basement areas must not use the estimate
for o in obs:
    if o.get('sqft_below'): chk(S.below_grade(o)[1] is False, f"{o['slug']}: estimate used despite stated area")

# ------------------------------------------------------------------ review 5.13
# Lines that are structure, envelope or mechanical. A finish read at any resolution may never
# lower one of these: their evidence is age, MLS text or the component's own frame, not a photo
# of a surface. (Review 2.7, second sentence.)
MECH = ("panel","partial rewire","rewire","waterproofing","roof","furnace","A/C","water heater","windows")
# Finish reads that feed prob(). Cleaning all of them must not move a MECH line.
FINISH_READS = {"kitchen_sink_mount":"undermount","kitchen_counter_edge":"eased","kitchen_soffit":"absent",
                "kitchen_door_profile":"flat_slab","bath_tub_type":"alcove","bath_tile_scale":"large_format",
                "bath_vanity_top":"stone","floor_condition":"no_defect_seen","ceiling_main":"flat_painted",
                "basement_ceiling":"drywall","basement_walls":"drywall"}
for o in obs:
    c = S.cost(o); b = str(o.get("basement") or "")
    ps = {nm: p for nm,bk,p,lo,ml,hi,bs in c["items"]}
    basis = {nm: bs for nm,bk,p,lo,ml,hi,bs in c["items"]}

    # 5.1 basement text: "Unfinished" is not a finished basement
    chk(S.usable(o)==(o.get("sqft_above") or 0) or "Unfinished" not in b,
        f"{o['slug']}: usable counts below-grade area on an Unfinished basement")
    chk(not S.below_grade(o)[1] or ("Finished" in b and "Unfinished" not in b),
        f"{o['slug']}: below-grade area estimated on a basement string with no 'Finished'")
    # 5.2 a partial finish is not a full one
    if not o.get("sqft_below") and "Partially" in b:
        chk(S.below_grade(o)[0] <= round(S.CFG["below_grade_estimate_factor_partial"]*(o.get("sqft_above") or 0)/1) + 1,
            f"{o['slug']}: 'Partially Finished' estimated at the full-finish factor")
    # 5.3 a Walk-Up is stairs, not daylight: it does not earn the walk-out weight
    ag = o.get("sqft_above") or 0; bg = S.below_grade(o)[0]
    if bg and "Walk-Up" in b and "Walk-Out" not in b and "Walkout" not in b:
        chk(abs(S.usable(o) - (ag + S.CFG["below_grade_weight"]*bg)) < 1e-9,
            f"{o['slug']}: Walk-Up basement given the walk-out weight")
    # 5.4 a clean finish read may never lower a structure / envelope / mechanical line
    o2 = dict(o); o2.update(FINISH_READS)
    ps2 = {nm: p for nm,bk,p,lo,ml,hi,bs in S.cost(S.normalise(o2))["items"]}
    for nm in MECH:
        if nm in ps:
            chk(nm in ps2 and ps2[nm] >= ps[nm] - 1e-9,
                f"{o['slug']}: clean finish reads lowered the {nm} line")
    # 5.4 a concealed floor cannot reach the observed floor
    if S._floor_concealed(o) and "flooring" in ps:
        chk(ps["flooring"] > S.CFG["observed_floor"] + 1e-9,
            f"{o['slug']}: concealed floor read down to the observed floor")
    # 5.5 unknown build year is worst case everywhere, electrical included
    if not S.eff_year(o):
        chk(S.era(S.eff_year(o))=="pre_1990", f"{o['slug']}: unknown year not treated as pre-1990")
        if o.get("panel_type") in (None,"","not_shown","fuse"):
            chk("panel" in ps, f"{o['slug']}: unknown year skipped the pre-1970 electrical block")
    # 5.6 oil to gas already buys the furnace: no second furnace in the reserve
    chk(not any(n=="oil→gas" for n in ps) or "furnace" not in ps,
        f"{o['slug']}: furnace charged twice (oil→gas plus the furnace reserve)")
    # 5.11 contingency is applied to day1 and wishlist, once, and never to reserve
    chk(all(bk in ("day1","wishlist","reserve") for _,bk,*_ in c["items"]),
        f"{o['slug']}: unknown cost bucket")

# ------------------------------------------------------------------ rank v6
# The v5 invariants about lambda, rank_value, fit_dollars_mo and the frontier ORDER are gone with
# the rule they guarded. Overpay is still computed, so its internal consistency is still checked.
COMP = S.COMP_KEYS
HD = S.CFG["hold"]["years_default"]
WS = S.weight_sets()
ranked = [r for r in rows if r["rank"] != "-"]
gated  = [r for r in rows if r["rank"] == "-"]
chk(len(ranked)+len(gated)==len(rows), "ranked + gated != rows")
chk(len(ranked)>0, "nothing ranked")

# 6.1 the order is the score, descending, and rank is the row position
for i,r in enumerate(ranked,1):
    chk(int(r["rank"])==i, f"{r['address']}: rank column is not the row position")
for a,b in zip(ranked, ranked[1:]):
    chk(float(a["score"]) >= float(b["score"]) - 0.05,
        f"decision.csv is not sorted on score descending at {a['address']} / {b['address']}")

# 6.2 every component is on the absolute 0 to 100 scale
for r in rows:
    for k in COMP:
        v = float(r["c_"+k])
        chk(0.0 <= v <= 100.0, f"{r['address']}: component {k} out of [0,100]: {v}")

# 6.3 the score. PRICE-REFRAME (2026-09-15): with the reframe on, `quality` is the weighted mean
# of the SEVEN non-price components renormalised over those seven and docked for a split, and
# `score` is that quality minus the dial's share of the cost penalty. The dock applies to quality
# only: it is a statement about the house, not about the mortgage payment.
for r in ranked:
    comp = {k: float(r["c_"+k]) for k in COMP}
    w = WS["joint"]
    if S.reframed():
        q7 = [k for k in COMP if k != "price"]
        t = sum(w[k] for k in q7) or 1.0
        expect_q = sum(w[k]*comp[k] for k in q7) / t
        if r["split_docked"] == "yes": expect_q *= S.CFG["split_dock"]
        chk(abs(expect_q - float(r["quality"])) <= 0.15,
            f"{r['address']}: quality {r['quality']} is not the weighted mean of the seven ({expect_q:.2f})")
        expect = expect_q - float(r["dial"]) * float(r["cost_pen"]) / 100.0
        chk(abs(expect - float(r["score"])) <= 0.15,
            f"{r['address']}: score {r['score']} is not quality minus the dial's share of the cost penalty ({expect:.2f})")
        chk(abs(float(r["cost_pts"]) - float(r["dial"])*float(r["cost_pen"])/100.0) <= 0.15,
            f"{r['address']}: cost_pts does not equal dial x cost_pen / 100")
    else:
        expect = sum(w[k]*comp[k] for k in COMP)
        if r["split_docked"] == "yes": expect *= S.CFG["split_dock"]
        chk(abs(expect - float(r["score"])) <= 0.15,
            f"{r['address']}: score {r['score']} is not the weighted mean of its components ({expect:.2f})")
    chk((r["split_docked"]=="yes") == ("plit" in str(next(o for o in obs if o['address']==r['address']).get('style',''))),
        f"{r['address']}: split dock flag does not match the style")

# 6.4 PHOTOGRAPHS CANNOT REACH THE TOP OF THE CONDITION RANGE (v6 §3, bound 4).
# Without a showing-record year or a _seen field, condition is capped by construction at about
# 77: the observed floor is 0.15, not 0, and p_hold keeps the mechanicals in the sum.
for r in rows:
    if r["seen_evidence"] != "yes":
        chk(float(r["c_condition"]) <= 80.0,
            f"{r['address']}: condition {r['c_condition']} above 80 with no showing evidence (the photo cap is broken)")

# 6.5 condition is the cost-weighted share of work NOT expected, and work_expected <= work_full
for r in rows:
    e, fl = float(r["work_expected"]), float(r["work_full"])
    chk(e <= fl + 1, f"{r['address']}: expected work exceeds the every-job total")
    chk(abs(100*(1 - e/fl) - float(r["c_condition"])) <= 0.6 if fl else True,
        f"{r['address']}: c_condition is not 100 x (1 - expected / full)")

# 6.6 SCORE IS MONOTONE IN EACH WEIGHT. Raising one weight by 10 (raw, before normalising) never
# lowers the rank of the house that is best in the batch on that component.
base = dict(S.CFG["weights"]["alex"])
rowsm = S.prepare(os.path.join(R, "observations.json"))
live = [x for x in rowsm if not x["gated"]]
def order(wraw):
    wn = S.norm_weights(wraw)
    srt = sorted(live, key=lambda x: (-S.v6_score(x["comp"], wn, x["split"]), x["slug"]))
    return {x["slug"]: i for i,x in enumerate(srt,1)}
o0 = order(base)
for k in COMP:
    best = max(live, key=lambda x: (x["comp"][k], x["slug"]))
    up = dict(base); up[k] = up[k] + 10
    o1 = order(up)
    chk(o1[best["slug"]] <= o0[best["slug"]],
        f"raising the {k} weight lowered the rank of {best['o']['address']}, the batch's best on {k}")

# 6.7 p_hold. A confirmed-original component is certain over any hold; a brand new one is H/life;
# an annual carry is paid H times.
chk(S.p_hold(5, 30, 5, confirmed_original=True) == 1.0, "p_hold: confirmed original is not 1.0")
chk(abs(S.p_hold(0, 20, 5) - 0.25) < 1e-9, "p_hold: a new 20-year component over 5 years is not H/life")
chk(S.p_hold(25, 20, 5) == 1.0, "p_hold: a component past due inside 1.5 lives is not 1.0")
chk(abs(S.p_hold(60, 20, 5) - 0.25) < 1e-9, "p_hold: an old component is not uniform over the cycle")
chk(S.p_hold(1, 1, 5) == 5.0, "p_hold: an annual carry is not paid H times")
# and the review 5.7 case: Wyandotte's confirmed-original windows reach the money over the hold
for o in obs:
    if o.get("window_frame") in ("aluminum_original","wood_original","original"):
        c = S.cost(o); meta = c["reserve_meta"]
        chk(meta.get("windows", (0,0,False))[2] is True,
            f"{o['slug']}: confirmed-original windows not marked confirmed")
        hst = 1 + S.CFG["meta"]["hst"]
        mean = next((lo+4*ml+hi)/6 for nm,b,p,lo,ml,hi,_ in c["items"] if nm=="windows")
        chk(S.reserve_over_hold(c, 5) >= mean*hst - 1,
            f"{o['slug']}: the window reserve does not reach full cost over a 5-year hold")

# 6.8 the pool carry is a priced reserve line wherever a pool is detected, and the stamp survives
for o in obs:
    c = S.cost(o); names = [nm for nm,*_ in c["items"]]
    chk(("pool carry" in names) == (S.pool_kind(o) == "in-ground"),
        f"{o['slug']}: pool carry line does not match the pool detection")

# 6.9 the cost of capital is derived, not asserted
chk("cost_of_capital" not in S.CFG["hold"], "hold.cost_of_capital is still a free key in costs.yaml")
d = S.CFG["hold"]["down_payment"]
chk(abs(S.COST_OF_CAPITAL - ((1-d)*S.CFG["hold"]["mortgage_rate"] + d*S.CFG["hold"]["opportunity_rate"])) < 1e-12,
    "COST_OF_CAPITAL is not derived from the mortgage and opportunity rates")

# 6.10 the retired v5 columns and keys are gone
for dead in ("rank_value","fit_dollars_mo"):
    chk(dead not in rows[0], f"decision.csv still carries the retired column {dead}")
chk("dollars_per_fit_point_mo" not in S.CFG.get("rank", {}),
    "costs.yaml still carries rank.dollars_per_fit_point_mo")
src = open(os.path.join(R,"score.py")).read()
chk("dollars_per_fit_point_mo" not in src, "score.py still references dollars_per_fit_point_mo")

# 6.11 gated rows carry '-' everywhere a rank would go, never a number above 90
for r in gated:
    for col in ("rank","score","rank_alex","band_lo","band_hi","rank_3","rank_10"):
        chk(r[col] == "-", f"{r['address']}: gated row has {col}={r[col]}, expected '-'")
for r in ranked:
    chk(1 <= int(r["rank"]) <= len(ranked), f"{r['address']}: rank outside 1..n")
    chk(int(r["band_lo"]) <= int(r["rank"]) <= int(r["band_hi"]),
        f"{r['address']}: rank {r['rank']} outside its own band {r['band_lo']}-{r['band_hi']}")

# 6.12 overpay is still computed and internally consistent, and is no longer the order
for r in ranked:
    if float(r["overpay_mo"]) == 0:
        chk(r["dominated_by"] == "-", f"{r['address']}: overpay 0 but a dominating house is named")
        chk(float(r["overpay_total"]) == 0, f"{r['address']}: overpay_mo 0 but overpay_total is not")
    else:
        chk(r["dominated_by"] not in ("-",""), f"{r['address']}: overpay > 0 with no dominating house")

# 6.13 the hold-cost parts still sum to the hold cost
for r in rows:
    parts = sum(float(r["own_"+k]) for k in ("day1_sunk","capital","taxes","reserve","closing"))
    chk(abs(parts/(12*float(r["hold_years"])) - float(r["own_mo"])) <= 1.0,
        f"{r['address']}: hold-cost parts do not sum to the monthly figure")

# 6.14 G4: a project is stamped, and only gated when the buyer said no projects
share = S.CFG["gates"].get("project_share_of_ask", 0.15)
for r in rows:
    exp = float(r["work_expected"]); ask = float(r["ask"])
    chk((r["project"] == "yes") == (exp > share*ask),
        f"{r['address']}: Project stamp does not match work_expected / ask")
    if r["project"] == "yes" and not S.CFG["gates"].get("no_projects"):
        chk(r["rank"] != "-" or "STOP" in r["notes"] or r["verdict"] == "STOP",
            f"{r['address']}: a project was excluded although no_projects is false")

# 6.15 the photos_may_lower_p switch. With it off, a photographic read no longer moves a line.
chk("photos_may_lower_p" in (S.CFG.get("condition") or {}), "condition.photos_may_lower_p is missing")


# ================================================= PRICE-REFRAME.md, 2026-09-15
# 6.16 the reframe identity. Ranking on `quality - dial * cost_pen / 100` differs from the old
# eight-component weighted mean only by an affine transform, so with the style dock neutralised
# the two orders must be identical. With the dock live they may differ, and that difference is
# deliberate: the dock applies to quality only and no longer discounts the mortgage payment.
if S.reframed():
    _rows = S.prepare("observations.json")
    _WS = S.weight_sets(); _HD = S.CFG["hold"]["years_default"]
    _live = [r for r in _rows if not r["gated"]]
    for r in _live: r["comp"] = r["comps"][_HD]
    _old = [r["slug"] for r in sorted(_live, key=lambda r: (-S.v6_score(r["comp"], _WS["joint"], False), r["slug"]))]
    _new = [r["slug"] for r in sorted(_live, key=lambda r: (-S.value_of(r["comp"], _WS["joint"], False, r["cost_pen"]), r["slug"]))]
    chk(_old == _new, "the price reframe changes the order even with the style dock neutralised; "
                      "dial should be 100 * w_price / (100 - w_price)")
    # and the dock-live difference must stay small and confined to splits and their neighbours
    _o2 = [r["slug"] for r in sorted(_live, key=lambda r: (-S.v6_score(r["comp"], _WS["joint"], r["split"]), r["slug"]))]
    _n2 = [r["slug"] for r in sorted(_live, key=lambda r: (-S.value_of(r["comp"], _WS["joint"], r["split"], r["cost_pen"]), r["slug"]))]
    _po = {s2: i for i, s2 in enumerate(_o2, 1)}; _pn = {s2: i for i, s2 in enumerate(_n2, 1)}
    chk(max(abs(_po[s2]-_pn[s2]) for s2 in _po) <= 3,
        "the style dock moving out of the cost term displaces a house by more than three places")

# 6.17 the cost penalty and the old price component are the same number, complemented
for r in rows:
    if r["rank"] == "-": continue
    chk(abs((100.0 - float(r["cost_pen"])) - float(r["c_price"])) < 0.05,
        f"{r['address']}: cost_pen and c_price disagree; they must be complements")

# 6.18 nothing may carry "/mo" except the monthly payment, and the payment must be its parts
for r in rows:
    p_ = float(r["pay_pi"]) + float(r["pay_tax"]) + float(r["pay_upkeep"])
    chk(abs(p_ - float(r["pay_mo"])) <= 1.5,
        f"{r['address']}: monthly payment does not equal P&I + tax + upkeep")

# 6.19 the dial must be declared provisional while no choices are on file
_P = S.CFG.get("price") or {}
if S.reframed() and not (S.CFG.get("choices") or {}).get("alex"):
    chk(_P.get("dial_provisional") is True,
        "the dial is not marked provisional although no pairwise choices are on file")


# ============================== SCORING-EXPLANATION-FINAL.md §1, 2026-09-15
# 6.20 ONE SOURCE. Every number the card prints and every sentence the glossary prints about a
# scale must come from explain_<component>(), and explain_<component>() must reproduce exactly
# what components() scores. This is the check that would have caught the 14 September build,
# where Barberry printed price 100 under a sentence describing the $54k/$84k band (which gives
# 37) and lot 23 under a sentence saying 4,000 sq ft scores 0 (which gives 0).
_obs = [S.normalise(o) for o in json.load(open(os.path.join(R, "observations.json")))]
for _o in _obs:
    _c = S.cost(_o)
    _comp, _fs2, _p2, _e2 = S.components(_o, _c, S.CFG["hold"]["years_default"])
    _ex = S.explain_all(_o, _c)
    for _k in ("space", "layout", "baths", "parking", "lot", "location", "condition", "price"):
        chk(abs(_ex[_k]["score"] - _comp[_k]) < 0.15,
            f"{_o['address']}: explain_{_k} says {_ex[_k]['score']} but components() says {_comp[_k]:.1f}")
        chk(bool(_ex[_k]["fact"]) and bool(_ex[_k]["scale"]),
            f"{_o['address']}: explain_{_k} returned an empty fact or scale")

# 6.21 the scale sentences must quote the anchors that are live in costs.yaml right now. A scale
# text that has drifted from the config is the exact failure mode this pair of tests exists for.
_o0 = _obs[0]; _ex0 = S.explain_all(_o0, S.cost(_o0))
def _has(txt, n): return f"{n:,}" in txt or str(n) in txt
_L = S.CFG.get("lot") or {}
if _L.get("matters", True):
    chk(_has(_ex0["lot"]["scale"], _L["floor_sqft"]) and _has(_ex0["lot"]["scale"], _L["cap_sqft"]),
        "the lot scale sentence does not quote lot.floor_sqft and lot.cap_sqft")
_sp = S.CFG["fit_weights"]["space"]
chk(_has(_ex0["space"]["scale"], _sp["floor_sqft"]) and _has(_ex0["space"]["scale"], _sp["knee_sqft"]),
    "the space scale sentence does not quote fit_weights.space floor and knee")
_P2 = S.CFG["price"]
chk(_has(_ex0["price"]["scale"], _P2["comfortable_mo"]) and _has(_ex0["price"]["scale"], _P2["max_mo"]),
    "the price scale sentence does not quote price.comfortable_mo and price.max_mo")
chk("54,000" not in _ex0["price"]["scale"] and "84,000" not in _ex0["price"]["scale"],
    "the price scale sentence still quotes the old search-band anchors")
chk("4,000" not in _ex0["lot"]["scale"] or _L.get("floor_sqft") == 4000,
    "the lot scale sentence still quotes the old 4,000 sq ft floor")


# 6.22 the condition block. The clean scenario cannot be worse than today and the defect scenario
# cannot be better, because resolving an unseen tell clean can only lower a probability and
# resolving it as a defect can only raise one. A house with no unseen tells has no swing.
for _o in _obs:
    _cb = S.condition_block(_o)
    chk(_cb["if_clean"] >= _cb["score"] - 0.15,
        f"{_o['address']}: the clean showing scenario scores below today's condition")
    chk(_cb["if_defect"] <= _cb["score"] + 0.15,
        f"{_o['address']}: the defect showing scenario scores above today's condition")
    if not _cb["unseen"]:
        chk(abs(_cb["if_clean"] - _cb["if_defect"]) < 0.15,
            f"{_o['address']}: no unseen tells but the two showing scenarios differ")
    chk(sum(b["total"] for b in _cb["buckets"]) > 0 or _cb["expected"] == 0,
        f"{_o['address']}: condition buckets are empty but work is expected")
    # the defect scenario must never manufacture a hard stop
    chk("efflorescence" not in S.DEFECT_READ.values(),
        "the defect scenario uses efflorescence, which is a hard STOP")

print("PASS" if not fails else "FAIL"); [print(" -",f) for f in fails]; sys.exit(1 if fails else 0)
