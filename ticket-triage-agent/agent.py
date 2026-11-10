#!/usr/bin/env python3
"""Ticket-triage agent: classify IT support ticket -> decide auto-fix/clarify/escalate
-> execute via (mock) ITSM tools, with KB retrieval (RAG) and full audit log.
Runs locally on Ollama (qwen2.5 + nomic-embed-text). No cloud keys needed."""
import json, sqlite3, time, math, os, re, urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
LLM_BASE = os.environ.get("LLM_BASE", "")   # OpenAI-compatible base, e.g. http://127.0.0.1:8091/v1
MODEL = os.environ.get("AGENT_MODEL", os.environ.get("LLM_MODEL", "qwen2.5:latest"))
EMBED = os.environ.get("EMBED_MODEL", "nomic-embed-text:latest")
DB = os.path.join(os.path.dirname(__file__), "audit.db")

def ollama(path, payload, tries=3):
    payload = dict(payload)
    payload["stream"] = False
    last = None
    for _ in range(tries):
        try:
            if LLM_BASE and path == "/api/chat":
                p = {"model": MODEL, "messages": payload["messages"], "stream": False}
                if payload.get("tools"): p["tools"] = payload["tools"]
                req = urllib.request.Request(f"{LLM_BASE}/chat/completions", data=json.dumps(p).encode(),
                                             headers={"Content-Type": "application/json"})
                r = json.loads(urllib.request.urlopen(req, timeout=120).read())
                return {"message": {"role": "assistant", "content": r["choices"][0]["message"].get("content"),
                                    "tool_calls": [{"function": {"name": c["function"]["name"],
                                                                "arguments": c["function"]["arguments"]}}
                                                   for c in (r["choices"][0]["message"].get("tool_calls") or [])]}}
            if LLM_BASE and path == "/api/embeddings":
                req = urllib.request.Request(f"{LLM_BASE}/embeddings", data=json.dumps({"model": EMBED, "input": payload["prompt"]}).encode(),
                                             headers={"Content-Type": "application/json"})
                return {"embedding": json.loads(urllib.request.urlopen(req, timeout=60).read())["data"][0]["embedding"]}
            req = urllib.request.Request(f"{OLLAMA}{path}", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=300).read())
        except Exception as e:
            last = e
    raise last

def embed(text):
    return ollama("/api/embeddings", {"model": EMBED, "prompt": text})["embedding"]

def cos(a, b):
    return sum(x*y for x, y in zip(a, b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) + 1e-9)

# ---------- KB (RAG over runbook snippets) ----------
KB = [
    ("password reset", "Reset via ITSM portal: Users > Reset Password. Never reset without verifying employee ID. Auto-fix allowed after ID check.", "low"),
    ("vpn not connecting", "Check MFA push, reinstall AnyConnect, check device time sync. Auto-fix: re-enroll MFA.", "low"),
    ("outlook not opening", "Repair Office profile, clear credentials manager, recreate profile.", "low"),
    ("intune device not compliant", "Force sync in Company Portal; check disk encryption; escalate if still non-compliant after sync.", "medium"),
    ("mailbox permission request", "Grant via Exchange admin; requires manager approval for external recipients. NEVER auto-grant to external domains.", "high"),
    ("shared drive access", "Add to SharePoint group after owner approval.", "medium"),
    ("printer not found", "Re-add via Printers > Add, check print server.", "low"),
    ("software install request", "Install from Company Portal if catalogued; else escalate to desktop team.", "medium"),
    ("account locked out", "Unlock in AD after verifying identity; check lockout source.", "low"),
    ("data deletion request", "NEVER auto-approve. Always escalate to security/DPO.", "critical"),
]

class KBIndex:
    def __init__(self):
        self.rows = [(t, embed(t + " " + d), d, r) for t, d, r in KB]
    def search(self, q, k=2):
        qe = embed(q)
        scored = sorted(self.rows, key=lambda r: cos(qe, r[1]), reverse=True)[:k]
        return [{"topic": r[0], "guidance": r[2], "risk": r[3], "score": round(cos(qe, r[1]), 3)} for r in scored]

# ---------- mock ITSM tools ----------
TOOLS = [
    {"type": "function", "function": {"name": "kb_search", "description": "Search IT runbook KB for guidance on the ticket topic.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "itsm_reset_password", "description": "Reset a user's password after identity verification.",
     "parameters": {"type": "object", "properties": {"user": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "itsm_unlock_account", "description": "Unlock a locked AD account after identity verification.",
     "parameters": {"type": "object", "properties": {"user": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "itsm_grant_mailbox_perm", "description": "Grant mailbox permission. REFUSES external domains.",
     "parameters": {"type": "object", "properties": {"user": {"type": "string"}, "target": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "itsm_intune_sync", "description": "Force Intune compliance sync on a device.",
     "parameters": {"type": "object", "properties": {"device": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "decide", "description": "Final decision for the ticket.",
     "parameters": {"type": "object", "properties": {
         "category": {"type": "string"}, "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
         "action": {"type": "string", "enum": ["auto_fix", "clarify", "escalate"]},
         "reason": {"type": "string"}}}}},
]

def audit(event):
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS audit(ts REAL, event TEXT)")
    con.execute("INSERT INTO audit VALUES (?, ?)", (time.time(), json.dumps(event)))
    con.commit(); con.close()

def run_tool(name, args, kb):
    if name == "kb_search":
        res = kb.search(args["query"])
    elif name == "itsm_reset_password":
        res = {"status": "ok", "note": f"password reset issued for {args['user']} (identity verified)"}
    elif name == "itsm_unlock_account":
        res = {"status": "ok", "note": f"account unlocked: {args['user']}"}
    elif name == "itsm_grant_mailbox_perm":
        if args["target"].split("@")[-1] not in ("corp.example.com",):
            res = {"status": "refused", "note": "external domain - policy requires human approval"}
        else:
            res = {"status": "ok", "note": f"granted {args['target']} access to {args['user']}'s mailbox"}
    elif name == "itsm_intune_sync":
        res = {"status": "ok", "note": f"sync forced on {args['device']}"}
    else:
        res = {"status": "unknown_tool"}
    audit({"tool": name, "args": args, "result": res})
    return res

def triage(ticket, kb):
    audit({"ticket": ticket})
    messages = [
        {"role": "system", "content": "You are an IT ticket-triage agent. Use kb_search first. Then call ITSM tools ONLY if the KB risk level is 'low' and identity is verified; 'medium' needs a clarify step; 'high'/'critical' must escalate. Always finish with the decide tool."},
        {"role": "user", "content": f"Ticket: {ticket}"} ]
    for _ in range(6):
        r = ollama("/api/chat", {"model": MODEL, "messages": messages, "tools": TOOLS})
        msg = r["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            break
        for c in calls:
            fn = c["function"]["name"]
            args = json.loads(c["function"]["arguments"]) if isinstance(c["function"]["arguments"], str) else c["function"]["arguments"]
            if fn == "decide":
                audit({"decision": args})
                return args
            res = run_tool(fn, args, kb)
            messages.append({"role": "tool", "name": fn, "content": json.dumps(res)})
    return {"category": "unknown", "priority": "P4", "action": "escalate", "reason": "no decision reached - escalated (safe default)"}

if __name__ == "__main__":
    import sys
    kb = KBIndex()
    t = sys.argv[1] if len(sys.argv) > 1 else "user john.doe cannot log in, password not working, verified employee ID 12345"
    print(json.dumps(triage(t, kb), indent=2))
