#!/usr/bin/env python3
"""Eval harness: runs the triage agent over a labeled synthetic ticket set,
reports category accuracy, action accuracy, and high-risk false auto-fix rate."""
import json, os, sys
from agent import triage, KBIndex

HERE = os.path.dirname(__file__)
EVAL = json.load(open(os.path.join(HERE, "data", "tickets_eval.json")))

def norm(s):
    return (s or "").lower().strip()

def main():
    kb = KBIndex()
    rows = []
    for t in EVAL:
        got = triage(t["text"], kb)
        rows.append({"id": t["id"], "expected_cat": t["category"], "expected_action": t["expected_action"],
                     "risk": t.get("risk", "low"), "got": got})
        print(f"{t['id']}: exp={t['category']}/{t['expected_action']} got={got['category']}/{got['action']}", flush=True)
    cat_ok = sum(1 for r in rows if norm(r["got"]["category"]) == norm(r["expected_cat"]))
    act_ok = sum(1 for r in rows if norm(r["got"]["action"]) == norm(r["expected_action"]))
    danger = [r for r in rows if r["risk"] in ("high", "critical") and norm(r["got"]["action"]) == "auto_fix"]
    n = len(rows)
    report = {
        "n_tickets": n,
        "category_accuracy": round(cat_ok / n, 3),
        "action_accuracy": round(act_ok / n, 3),
        "high_risk_false_autofix": len(danger),   # target: 0
        "details": rows,
    }
    out = os.path.join(HERE, "eval_report.json")
    json.dump(report, open(out, "w"), indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, indent=2))

if __name__ == "__main__":
    main()
