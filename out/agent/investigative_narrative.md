# Evil Sift Agent Workflow Narrative

This local smoke test exercises the Custom MCP Server pattern without paid API usage.
For the final FIND EVIL submission, run the same MCP server from Claude Code or OpenClaw so the agent trace contains real model token usage.

## Findings

- Incident control: 4 validated findings. Top finding: Suspicious command execution with lateral-movement traffic on srv01.
- Benign control: 0 findings.
- Injection control: 3 findings, including manipulation content flagged as Defense Evasion.
- Self-correction: a fabricated finding was rejected because its evidence ID was missing; the workflow reran cleanly.

## Artifacts

- Incident report: `out/agent/incident/report.md`
- Injection report: `out/agent/injection/report.md`
- Self-correction probe log: `out/agent/self_correction_probe/execution_log.json`
