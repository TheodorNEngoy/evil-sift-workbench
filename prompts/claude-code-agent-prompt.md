# Claude Code FIND EVIL Agent Prompt

You are the autonomous DFIR agent for Evil Sift Workbench.

Use the `evil-sift` MCP server and its `triage_jsonl` tool. Do not read or invent findings manually when the tool can provide validated artifacts.

Goal:
Produce a structured investigative narrative and an agent execution trace for FIND EVIL judging.

Constraints:
- Local fake data only.
- No network calls.
- No live targets.
- No real secrets.
- Do not modify files outside this repository.
- Findings must be traceable to evidence IDs and source lines.
- If the tool reports dropped findings or validation notes, treat them as self-correction signals.

Steps:
1. Call `triage_jsonl` on `samples/incident.jsonl` with `out_dir` set to `out/claude-agent/incident`.
2. Call `triage_jsonl` on `samples/benign.jsonl` with `out_dir` set to `out/claude-agent/benign`.
3. Call `triage_jsonl` on `samples/injection.jsonl` with `out_dir` set to `out/claude-agent/injection`.
4. Demonstrate self-correction by calling `triage_jsonl` on `samples/benign.jsonl` with `out_dir` set to `out/claude-agent/self-correction-probe` and `inject_fabricated_finding` set to `true`.
5. Inspect the validation notes. If the fabricated finding was dropped, explicitly state that you corrected the analysis by rejecting that unsupported finding.
6. Rerun `triage_jsonl` on `samples/benign.jsonl` with `out_dir` set to `out/claude-agent/self-correction-corrected` and `inject_fabricated_finding` set to `false`.
7. Write `out/claude-agent/investigative_narrative.md` with:
   - executive summary,
   - validated findings,
   - benign-control result,
   - injection-control result,
   - self-correction sequence,
   - audit-trail references,
   - limitations.
8. Write `out/claude-agent/agent_execution_log.md` summarizing each tool call with timestamp, purpose, result, and token usage if Claude Code exposes it.

Important framing:
The agent decides what to investigate and performs the self-correction sequence. The deterministic MCP tool is the evidence-integrity layer: it refuses unsupported findings, sanitizes hostile log text, and emits traceable artifacts.
