# Kasey Louw — AI Agent Portfolio

AI apps & agents portfolio — built 2026-11. Kasey Louw (South Africa) ·
Microsoft Certified: Azure AI Apps and Agents Developer Associate (**AI-103**), MS-102, MD-102, MS-900 ·
HyperionDev AI Engineering bootcamp · IT technician (MSP L2/L3 background) · GitHub: @kasey-softwareDev

## Projects

### 1. ticket-triage-agent (Python, local LLM, tool-calling, RAG, eval harness)
An agent that ingests an IT support ticket, retrieves runbook guidance (RAG over embeddings),
decides auto-fix / clarify / escalate, and executes low-risk fixes through ITSM tool calls —
with a policy guardrail layer (external domains refused, deletions always escalated) and a
full SQLite audit log of every tool call.

- Stack: Python 3, Ollama (qwen2.5 + nomic-embed-text), tool-calling loop, cosine-sim KB retrieval, SQLite audit log
- Eval: 30 labeled synthetic tickets — see `ticket-triage-agent/eval_report.json` for measured numbers
  (category accuracy, action accuracy, high-risk false auto-fix count; target 0 on the last one)
- Run: `pip install -r requirements.txt` · `python eval.py` (needs local Ollama) · `python agent.py "ticket text"`

### 2. copilot-studio-support-agent (Microsoft Copilot Studio declarative agent package)
Same triage agent as a declarative agent for M365 Copilot Chat/Teams: manifest, knowledge source
config, HTTP-connector action for password reset, topics, and guardrails (no external grants,
no deletions, human approval for medium risk). Ships as a package + deployment guide
(live publishing needs an M365 tenant with Copilot Studio licensing).

## Why these projects
Hiring-manager signal for 2026 AI-agent roles: a runnable artifact, an eval set with real numbers,
a guardrail story, and an audit trail — plus domain edge from real MSP ticket work.

## Contact
kasey.cat08@gmail.com · LinkedIn: linkedin.com/in/kasey-louw · South Africa (SAST, UTC+2), remote-first
