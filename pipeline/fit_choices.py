#!/usr/bin/env python3
"""Fit one person's eight weights from their fifteen pairwise choices.

Correction of 14 September, item 2. The model is the usual paired-comparison logit: the chance a
person picks house A over house B is sigmoid(beta * w . (comp_A - comp_B) / 100), with w >= 0 and
sum(w) = 100 so the fitted numbers are on the same 0-to-100 scale as everything else on the page
and stay interpretable as shares of the score. beta is a free consistency parameter: a decisive
respondent fits a large beta, a noisy one a small beta, and beta does not change the ranking.

Shrinkage. Fifteen choices are not many for eight weights, so the fit is ridged toward the prior
already on file (the rank-order centroid numbers, which are explicitly provisional). The ridge
strength is not picked by taste: calibrate_ridge() finds the LARGEST lambda under which a
perfectly consistent respondent still moves every DESIGN-SUPPORTED weight by at least
pairs.ridge_min_move points. A component the fifteen pairs cannot speak to stays near its prior,
and that is the honest answer for it.

Nothing here runs on a partial set. Fifteen answers or none.
"""
import json, os, sys
import numpy as np
from scipy.optimize import minimize

R = os.path.dirname(os.path.abspath(__file__))

def _cfg():
    import yaml
    return yaml.safe_load(open(os.path.join(R, "costs.yaml")))

def load_pairs():
    p = os.path.join(R, "out", "pairs.json")
    if not os.path.exists(p): return None
    return json.load(open(p))

def design(pairs, choices):
    """(D, y): D is fifteen difference vectors A minus B; y is +1 when A was picked."""
    K = pairs["components"]
    by = {c["pair"]: c["pick"] for c in choices}
    D, y, ids = [], [], []
    for pr in pairs["pairs"]:
        if pr["id"] not in by: continue
        D.append([pr["d"][k] for k in K])
        y.append(1.0 if str(by[pr["id"]]).upper() == "A" else -1.0)
        ids.append(pr["id"])
    return np.array(D, float), np.array(y, float), ids

def _nll(theta, D, y, prior, lam):
    w = theta[:-1]; beta = np.exp(theta[-1])
    z = y * beta * (D @ w) / 100.0
    ll = -np.logaddexp(0.0, -z).sum()
    return -ll + lam * float(np.sum((w - prior)**2))

def fit_once(D, y, prior, lam):
    n = len(prior)
    cons = [{"type": "eq", "fun": lambda t: float(np.sum(t[:-1]) - 100.0)}]
    bnds = [(0.0, 100.0)]*n + [(-4.0, 4.0)]
    t0 = np.concatenate([prior, [0.0]])
    r = minimize(_nll, t0, args=(D, y, prior, lam), method="SLSQP",
                 bounds=bnds, constraints=cons, options={"maxiter": 500, "ftol": 1e-9})
    w = np.clip(r.x[:-1], 0.0, None)
    s = w.sum() or 1.0
    return w * 100.0 / s, float(np.exp(r.x[-1])), bool(r.success)

def supported(D, gap):
    """Components the design can actually speak to: at least three pairs with |d_k| >= gap."""
    return [k for k in range(D.shape[1]) if int((np.abs(D[:, k]) >= gap).sum()) >= 3]

def calibrate_ridge(D, prior, gap, min_move):
    """The largest lambda under which a perfectly consistent respondent still moves every
    design-supported weight by at least min_move points.

    Returns (lambda, supported, probe_moves). Falling through to lambda 0 is not a failure: zero
    is the least shrinkage there is, so it is the setting that permits the most movement. What it
    means is that some component cannot be moved min_move points by these fifteen pairs at any
    shrinkage, and probe_moves names it so the report can say so instead of hiding it."""
    sup = supported(D, gap); best = None
    for lam in (3.0, 1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001, 0.0):
        moves = {}
        for k in sup:
            target = prior.copy(); target[k] += 25.0
            target = target * 100.0 / target.sum()
            ysyn = np.sign(D @ target); ysyn[ysyn == 0] = 1.0
            w, _b, _s = fit_once(D, ysyn, prior, lam)
            moves[k] = float(w[k] - prior[k])
        if best is None or lam == 0.0: best = (lam, moves)
        if all(v >= min_move for v in moves.values()): return lam, sup, moves
    return best[0], sup, best[1]

