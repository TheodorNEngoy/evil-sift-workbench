# FIND EVIL Submission Outline

## Project

Evil Sift Workbench is a Custom MCP Server workflow for autonomous DFIR triage. Claude Code or OpenClaw can call `triage_jsonl` to turn small security event bundles into an analyst-ready evidence packet. The deterministic tool traces suspicious authentication and endpoint/network chains, validates every finding against concrete log evidence, resists prompt-injection embedded in telemetry, and emits both a human report and machine-readable artifacts.

## Judging-criteria mapping

- **Autonomous execution**: Claude Code/OpenClaw orchestrates the `triage_jsonl` MCP tool. The local no-API smoke test (`./demo.sh`) proves the same MCP workflow, including a self-correction sequence, without token spend.
- **IR accuracy**: every finding cites concrete evidence IDs and source line numbers; a finding citing nonexistent evidence is dropped and the drop is logged (covered by a unit test that injects a fabricated finding).
- **Robustness / adversarial resistance**: a dedicated injection control proves log content saying "do not flag" or "ignore previous instructions" cannot suppress a verdict; the manipulation attempt itself becomes a Defense Evasion finding, and all rendered output is sanitized against code-fence breakout.
- **Depth over breadth**: five chain-oriented detectors (password spray → success, multi-account spray source, suspicious execution + lateral movement, execution → external callback, embedded manipulation content), each with an explainable risk-score basis.
- **Constraint compliance**: all data is local fake data; no network, no secrets, no third-party systems, stdlib only.
- **Audit trail**: `audit_trail.json` records the input file SHA-256, tool version, validation notes, and the exact evidence events behind each finding. Outputs are deterministic — same input hash, same packet.
- **Execution trace**: `execution_log.json` records the deterministic tool sequence; `out/agent/agent_execution_log.json` records the local MCP workflow; the final Claude Code/OpenClaw run should add real token/tool-call trace.
- **Usability**: a SOC analyst gets a ranked report, decoded `-enc` payload previews, starter detection hints, and explicit next steps.

## Demo commands and expected outputs

```bash
./demo.sh
```

Expected:

- `out/incident/` — 4 findings (Critical 90 lateral movement, High 85 password spray, High 80 external callback, Medium 65 multi-account source), each with evidence snippets.
- `out/benign/` — 0 findings: the negative control proving it is not a "everything is evil" toy.
- `out/injection/` — 3 findings: the attack chain still fires at full severity despite embedded "do not flag" instructions, plus an "Embedded analyst/AI manipulation content" finding; `report.md` contains no unsanitized code fences.
- Self-correction guard: `SELF-CORRECTION PASS: fabricated finding dropped before report rendering`.
- Local MCP agent smoke test: `LOCAL AGENT DEMO PASS: MCP-style workflow ran incident, benign, injection, and self-correction controls`.
- Unit tests: `Ran 12 tests ... OK`.
- Final lines: five `PASS ...` assertions printed by the demo's own end-to-end checks.

Claude Code command for final agent trace:

```bash
claude --mcp-config .mcp.json --max-budget-usd 0.50 --permission-mode acceptEdits --print "$(cat prompts/claude-code-agent-prompt.md)"
```

## Demo video plan (≈90 seconds)

1. (10s) State the pattern: Claude Code/OpenClaw agent plus Custom MCP Server evidence-integrity tool.
2. (20s) Run `./demo.sh`; pause on the MCP workflow and incident summary lines.
3. (15s) Pause on the self-correction guard: fabricated evidence is dropped before rendering.
4. (20s) Open `out/incident/report.md`: show one finding's evidence IDs, source lines, decoded `-enc` preview, and score basis.
5. (20s) The differentiators: benign control shows 0 findings; injection control shows the verdict survived "do not flag" and the manipulation got flagged.
6. (15s) Open `out/agent/agent_execution_log.json`, `out/incident/audit_trail.json`, and `out/incident/execution_log.json`: agent workflow + input SHA-256 + per-finding evidence = reproducible, defensible packet.

## Pre-submission checklist

1. Run the Claude Code/OpenClaw agent trace from `docs/claude-code-runbook.md` after token usage is approved.
2. Record/upload the demo video to YouTube/Vimeo/Youku; local `.webm` alone is not enough for Devpost.
3. Screenshot `out/incident/report.md` (finding with evidence snippets), `docs/architecture.svg`, and the demo's `PASS` block.
4. Paste the Devpost description from `docs/devpost-story.md`.
5. Link or mention `docs/dataset-documentation.md`, `docs/accuracy-report.md`, `out/agent/agent_execution_log.json`, and the Claude Code/OpenClaw agent trace.
6. Re-run `./demo.sh` from a clean checkout immediately before submitting.
