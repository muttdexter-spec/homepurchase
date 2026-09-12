#!/usr/bin/env python3
"""Invariants the model must hold. Run after any change: python3 test_model.py"""
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
    c=S.cost(o); fs,_=S.facts(o); v,notes=S.verdict(o,c,fs); rs=S.resale(o,c)
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
print("PASS" if not fails else "FAIL"); [print(" -",f) for f in fails]; sys.exit(1 if fails else 0)
