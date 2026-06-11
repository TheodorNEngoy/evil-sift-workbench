# Evil Sift Workbench Report

## Executive Summary

- Top finding: **Suspicious command execution with lateral-movement traffic on srv01** (Critical, Medium confidence).
- Findings: 4.
- Events reviewed: 14.
- Hosts reviewed: dc01, srv01

## Event Mix

- auth_failure: 9
- auth_success: 1
- network: 2
- process: 1
- zeek_conn: 1

## Findings

### 1. Suspicious command execution with lateral-movement traffic on srv01

- Severity: Critical
- Confidence: Medium
- Risk score: 90/100 (base 75 suspicious execution +15 lateral-movement traffic on admin ports, same host)
- Tactic: Execution / Lateral Movement
- Rationale: A suspicious shell command appears near administrative network traffic. The tool marks this as medium confidence until process parentage or timeline context confirms it.
- Evidence IDs: spl-00004, spl-00002, spl-00003
- Detection hint: `suspicious_process AND admin_port_network_activity on same host`
- Evidence snippets:
  - `spl-00004` line 4: `{"_source_line": 4, "command": "powershell.exe -enc SQBFAFgA", "decoded_command_preview": "IEX", "detail": "Process Create", "event_type": "process", "host": "srv01", "id": "spl-00004", "parent": "wsmprovhost.exe", "ts": "2026-06-10T08:03:20Z", "user": "svc-backup"}`
  - `spl-00002` line 2: `{"_source_line": 2, "detail": "Network connection detected", "dst_ip": "10.0.0.22", "dst_port": 5985, "event_type": "network", "host": "srv01", "id": "spl-00002", "proto": "tcp", "src_ip": "10.0.0.11", "ts": "2026-06-10T08:04:10Z", "user": "svc-backup"}`
  - `spl-00003` line 3: `{"_source_line": 3, "detail": "Network connection detected", "dst_ip": "10.0.0.21", "dst_port": 445, "event_type": "network", "host": "srv01", "id": "spl-00003", "proto": "tcp", "src_ip": "10.0.0.11", "ts": "2026-06-10T08:03:50Z", "user": "svc-backup"}`

### 2. Password-spray followed by successful login for svc-backup

- Severity: High
- Confidence: High
- Risk score: 85/100 (base 60 credential-access pattern +25 confirmed success after repeated failures)
- Tactic: Credential Access / Initial Access
- Rationale: 5 authentication failures for the same user were followed by a successful login. This is a compact attack chain, not a single noisy event.
- Evidence IDs: spl-00010, spl-00011, spl-00012, spl-00013, spl-00014, spl-00009
- Detection hint: `auth_failure_count_by_user >= 5 followed by auth_success within window`
- Evidence snippets:
  - `spl-00010` line 10: `{"_source_line": 10, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00010", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:45Z", "user": "svc-backup"}`
  - `spl-00011` line 11: `{"_source_line": 11, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00011", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:34Z", "user": "svc-backup"}`
  - `spl-00012` line 12: `{"_source_line": 12, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00012", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:23Z", "user": "svc-backup"}`
  - `spl-00013` line 13: `{"_source_line": 13, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00013", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:12Z", "user": "svc-backup"}`
  - `spl-00014` line 14: `{"_source_line": 14, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00014", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:01Z", "user": "svc-backup"}`
  - `spl-00009` line 9: `{"_source_line": 9, "detail": "An account was successfully logged on", "event_type": "auth_success", "host": "dc01", "id": "spl-00009", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:01:01Z", "user": "svc-backup"}`

### 3. Suspicious command followed by external callback on srv01

- Severity: High
- Confidence: Medium
- Risk score: 80/100 (base 65 suspicious execution +15 external egress in same host timeline)
- Tactic: Command and Control
- Rationale: A suspicious shell command was followed by outbound web traffic to a non-internal test-network address in the same host timeline. This is useful as a triage pivot, but still needs endpoint/network enrichment before containment.
- Evidence IDs: spl-00004, spl-00001
- Detection hint: `suspicious_process followed by external zeek_conn/web egress on same host`
- Evidence snippets:
  - `spl-00004` line 4: `{"_source_line": 4, "command": "powershell.exe -enc SQBFAFgA", "decoded_command_preview": "IEX", "detail": "Process Create", "event_type": "process", "host": "srv01", "id": "spl-00004", "parent": "wsmprovhost.exe", "ts": "2026-06-10T08:03:20Z", "user": "svc-backup"}`
  - `spl-00001` line 1: `{"_source_line": 1, "artifact_type": "zeek_conn", "dst_ip": "203.0.113.77", "dst_port": 443, "event_type": "zeek_conn", "host": "srv01", "id": "spl-00001", "proto": "tcp", "src_ip": "10.0.0.11", "ts": "2026-06-10T08:04:50Z"}`

### 4. Single source attempted multiple accounts (198.51.100.44)

- Severity: Medium
- Confidence: High
- Risk score: 65/100 (base 65 single-stage credential-access pattern; no confirmed-success bonus)
- Tactic: Credential Access
- Rationale: Source 198.51.100.44 attempted authentication against 5 distinct accounts.
- Evidence IDs: spl-00005, spl-00006, spl-00007, spl-00008, spl-00010, spl-00011, spl-00012, spl-00013
- Detection hint: `distinct_failed_users_by_src_ip >= 4`
- Evidence snippets:
  - `spl-00005` line 5: `{"_source_line": 5, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00005", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:13Z", "user": "dave"}`
  - `spl-00006` line 6: `{"_source_line": 6, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00006", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:12Z", "user": "carol"}`
  - `spl-00007` line 7: `{"_source_line": 7, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00007", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:11Z", "user": "bob"}`
  - `spl-00008` line 8: `{"_source_line": 8, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00008", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:10Z", "user": "alice"}`
  - `spl-00010` line 10: `{"_source_line": 10, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00010", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:45Z", "user": "svc-backup"}`
  - `spl-00011` line 11: `{"_source_line": 11, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00011", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:34Z", "user": "svc-backup"}`
  - `spl-00012` line 12: `{"_source_line": 12, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00012", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:23Z", "user": "svc-backup"}`
  - `spl-00013` line 13: `{"_source_line": 13, "detail": "An account failed to log on", "event_type": "auth_failure", "host": "dc01", "id": "spl-00013", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:12Z", "user": "svc-backup"}`

## Self-Correction / Validation

Every finding was dropped unless each cited evidence ID existed in the input dataset. Medium-confidence findings explicitly say what additional evidence would be needed. Log content is rendered through a sanitizer so embedded text cannot alter this report's structure.
- No findings were dropped during evidence validation.

## Analyst Next Steps

- Confirm the time window and source host ownership.
- Pull surrounding authentication and endpoint telemetry for the cited evidence IDs.
- Convert validated detection hints into environment-specific SIEM rules.
