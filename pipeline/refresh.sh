#!/bin/sh
# One command after any edit to observations.json or costs.yaml.
set -e; cd "$(dirname "$0")"
mkdir -p out ../deliverables
python3 score.py observations.json out/ > out/score_report.txt
python3 export_detail.py > /dev/null
python3 build_agent_questions.py
python3 test_model.py
python3 build_walkthrough.py
python3 build_cost_detail.py
echo "done: out/decision.csv, out/detail.json, out/agent_questions.md, ../deliverables/*.html, ../deliverables/renovation-cost-detail.md"
