# Devpost Submission Fields

## Project Name

Evil Sift Workbench

## Repository

https://github.com/TheodorNEngoy/evil-sift-workbench

## Demo Video

Paste this public YouTube URL into Devpost:

```text
https://www.youtube.com/watch?v=5z3JEZb1wKI
```

Source file:

```text
video/find-evil-demo-narrated.webm
```

## Architecture Diagram

Upload:

```text
docs/architecture.svg
```

## Story

Paste from:

```text
docs/devpost-story.md
```

## Supporting Evidence To Mention

- Dataset documentation: `docs/dataset-documentation.md`
- Accuracy report: `docs/accuracy-report.md`
- Claude Code agent narrative: `out/claude-agent/investigative_narrative.md`
- Claude Code agent execution log: `out/claude-agent/agent_execution_log.md`
- Raw MCP JSON-RPC transcript: `out/claude-agent/mcp_jsonrpc_transcript.jsonl`
- Local smoke-test agent log: `out/agent/agent_execution_log.json`

## One-Line Summary

Claude Code/OpenClaw-ready DFIR triage with a Custom MCP Server evidence layer that refuses hallucinated findings and treats hostile log text as data, not instructions.

## Final Pre-Submit Command

```bash
./demo.sh
```

Expected:

```text
PASS incident: 4 validated findings, each citing concrete evidence IDs
PASS benign control: zero findings (no false positives)
PASS injection control: verdicts unchanged, manipulation attempt flagged, report sanitized
PASS MCP agent smoke test: tool workflow produced narrative and self-correction log
PASS audit trails + execution logs: input SHA-256 and deterministic traces recorded
```
