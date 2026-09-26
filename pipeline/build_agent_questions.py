#!/usr/bin/env python3
"""Questions for the listing agent, per house, generated from the records. Two standing questions
go to every listing; the rest come from what the photos could not settle."""
import json, csv, os, sys, re, datetime
R=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,R)
import score as S
O={o['address']:o for o in S.load_pool(os.path.join(R,'observations.json'))}
rows=list(csv.DictReader(open(os.path.join(R,'out','decision.csv'))))
def tt(s):   # title case that leaves "Shepherd's" alone
    return re.sub(r"[A-Za-z]+('[A-Za-z]+)?", lambda m: m.group(0)[0].upper()+m.group(0)[1:].lower(), s)
L=[f"# Questions for the listing agents, all {len(rows)} ({datetime.date.today().strftime('%-d %B %Y')})","",
   "Two questions go to every listing: (1) How old are the roof, furnace and A/C, and can you send invoices? (2) Are any photos virtually staged or digitally enhanced, and when were they taken? Below are the house-specific ones, in rank order.",""]
for r in rows:
    o=O[r['address']]; q=[]
    m=o.get('mech_ages_stated')
    if m and 'remarks only' in str(m): q.append(f"The remarks claim {str(m).replace(' (remarks only)','').replace('(remarks only)','').strip()}. Invoices?")
    cve=o.get('claim_vs_evidence'); cve=[cve] if isinstance(cve,str) else (cve or [])
    for c in cve:
        if any(w in c.lower() for w in ('above-ground','does not hold','cannot be verified','which is it')): q.append(c[0].upper()+c[1:])
    if o.get('staging')=='virtually_staged': q.append("Which photos are virtually staged?")
    if o.get('window_frame') in (None,'','not_shown'): q.append("Window frames: original or replaced, and when?")
    if o.get('bath_tub_type')=='not_shown': q.append("The tub is behind a curtain or never shown. Original or replaced?")
    if o.get('basement_ceiling')=='not_shown' and o.get('basement_walls')=='not_shown': q.append("No basement photos at all. Finished? Any water history?")
    if o.get('basement_moisture')=='sump': q.append("Why is there a sump pump, and has it ever run in anger?")
    if not o.get('sqft_below') and 'inish' in str(o.get('basement','')): q.append("Finished basement area in sq ft? (the model is estimating it)")
    if not o.get('year_built'): q.append("Year built? MLS is blank.")
    if o.get('pool')=='in-ground': q.append("Pool: liner, heater and pump ages; last closing; any leak history.")
    if o.get('tenanted'): q.append("Lease end date and vacant-possession terms.")
    if S.eff_year(o) and S.eff_year(o)<1970 and o.get('panel_type') in (None,'','not_shown'): q.append("Panel: fuses or breakers, amperage, any knob-and-tube or aluminum wiring? ESA certificate?")
    if o.get('secondary_bath_original'): q.append("Any plan or permit history on the original second bath?")
    for f in (o.get('red_flags') or [])[:2]:
        if 'ask' in f.lower(): q.append(f[0].upper()+f[1:])
    L.append(f"## {r['rank']}. {tt(r['address'].split(',')[0])} ({r['grade']}, {r['verdict']})")
    L += [f"- {x}" for x in dict.fromkeys(q)] or ["- Only the two standing questions."]
    L.append("")
open(os.path.join(R,'out','agent_questions.md'),'w').write("\n".join(L)); print(len(L),'lines')
