# homepurchase

First-house search for Burlington / Oakville: listing harvest, photo-based condition grading, renovation costing, scoring, and the printable walkthrough report used at showings.

**Live site:** https://muttdexter-spec.github.io/homepurchase/

## What is here

| Path | What it holds |
| --- | --- |
| `index.html` | Entry point. Routes phones to the mobile build, everything else to the full build. `?v=full` or `?v=mobile` forces a version. |
| `full.html` | Walking the Shortlist, desktop build |
| `mobile.html` | Walking the Shortlist, phone build |
| `pipeline/` | Crawlers, scoring model (`score.py`), cost assumptions (`costs.yaml`), report builders, and the input data they read (`observations.json`, `rooms_legacy.json`, `live_*.json`) |
| `pipeline/out/` | Generated outputs: decision CSV, detail JSON, score report, agent questions |
| `deliverables/` | Where the builders write the regenerated report HTML. Only this README is kept in the repo. |
| `docs/` | Operating manual, grading and photo methodology, search harvest notes, QA pass, renovation cost detail |

## Pipeline

Edit `pipeline/observations.json` (what you saw at a showing) or `pipeline/costs.yaml` (renovation cost assumptions), then:

```bash
cd pipeline
sh refresh.sh
```

That runs `score.py`, `export_detail.py`, `build_agent_questions.py`, `test_model.py`, `build_walkthrough.py` and `build_cost_detail.py` in order. It needs Python 3 with `pyyaml`.

Regenerated report HTML lands in `deliverables/`. To publish it, copy the desktop build over `full.html` and the phone build over `mobile.html` at the repo root, then commit and push. The site is these two files plus `index.html`, so nothing else has to be rebuilt.

## Deploying

**Settings → Pages → Build and deployment → Source: Deploy from a branch → `main` / `/ (root)`.**

Nothing else is needed. Pages rebuilds within a minute of every commit to `main`. No file or folder here starts with an underscore, so Jekyll passes the site through untouched and no `.nojekyll` file is required.

### Optional, if you later work from a clone

Two dotfiles are deliberately absent because Windows will not let a browser upload them:

- `.gitignore` — suggested contents: `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `.DS_Store`, `Thumbs.db`, `*old.html`
- `.github/workflows/pages.yml` — only if you would rather deploy through Actions than branch deploy

Both are easy to add later with **Add file → Create new file** on GitHub, which accepts dotted names that the upload dialog rejects.

## Note on visibility

This repository is public, so the shortlist, addresses, asking prices, condition grades, and the verdicts in `docs/` and `out/` are readable by anyone with the URL. `index.html` sends `noindex` so search engines skip it, but that is a courtesy, not access control. To pull the analysis out of public view while keeping the site up, delete `docs/`, `out/` and `data/` from the repo (the built HTML is self-contained), or make the repo private and open the HTML locally instead.
