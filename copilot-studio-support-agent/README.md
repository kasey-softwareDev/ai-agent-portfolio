# Project 2 — Declarative support agent for Microsoft 365 Copilot (Copilot Studio)

A declarative agent that triages internal IT tickets inside Teams / M365 Copilot Chat:
grounds answers in the IT runbook (SharePoint knowledge source), can call a custom
action (HTTP connector to the ITSM API) for password resets, and always escalates
high/critical-risk requests to a human.

## Files
- `agent/manifest.yaml` — declarative agent definition (name, instructions, knowledge sources, actions, topics, guardrails)
- `agent/actions/itsm-reset-password.json` — custom action (connector) schema: POST /api/password-reset with employee-ID verification
- `docs/deployment.md` — step-by-step: Copilot Studio > Create agent > upload manifest > add SharePoint KB > publish to Teams
- `docs/eval-notes.md` — how the same 30-ticket eval set from project 1 maps to Copilot Studio test cases

> Honest note: building/publishing a live Copilot Studio agent requires an M365 tenant
> with Copilot Studio licensing, so this repo ships the full agent package + docs +
> test plan rather than a live URL. The runtime agent with real measured eval numbers
> is project 1 (ticket-triage-agent).
