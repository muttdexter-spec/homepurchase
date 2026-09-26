#!/bin/sh
# One command after any edit to observations.json or costs.yaml.
set -e; cd "$(dirname "$0")"
mkdir -p out ../deliverables
# The fifteen-choice picker is off the page (23 Sep 2026). build_pairs.py would re-select the pairs
# and fit_choices.py has no choices to fit, so both stay out unless the elicitation is restarted.
# python3 build_pairs.py > out/pairs_report.txt
# python3 fit_choices.py > out/weights_report.txt
python3 score.py observations.json out/ > out/score_report.txt
python3 export_detail.py > /dev/null
python3 build_agent_questions.py
python3 test_model.py
python3 build_walkthrough.py
python3 build_cost_detail.py
echo "done: out/decision.csv, out/detail.json, out/agent_questions.md, ../full.html, ../mobile.html, ../deliverables/renovation-cost-detail.md"
