#!/usr/bin/env python3
"""Emit per-listing cost line items + value math for the walkthrough report."""
import json, os, sys
R = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, R)
import score as S

obs = [S.normalise(o) for o in json.load(open(os.path.join(R, "observations.json")))]
out = {}
for o in obs:
    c = S.cost(o); fs, parts = S.facts(o); v, notes = S.verdict(o, c, fs); rs = S.resale(o, c)
    k = 1 + S.cont(S.eff_year(o))
    hst = 1 + S.CFG["meta"]["hst"]
    items = []
    for nm, b, p, lo, ml, hi, basis in c["items"]:
        mean = (lo + 4*ml + hi) / 6
        if b == "reserve":
            life = S.CAT_life(nm)
            items.append({"name": nm, "bucket": b, "p": round(p, 2),
                          "exp": round(p*mean*hst), "lo": round(lo*hst), "hi": round(hi*hst),
                          "life": life, "per_yr": round(p*mean*hst/life), "basis": basis})
        else:
            items.append({"name": nm, "bucket": b, "p": round(p, 2),
                          "exp": round(p*mean*k*hst), "lo": round(lo*k*hst), "hi": round(hi*k*hst),
                          "basis": basis})
    out[o["slug"]] = {
        "addr": o["address"], "list": o["list_price"],
        "items": items,
        "reno": S.reno_list(o, c), "reno_text": S.reno_text(S.reno_list(o, c))[0], "reno_total": S.reno_text(S.reno_list(o, c))[1],
        "day1_p50": c["day1_p50"], "day1_p80": c["day1_p80"],
        "wish_p50": c["wish_p50"], "wish_p80": c["wish_p80"],
        "naive": c["naive_sum_of_p80s"],
        "reserve_monthly": c["reserve_monthly"], "near_term_5yr": c["near_term_5yr"],
        "contingency_pct": round(100*(k-1)), "era_p": S.CFG["p_not_done"][S.era(S.eff_year(o))],
        "yb": S.eff_year(o), "yb_src": ("mls" if o.get("year_built") else "est" if o.get("year_built_est") else "band" if o.get("year_built_details") else "none"),
        "bg_est": S.below_grade(o)[1],
        "usable": rs["usable"], "norm": rs["norm"], "headroom": rs["headroom"],
        "arv_lo": rs["arv_lo"], "arv_mid": rs["arv_mid"], "arv_hi": rs["arv_hi"],
        "recovered_pct": rs["recovered_pct"], "sunk": rs["sunk"], "breakeven": rs["breakeven"],
        "bath_op": rs["bath_op"],
        # SCORING-EXPLANATION-FINAL §1: the ONE source of every number and every scale sentence.
        # The card prints explain[k].fact, the glossary prints explain[k].scale. Nothing about a
        # scale is typed into a template.
        "explain": S.explain_all(o, c),
        # SCORING-EXPLANATION-FINAL §2: the three cost-model buckets, the unseen tells, and
        # what a showing is worth in the score's own units (two more runs of cost()).
        "condition_block": S.condition_block(o, c),
        "fact_score": fs, "fact_parts": {a: round(b, 1) for a, b in parts.items()},
        "grade": S.grade(fs), "verdict": v, "verdict_notes": notes,
        "tax_mo": round((o.get("annual_taxes") or 0)/12),
        "taxes": o.get("annual_taxes"),
        "mech_stated": o.get("mech_ages_stated"),
        "photos": o.get("photos_total") or (o.get("coverage") or {}).get("photos_total"),
        "inv": o.get("photo_inventory"),
        "tier1": o.get("evidence_completeness"),
        "concealed": o.get("concealed_surfaces"), "red_flags": o.get("red_flags"),
        "claim_vs_evidence": o.get("claim_vs_evidence"),
        "defects": o.get("defect_findings"),
        "staging": o.get("staging"), "hdr": o.get("hdr_blowout"),
        "evidence": S.evidence(o)[0], "evidence_notes": S.evidence(o)[2], "cash_to_close": S.cash_to_close(o["list_price"], c["day1_p80"]),
    }
json.dump(out, open(os.path.join(R, "out", "detail.json"), "w"), indent=1)
print(len(out), "listings")
for s in ["bur-3205-tania", "bur-522-enfield"]:
    if s in out:
        d = out[s]
        print("\n", s, d["day1_p80"], d["wish_p80"], d["reserve_monthly"])
        for i in d["items"]:
            print("  ", i["bucket"], i["name"], i["p"], i["exp"])
