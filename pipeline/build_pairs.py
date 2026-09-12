#!/usr/bin/env python3
"""Choose the fifteen house pairs the buyers answer on the page, and write out/pairs.json.

Correction of 14 September, item 2. Swing weighting asked for eight numbers and got none, so the
elicitation becomes fifteen forced choices between real houses in this batch, and the weights are
fitted from the choices (score.py: fit_weights_from_choices).

Selection is D-optimal on the DIFFERENCE vectors. For a logistic choice model the Fisher
information is proportional to sum over pairs of d d-transpose, so maximising log det of that sum
is maximising the precision of the fitted weights, and it is the standard construction for a
paired-comparison design. Greedy forward selection, because fifteen from ~630 candidate pairs is a
combinatorial problem and the greedy determinant step is the usual practical answer.

Constraints, from the correction:
  * every component in at least three pairs with |d_k| >= swing_gap (default 30). A pair where two
    houses are three points apart on lot teaches the fit nothing about the lot weight.
  * no house in more than max_appearances_per_house pairs (default 4). Variety, and it stops one
    unusual house driving the whole fit.
  * no pair where one house is at least as good as the other on all eight. There is no preference
    to learn from a choice anyone would make the same way.

Usage: python3 build_pairs.py
"""
import json, os, sys, random
import numpy as np

R = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, R)
import score as S

K = list(S.COMP_KEYS)
P = S.CFG.get("pairs") or {}
N_PAIRS   = int(P.get("n", 15))
GAP       = float(P.get("swing_gap", 30))
MIN_PER_K = int(P.get("min_pairs_per_component", 3))
MAX_APP   = int(P.get("max_appearances_per_house", 4))

def dominates(a, b):
    """a is at least as good as b on all eight."""
    return all(a[k] >= b[k] - 1e-9 for k in K)

def candidates(rows):
    out = []
    for i in range(len(rows)):
        for j in range(i+1, len(rows)):
            A, B = rows[i], rows[j]
            ca, cb = A["comp"], B["comp"]
            if dominates(ca, cb) or dominates(cb, ca):
                continue
            d = np.array([ca[k] - cb[k] for k in K], dtype=float)
            out.append({"a": A, "b": B, "d": d})
    return out

def logdet_gain(Minv, d):
    """log det(M + d d') - log det(M) = log(1 + d' M^-1 d)."""
    return float(np.log1p(d @ Minv @ d))

def select(cands, rng):
    lam = 1.0                                  # ridge on the information matrix, in component-points^2
    M = np.eye(len(K)) * lam
    chosen, appear = [], {}
    def ok(c):
        return (appear.get(c["a"]["slug"], 0) < MAX_APP and
                appear.get(c["b"]["slug"], 0) < MAX_APP and c not in chosen)
    def take(c, why):
        chosen.append(c); c["why"] = why
        appear[c["a"]["slug"]] = appear.get(c["a"]["slug"], 0) + 1
        appear[c["b"]["slug"]] = appear.get(c["b"]["slug"], 0) + 1
        return M + np.outer(c["d"], c["d"])

    # Phase 1: satisfy the per-component coverage first, scarcest component first, so the
    # unconstrained determinant step cannot spend all fifteen pairs on the wide components.
    need = {k: MIN_PER_K for k in K}
    supply = {k: sum(1 for c in cands if abs(c["d"][K.index(k)]) >= GAP) for k in K}
    short = [k for k in K if supply[k] < MIN_PER_K]
    if short:
        raise SystemExit(
            "build_pairs: the three-pairs-per-component constraint cannot be met on this batch for "
            + ", ".join(f"{k} (only {supply[k]} candidate pairs with |d| >= {GAP:.0f})" for k in short)
            + ". Stop and ask the owner before relaxing swing_gap or min_pairs_per_component.")
    for k in sorted(K, key=lambda k: supply[k]):
        ki = K.index(k)
        while need[k] > 0:
            pool = [c for c in cands if abs(c["d"][ki]) >= GAP and ok(c)]
            if not pool:
                raise SystemExit(
                    f"build_pairs: ran out of usable pairs for {k} under "
                    f"max_appearances_per_house={MAX_APP}. Stop and ask the owner.")
            Minv = np.linalg.inv(M)
            best = max(pool, key=lambda c: logdet_gain(Minv, c["d"]))
            M = take(best, f"covers {k} (|d| = {abs(best['d'][ki]):.0f})")
            for kk in K:
                if abs(best["d"][K.index(kk)]) >= GAP: need[kk] = max(0, need[kk] - 1)
            if len(chosen) >= N_PAIRS: return chosen, appear

    # Phase 2: fill to fifteen on the determinant alone.
    while len(chosen) < N_PAIRS:
        pool = [c for c in cands if ok(c)]
        if not pool:
            raise SystemExit("build_pairs: no pairs left under the appearance cap. Stop and ask the owner.")
        Minv = np.linalg.inv(M)
        best = max(pool, key=lambda c: logdet_gain(Minv, c["d"]))
        wide = sorted(K, key=lambda k: -abs(best["d"][K.index(k)]))[:2]
        M = take(best, "widest on " + " and ".join(
            f"{k} ({abs(best['d'][K.index(k)]):.0f})" for k in wide))
    return chosen, appear

def one_line(o):
    """One line from the record, for the card. The listing's own words, trimmed."""
    t = str(o.get("notes") or o.get("notes_stage1") or o.get("remarks") or "").strip()
    t = " ".join(t.split())
    return (t[:150] + "...") if len(t) > 150 else (t or "-")

def main():
    rows = [r for r in S.prepare(os.path.join(R, "observations.json")) if not r["gated"]]
    cands = candidates(rows)
    chosen, appear = select(cands, random.Random(20260914))
    # Fixed random presentation order, and a fixed A/B side per pair, so the order of the fifteen
    # carries no information and both people see the same thing.
    rng = random.Random(20260914)
    rng.shuffle(chosen)
    out = {"built": "2026-09-14", "n": len(chosen), "components": K,
           "swing_gap": GAP, "min_pairs_per_component": MIN_PER_K,
           "max_appearances_per_house": MAX_APP, "pairs": []}
    for i, c in enumerate(chosen, 1):
        A, B = (c["a"], c["b"]) if rng.random() < 0.5 else (c["b"], c["a"])
        def side(r):
            return {"slug": r["slug"], "address": r["o"]["address"],
                    "street": S.short_street(r["o"]["address"]),
                    "ask": r["ask"], "grade": r["grade"],
                    "comp": {k: round(r["comp"][k], 1) for k in K},
                    "line": one_line(r["o"])}
        out["pairs"].append({"id": f"p{i:02d}", "why": c["why"], "A": side(A), "B": side(B),
                             "d": {k: round(float(A["comp"][k] - B["comp"][k]), 1) for k in K}})
    os.makedirs(os.path.join(R, "out"), exist_ok=True)
    json.dump(out, open(os.path.join(R, "out", "pairs.json"), "w"), indent=1)

    cov = {k: sum(1 for p in out["pairs"] if abs(p["d"][k]) >= GAP) for k in K}
    print(f'wrote out/pairs.json: {len(out["pairs"])} pairs from {len(cands)} candidates')
    print("coverage (pairs with |d| >= %.0f): " % GAP + "  ".join(f"{k} {cov[k]}" for k in K))
    print("appearances: max %d, houses used %d" % (max(appear.values()), len(appear)))
    for p in out["pairs"]:
        print(f'  {p["id"]}  {p["A"]["street"]:14} vs {p["B"]["street"]:14}  {p["why"]}')

if __name__ == "__main__":
    main()
