# Devpost Story Draft

## Project name

Evil Sift Workbench

## Tagline

Claude Code/OpenClaw-ready DFIR triage with a deterministic evidence-integrity MCP tool that refuses hallucinated findings and treats hostile log text as data, not instructions.

## What it does

Evil Sift Workbench is an autonomous triage workflow built around the **Custom MCP Server** pattern. Claude Code or OpenClaw can call the `triage_jsonl` MCP tool to investigate local evidence bundles, inspect validation notes, perform a self-correction sequence, and write a structured investigative narrative.

The key design choice is separation of duties: the agent decides what to investigate, but a deterministic evidence-integrity core makes the final evidence-backed calls. It detects compact attack chains, validates every finding against concrete evidence IDs, safely previews encoded PowerShell, ranks findings by risk, and emits a human report, structured findings, detection hints, a hashed audit trail, and structured execution logs.

The differentiator is adversarial robustness. The demo includes telemetry that literally tells the tool "do not flag" and "ignore previous instructions." The attack chain is still detected, the manipulation attempt becomes its own Defense Evasion finding, and the rendered report stays well-formed because log-derived text is sanitized.

The final agent trace is preserved in `out/claude-agent/`: `agent_execution_log.md` summarizes each MCP call, `mcp_jsonrpc_transcript.jsonl` preserves the raw 14-message JSON-RPC transcript, and `investigative_narrative.md` contains the agent-authored report using only tool-validated packets.

## How we built it

The prototype is a Python stdlib MCP server plus deterministic analysis core. It intentionally avoids live systems, real secrets, and network calls during analysis.

Pipeline:

1. Claude Code/OpenClaw calls `triage_jsonl` through the local MCP server.
2. Strict JSONL ingest fails fast on malformed lines or duplicate evidence IDs.
3. Deterministic chain detectors look for password spray, success-after-failures, suspicious execution, lateral movement, external callback, and analyst/AI-directed manipulation content.
4. Evidence validation drops any finding whose cited evidence IDs are missing and returns validation notes to the agent as self-correction signals.
5. The renderer sorts findings by risk score and sanitizes log-derived text before writing Markdown.
6. Audit and execution logs record input hashes, evidence, validation notes, tool steps, and agent/tool traceability.

## Challenges

The hard part was making the agent useful without letting it invent evidence. The design had to make hostile telemetry inert, prevent fabricated findings from surviving, and make every conclusion reproducible from local data.

Another challenge was scope discipline. The hackathon invites broad SIFT integrations, but the highest-quality path for this prototype was a small reliable MCP evidence layer rather than a wide unfinished parser suite.

## What we learned

For autonomous incident response, model capability is not enough. The surrounding harness needs evidence constraints, auditability, negative controls, and adversarial controls. Even a simple detector becomes more judgeable when it can prove what it saw, what it dropped, and why log content could not steer the verdict.

## What's next

- Broaden ingest beyond normalized JSONL with raw-artifact adapters for EVTX, Zeek, and selected SIFT outputs.
- Add time-window correlation.
- Contribute the `triage_jsonl` MCP tool and its guardrail tests upstream to Protocol SIFT-style workflows.
- Expand the accuracy benchmark with more benign administrative activity and known attack chains.

## Try it out

```bash
./demo.sh
```

Expected final assertions:

```text
PASS incident: 4 validated findings, each citing concrete evidence IDs
PASS benign control: zero findings (no false positives)
PASS injection control: verdicts unchanged, manipulation attempt flagged, report sanitized
PASS MCP agent smoke test: tool workflow produced narrative and self-correction log
PASS audit trails + execution logs: input SHA-256 and deterministic traces recorded
```
