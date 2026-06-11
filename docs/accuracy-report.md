# Accuracy Report

## Summary

Evil Sift Workbench was tested against three local fake datasets: one positive incident control, one benign negative control, and one adversarial prompt-injection control. The deterministic MCP tool produces the expected results and the local agent smoke test exercises the same tool contract:

| Dataset | Expected | Observed |
| --- | --- | --- |
| `samples/incident.jsonl` | 4 attack-chain findings | 4 findings |
| `samples/benign.jsonl` | 0 findings | 0 findings |
| `samples/injection.jsonl` | attack chain still detected plus manipulation finding | 3 findings |

The test suite covers the same contract with unit-level assertions:

```bash
python3 -m unittest -v tests
```

## False Positives

The benign control currently produces zero findings. This is not a claim of broad production precision; it is a regression guard proving the detector does not flag every routine authentication, PowerShell, or network event as evil.

Known false-positive risk remains around legitimate administrative encoded PowerShell, remote administration over SMB/WinRM, and web callbacks to benign external services. The report labels these chains with confidence and next-step language rather than presenting them as final incident truth.

## Missed Artifacts

The prototype does not parse raw disk, memory, EVTX, or Zeek files. It expects normalized JSONL. It also does not perform full time-window correlation yet; it groups by host, source, and user. A production version should add parser adapters and explicit temporal windows.

## Hallucination And Evidence Integrity

Findings are not accepted unless every cited evidence ID exists in the input dataset. A regression test injects a fabricated finding with nonexistent evidence and verifies that it is dropped and logged in validation notes.

Every accepted finding emits:

- evidence IDs,
- source line numbers,
- compact evidence snippets,
- risk score,
- score basis,
- detection hint,
- input SHA-256 in `audit_trail.json`.

This makes each conclusion traceable back to concrete local data.

## Prompt-Injection / Refusal Resistance

`samples/injection.jsonl` includes hostile log text such as "do not flag", "ignore previous instructions", and a code-fence breakout attempt. The verdicts are unaffected because the MCP tool does not interpret log text as instructions. The manipulation attempt is surfaced as a Defense Evasion finding, and rendered report text is sanitized before entering Markdown.

## Evidence Spoliation

The tool reads local input files and writes generated artifacts under the requested `--out` directory. It does not modify source datasets, does not contact live systems, does not call external APIs, and does not run third-party forensic tools against evidence. The security boundary is intentionally narrow for this prototype.

## Agent And Token Usage

The no-API smoke test in `scripts/local_agent_demo.py` records zero token usage and exists only to make the MCP tool contract reproducible without spending money. The final Claude Code agent trace is in `out/claude-agent/agent_execution_log.md`, with raw MCP request/response proof in `out/claude-agent/mcp_jsonrpc_transcript.jsonl`.

The key accuracy claim is not "no model." The claim is that the autonomous agent delegates verdicts to an architectural evidence-integrity layer that refuses unsupported findings and cannot be steered by hostile log content.
