#!/usr/bin/env python3
"""Render deliverables/renovation-cost-detail.md from out/detail.json + out/decision.csv.
Run after score.py and export_detail.py (refresh.sh does this)."""
import csv, json, os, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
det = json.load(open(os.path.join(HERE, "out/detail.json")))
rows = list(csv.DictReader(open(os.path.join(HERE, "out/decision.csv"))))
import yaml, re
VER = yaml.safe_load(open(os.path.join(HERE, "costs.yaml")))["meta"]["version"]
def tt(s):   # title case that leaves "Shepherd's" alone
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda m: m.group(0)[0].upper()+m.group(0)[1:].lower(), s)
today = datetime.date.today().strftime("%-d %B %Y")

def money(v):
    try: return f"${int(round(float(v))):,}"
    except (TypeError, ValueError): return "-"

def pct(p): return f"{int(round(float(p)*100))}%"

out = [f"# Renovation cost detail, all {len(rows)} listings", "",
       f"Model v{VER}, {today}. Every line: probability the job is needed, expected cost "
       "(probability-weighted, HST and era contingency included), and the low/high range if the job is done. "
       "Day-one and wish-list totals are p80 of 4,000 simulated draws on the sum. Evidence grade says how much of "
       "the number rests on photos versus base rates; the rank band is where the listing lands if the unobserved "
       "items flip.", ""]

by_addr = {}
for k, d in det.items():
    by_addr[d["addr"]] = (k, d)

for r in rows:
    addr = r["address"]
    k, d = by_addr.get(addr, (None, None))
    if d is None:
        print("no detail for", addr, file=sys.stderr); continue
    short = tt(addr.split(",")[0])
    band = f"{r['rank_p10']}–{r['rank_p90']}" if r.get("rank_p10","-") not in ("-","") else "-"
    ev = r.get("evidence", "")
    evn = r.get("evidence_notes", "")
    out.append(f"## {r['rank']}. {short}: grade {r['grade']}, ${r['all_in_psf']}/usable sq ft, {r['verdict']}")
    line = (f"Ask {money(r['ask'])} · day-one p80 {money(r['day1_p80'])} · wish list p80 {money(r['wishlist_p80'])} · "
            f"reserve ${d['reserve_monthly']}/mo · year used {r['year_used']} ({r['year_src']}) · usable {int(r['usable_sqft']):,} sq ft"
            f"{' (basement estimated)' if r.get('bg_sqft_est')=='est' else ''} · tells settled {r['tells_seen_of_15']}/15 of {r['photos_total']} photos · "
            f"evidence {ev}{(' ('+evn+')') if evn else ''} · rank band {band} · cash to close at 20% {money(r['cash_to_close_20pct'])}")
    reno = d.get("reno") or []
    needed = [i for i in reno if i["status"] != "possible"]; maybe = [i for i in reno if i["status"] == "possible"]
    if needed:
        out += ["", "**Renovations needed:** " + "; ".join(f"{i['name']} ${i['cost']//1000}k" + (" (unseen)" if i["status"]=="likely, unseen" else "") for i in needed)
                + f", ${sum(i['cost'] for i in needed)//1000}k if you do all of it" + (". Possible: " + ", ".join(f"{i['name']} ${i['cost']//1000}k ({int(round(i['p']*100))}%)" for i in maybe) if maybe else "")]
    out += [line, "", "| Bucket | Line | P(needed) | Expected | Low | High | Basis |", "|---|---|---|---|---|---|---|"]
    for it in d["items"]:
        out.append(f"| {it['bucket']} | {it['name']} | {pct(it['p'])} | {money(it['exp'])} | {money(it['lo'])} | {money(it['hi'])} | {it.get('basis','')} |")
    out += ["", f"Resale after the work {money(d['arv_lo'])} to {money(d['arv_hi'])} (mid {money(d['arv_mid'])}); "
            f"peer norm {money(d['norm'])}; recovered {d['recovered_pct']}%; sunk {money(d['sunk'])}; break-even {money(d['breakeven'])}."]
    if d.get("verdict_notes"):
        out += ["", "Verdict notes: " + " · ".join(d["verdict_notes"])]
    if d.get("red_flags"):
        out += ["", "Red flags: " + " · ".join(d["red_flags"])]
    if d.get("concealed"):
        out += ["", "Concealed in the photos: " + " · ".join(d["concealed"])]
    cve = d.get("claim_vs_evidence")
    if cve:
        if isinstance(cve, list): cve = " ".join(str(x) for x in cve)
        out += ["", "Claim vs evidence: " + cve]
    out.append("")

dst = os.path.join(HERE, "..", "deliverables", "renovation-cost-detail.md")
open(dst, "w").write("\n".join(out))
print("wrote", os.path.relpath(dst), len(rows), "listings")
