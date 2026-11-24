#!/usr/bin/env python3
"""Fake `claude -p`: logs one line per call and answers from FAKE_CLAUDE_REPLIES or in smart mode.

Env: FAKE_CLAUDE_LOG (file, one line appended per call), FAKE_CLAUDE_REPLIES (JSON file: list of
{"result": str, "cost"?: any, "usage"?: any} | {"exit": int} | {"sleep": seconds}, one per call, the last repeats),
FAKE_CLAUDE_MARKER (smart mode: a skill line containing it gets an `outdated` finding),
FAKE_CLAUDE_COST / FAKE_CLAUDE_TOKENS (total_cost_usd / input_tokens reported per call).
"""
import json
import os
import re
import sys
import time

prompt = sys.stdin.read()
with open(os.environ["FAKE_CLAUDE_LOG"], "a") as log:
    log.write("call\n")
    calls = log.tell() // len("call\n")

reply_file = os.environ.get("FAKE_CLAUDE_REPLIES")
if reply_file:
    replies = json.load(open(reply_file))
    scripted = replies[min(calls, len(replies)) - 1]
else:
    ids = re.findall(r"^### (\S+) \[", prompt, re.M)
    findings = []
    marker = os.environ.get("FAKE_CLAUDE_MARKER")
    path = None
    for line in prompt.splitlines():
        header = re.match(r"^=== (.+) ===$", line)
        if header:
            path = header.group(1)
        numbered = re.match(r"^(\d+): (.*)$", line)
        if marker and path and numbered and marker in numbered.group(2):
            findings.append({"kind": "outdated", "path": path, "line": int(numbered.group(1)),
                             "quote": marker, "why": "deprecated in this release", "confidence": "high"})
    reply = {"items": [{"id": i, "findings": findings if n == 0 else []} for n, i in enumerate(ids)]}
    scripted = {"result": json.dumps(reply)}

if "sleep" in scripted:
    time.sleep(float(scripted["sleep"]))
if "exit" in scripted:
    sys.exit(scripted["exit"])
out = {"result": scripted["result"], "is_error": False,
       "total_cost_usd": scripted.get("cost", float(os.environ.get("FAKE_CLAUDE_COST", "0"))),
       "usage": scripted.get("usage", {"input_tokens": int(os.environ.get("FAKE_CLAUDE_TOKENS", "100"))})}
if out["total_cost_usd"] == "__absent__":
    del out["total_cost_usd"]
print(json.dumps(out))