def fit(person, cfg=None, pairs=None):
    """Returns None when the person has not answered all fifteen. Otherwise the fitted weights
    and everything needed to report them honestly."""
    cfg = cfg or _cfg(); pairs = pairs or load_pairs()
    if not pairs: return None
    choices = ((cfg.get("choices") or {}).get(person)) or []
    if len(choices) < pairs["n"]: return None
    K = pairs["components"]
    D, y, ids = design(pairs, choices)
    if len(ids) < pairs["n"]: return None
    pw = (cfg.get("weights") or {}).get(person)
    prior = np.array([float(pw[k]) for k in K], float) if isinstance(pw, dict) else np.full(len(K), 100.0/len(K))
    prior = prior * 100.0 / prior.sum()
    gap = float((cfg.get("pairs") or {}).get("swing_gap", 30))
    mm = float((cfg.get("pairs") or {}).get("ridge_min_move", 10))
    lam, sup, probe = calibrate_ridge(D, prior, gap, mm)
    w, beta, ok = fit_once(D, y, prior, lam)

    pred = np.sign(D @ w); pred[pred == 0] = 1.0
    agree = [ids[i] for i in range(len(ids)) if pred[i] == y[i]]
    miss  = [ids[i] for i in range(len(ids)) if pred[i] != y[i]]

    # which two choices moved the weights most: refit without each, measure the L1 shift
    infl = []
    for i in range(len(ids)):
        keep = [j for j in range(len(ids)) if j != i]
        wi, _b, _s = fit_once(D[keep], y[keep], prior, lam)
        infl.append((float(np.abs(wi - w).sum()), ids[i]))
    infl.sort(reverse=True)

    return {"person": person, "weights": {K[i]: round(float(w[i]), 2) for i in range(len(K))},
            "prior": {K[i]: round(float(prior[i]), 2) for i in range(len(K))},
            "moved": {K[i]: round(float(w[i] - prior[i]), 2) for i in range(len(K))},
            "ridge_lambda": lam, "consistency_beta": round(beta, 3),
            "supported_components": [K[i] for i in sup],
            "probe_move_at_lambda": {K[i]: round(v, 2) for i, v in probe.items()},
            "immovable_components": [K[i] for i, v in probe.items() if v < mm],
            "unsupported_components": [K[i] for i in range(len(K)) if i not in sup],
            "reproduced": len(agree), "of": len(ids), "not_reproduced": miss,
            "most_influential": [t[1] for t in infl[:2]],
            "influence": {t[1]: round(t[0], 2) for t in infl},
            "converged": ok, "method": "pairwise_choice"}

if __name__ == "__main__":
    cfg = _cfg(); pairs = load_pairs()
    if not pairs:
        print("no out/pairs.json; run build_pairs.py first"); sys.exit(0)
    any_fit = False
    for who in ("alex", "partner"):
        f = fit(who, cfg, pairs)
        n = len(((cfg.get("choices") or {}).get(who)) or [])
        if not f:
            print(f'{who}: {n} of {pairs["n"]} choices on file. Not fitted; weights stay provisional.')
            continue
        any_fit = True
        print(f'{who}: fitted from {f["of"]} choices, ridge lambda {f["ridge_lambda"]}, '
              f'consistency beta {f["consistency_beta"]}')
        print("   " + "  ".join(f'{k} {v:.1f}' for k, v in f["weights"].items()))
        print(f'   reproduces {f["reproduced"]} of {f["of"]} choices'
              + (f'; misses {", ".join(f["not_reproduced"])}' if f["not_reproduced"] else ""))
        print(f'   most influential choices: {", ".join(f["most_influential"])}')
        if f["unsupported_components"]:
            print(f'   the design cannot speak to: {", ".join(f["unsupported_components"])} (left near the prior)')
        if f["immovable_components"]:
            print(f'   these fifteen pairs cannot move by the required margin: {", ".join(f["immovable_components"])}')
    if any_fit:
        json.dump({w: fit(w, cfg, pairs) for w in ("alex", "partner")},
                  open(os.path.join(R, "out", "weights_fitted.json"), "w"), indent=1, default=str)
