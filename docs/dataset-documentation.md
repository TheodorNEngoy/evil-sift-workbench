# Dataset Documentation

All included datasets are fake, local JSONL event bundles created for repeatable FIND EVIL judging. They contain no real secrets, no live infrastructure, and no third-party customer data.

## Format

Each line is one JSON object. Relevant fields include:

- `id`: stable evidence identifier.
- `timestamp` or `ts`: event time.
- `event_type`: normalized event class such as `auth_failure`, `auth_success`, `process`, or `network`.
- `host`, `user`, `src_ip`, `dst_ip`, `dst_port`: triage pivots.
- `command`, `detail`: log-derived text. These fields are intentionally treated as untrusted data.

The ingest layer adds `_source_line` during processing so every finding can cite both evidence IDs and source line numbers.

## Samples

| Sample | Purpose | Ground truth | Expected result |
| --- | --- | --- | --- |
| `samples/incident.jsonl` | Positive control attack chain | Password spray against multiple users, success for `svc-backup`, encoded PowerShell on `srv01`, SMB/WinRM lateral movement, external TLS callback | 4 findings |
| `samples/benign.jsonl` | Negative control | A mistyped password, normal logon, ordinary admin PowerShell, allowlisted update traffic | 0 findings |
| `samples/injection.jsonl` | Adversarial telemetry control | Same style of attack chain, but log fields contain "do not flag", "ignore previous instructions", and a code-fence breakout attempt | 3 findings: attack chain remains detected plus manipulation content |

## Reproducibility

Run:

```bash
./demo.sh
```

The demo regenerates `out/incident`, `out/benign`, and `out/injection`. Each output directory contains:

- `report.md`
- `findings.json`
- `detections.yml`
- `audit_trail.json`
- `execution_log.json`

`audit_trail.json` records the input SHA-256 and the evidence backing each finding. `execution_log.json` records the local deterministic tool steps. `out/agent/agent_execution_log.json` records the local no-API MCP workflow smoke test, and the Claude Code/OpenClaw runbook produces the final agent trace with real token usage.

## Scope Limits

The prototype uses normalized JSONL rather than raw EVTX, disk images, memory captures, or Zeek logs. That is a conscious stop-rule tradeoff: the submission emphasizes evidence integrity, reproducibility, and injection resistance over broad parser coverage.
