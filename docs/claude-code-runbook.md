# Claude Code Agent Runbook

Evil Sift uses the **Custom MCP Server** pattern:

- Claude Code or OpenClaw is the agentic execution layer.
- `mcp/evil_sift_mcp_server.py` exposes the deterministic evidence-integrity tool `triage_jsonl`.
- The agent decides what to investigate, calls the MCP tool, inspects validation notes, performs self-correction, and writes the final narrative.
- The MCP tool remains the verdict authority: unsupported findings are dropped, hostile log text is sanitized, and every finding links to evidence IDs.

## No-API Smoke Test

Run this any time:

```bash
./demo.sh
```

Or just the agent workflow smoke test:

```bash
python3 scripts/local_agent_demo.py
```

This writes:

```text
out/agent/investigative_narrative.md
out/agent/agent_execution_log.json
```

The smoke test does not call Claude and records zero token usage. It proves the MCP tool contract and self-correction sequence without spending money.

## Claude Code Run

Only run this when token usage is approved. Use a small hard cap:

```bash
claude \
  --mcp-config .mcp.json \
  --max-budget-usd 0.50 \
  --permission-mode acceptEdits \
  --print "$(cat prompts/claude-code-agent-prompt.md)"
```

Expected result:

```text
out/claude-agent/incident/
out/claude-agent/benign/
out/claude-agent/injection/
out/claude-agent/self-correction-probe/
out/claude-agent/self-correction-corrected/
out/claude-agent/investigative_narrative.md
out/claude-agent/agent_execution_log.md
```

For the final Devpost submission, include the Claude Code output as the agent execution log with real token usage. Keep the local smoke-test log as a no-spend reproducibility artifact.

## Manual Interactive Alternative

If the non-interactive command has trouble with MCP permissions, run:

```bash
claude --mcp-config .mcp.json
```

Then paste the contents of:

```text
prompts/claude-code-agent-prompt.md
```

Accept only local file reads/writes inside this repository and MCP calls to `evil-sift`.
