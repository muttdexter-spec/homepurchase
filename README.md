# homepurchase

First-house search for Burlington / Oakville: listing harvest, photo-based condition grading, renovation costing, scoring, and the printable walkthrough report used at showings.

**Live site:** https://muttdexter-spec.github.io/homepurchase/

Ranked since 14 September 2026 on **one score out of 100 per house**: eight components, each on an absolute scale, weighted by the two buyers. `docs/ranking-system-v6.md` is the specification, `docs/RANK-V6-DECISION.md` is the argument for it, and `CHANGELOG.md` has the short version.

The weights are **provisional** until both buyers have answered the fifteen pairwise choices on the page. Every card says so.

## What is here

| Path | What it holds |
| --- | --- |
| `index.html` | Entry point. Routes phones to the mobile build, everything else to the full build. `?v=full` or `?v=mobile` forces a version. |
| `full.html` | Walking the Shortlist, desktop build |
| `mobile.html` | Walking the Shortlist, phone build |
| `pipeline/` | Crawlers, scoring model (`score.py`), cost assumptions (`costs.yaml`), report builders, and the input data they read (`observations.json`, `rooms_legacy.json`, `live_*.json`) |
| `pipeline/out/` | Generated outputs: decision CSV, detail JSON, score report, agent questions |
| `deliverables/` | Where `build_cost_detail.py` writes `renovation-cost-detail.md`. Only this README is kept in the repo. |
| `docs/` | Start here: `HANDOFF-START-HERE.md`. Then `ranking-system-v6.md` (how the order is computed), `RANK-V6-DECISION.md` (why v5 was replaced), `USABILITY-SPEC.md` (what each number on the page is and where it sits), `ELICITATION.md` (how the weights are obtained, and what happened on 13 and 14 September), `QA-PASS-2026-09-14.md` (what changed), `BACKLOG-optimizations.md` (what is next). Plus the operating manual, the grading and photo methodology, the search harvest notes and the per-line renovation costs. `superseded/` holds v4 and v5. |
| `CHANGELOG.md` | One entry per model or page version |

## Pipeline

Edit `pipeline/observations.json` (what you saw at a showing) or `pipeline/costs.yaml` (renovation cost assumptions), then:

```bash
cd pipeline
sh refresh.sh
```

That runs `build_pairs.py`, `fit_choices.py`, `score.py`, `export_detail.py`, `build_agent_questions.py`, `test_model.py`, `build_walkthrough.py` and `build_cost_detail.py` in order. It needs Python 3 with `pyyaml`, `numpy` and `scipy`.

`build_walkthrough.py` writes `full.html` and `mobile.html` **straight to the repo root**, so after `refresh.sh` you commit and push and the site is current. Nothing has to be copied. The site is those two files plus `index.html`.

`score.py` holds the cost model (v3.4) and rank v6: the gate ladder, eight components on absolute scales, and one weighted score. Every tunable is in `costs.yaml`, under `catalog`, `recovery`, `p_not_done` and `contingency` for the cost model and under `hold`, `gates`, `weights`, `choices` and `pairs` for the ranking.

The weights are the one thing in here that must not come from the model. They are fitted from fifteen forced choices between real houses, one set per buyer: `build_pairs.py` designs the pairs, the page collects the answers, `fit_choices.py` fits them. Until a person has answered all fifteen, their weights are whatever is in `costs.yaml: weights` and the page stamps every card **Weights provisional**.

The page chrome is not in the builder. It lives in `pipeline/page_full.tpl.html` and `pipeline/page_mobile.tpl.html`, which are the previously built pages with every model-produced region replaced by a `{{PLACEHOLDER}}`. `build_walkthrough.py` fills them, so a regenerated page differs from the last one only where the model changed. After a deliberate change to the chrome, run `pipeline/make_page_templates.py` by hand to re-freeze the templates and read the diff. It is not part of `refresh.sh`.

Both builds carry a hold toggle at 3, 5 and 10 years alongside down payment, rate and amortization. Changing any of them rewrites every monthly payment on the page from one `monthlyPayment()`; the rank itself is computed offline and does not move, and the control bar says so.

`manifest.json` and `sw.js` at the root make the page open with the network off after one visit, which is what a basement at a showing needs.

## Deploying

**Settings → Pages → Build and deployment → Source: Deploy from a branch → `main` / `/ (root)`.**

Nothing else is needed. Pages rebuilds within a minute of every commit to `main`. No file or folder here starts with an underscore, so Jekyll passes the site through untouched and no `.nojekyll` file is required.

### Optional, if you later work from a clone

Two dotfiles are deliberately absent because Windows will not let a browser upload them:

- `.gitignore`, suggested contents: `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `.DS_Store`, `Thumbs.db`, `*old.html`
- `.github/workflows/pages.yml`, only if you would rather deploy through Actions than branch deploy

Both are easy to add later with **Add file → Create new file** on GitHub, which accepts dotted names that the upload dialog rejects.

## Note on visibility

This repository is public, so the shortlist, addresses, asking prices, condition grades, and the verdicts in `docs/` and `out/` are readable by anyone with the URL. `index.html` sends `noindex` so search engines skip it, but that is a courtesy, not access control. To pull the analysis out of public view while keeping the site up, delete `docs/`, `out/` and `data/` from the repo (the built HTML is self-contained), or make the repo private and open the HTML locally instead.
