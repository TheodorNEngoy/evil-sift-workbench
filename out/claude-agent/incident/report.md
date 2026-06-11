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
- Evidence IDs: ev-011, ev-012, ev-013
- Detection hint: `suspicious_process AND admin_port_network_activity on same host`
- Evidence snippets:
  - `ev-011` line 11: `{"_source_line": 11, "command": "powershell.exe -enc SQBFAFgA", "decoded_command_preview": "IEX", "event_type": "process", "host": "srv01", "id": "ev-011", "parent": "wsmprovhost.exe", "ts": "2026-06-10T08:03:20Z", "user": "svc-backup"}`
  - `ev-012` line 12: `{"_source_line": 12, "detail": "SMB session", "dst_ip": "10.0.0.21", "dst_port": 445, "event_type": "network", "host": "srv01", "id": "ev-012", "ts": "2026-06-10T08:03:50Z", "user": "svc-backup"}`
  - `ev-013` line 13: `{"_source_line": 13, "detail": "WinRM session", "dst_ip": "10.0.0.22", "dst_port": 5985, "event_type": "network", "host": "srv01", "id": "ev-013", "ts": "2026-06-10T08:04:10Z", "user": "svc-backup"}`

### 2. Password-spray followed by successful login for svc-backup

- Severity: High
- Confidence: High
- Risk score: 85/100 (base 60 credential-access pattern +25 confirmed success after repeated failures)
- Tactic: Credential Access / Initial Access
- Rationale: 5 authentication failures for the same user were followed by a successful login. This is a compact attack chain, not a single noisy event.
- Evidence IDs: ev-001, ev-002, ev-003, ev-004, ev-005, ev-006
- Detection hint: `auth_failure_count_by_user >= 5 followed by auth_success within window`
- Evidence snippets:
  - `ev-001` line 1: `{"_source_line": 1, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-001", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:01Z", "user": "svc-backup"}`
  - `ev-002` line 2: `{"_source_line": 2, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-002", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:12Z", "user": "svc-backup"}`
  - `ev-003` line 3: `{"_source_line": 3, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-003", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:23Z", "user": "svc-backup"}`
  - `ev-004` line 4: `{"_source_line": 4, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-004", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:34Z", "user": "svc-backup"}`
  - `ev-005` line 5: `{"_source_line": 5, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-005", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:45Z", "user": "svc-backup"}`
  - `ev-006` line 6: `{"_source_line": 6, "detail": "interactive logon", "event_type": "auth_success", "host": "dc01", "id": "ev-006", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:01:01Z", "user": "svc-backup"}`

### 3. Suspicious command followed by external callback on srv01

- Severity: High
- Confidence: Medium
- Risk score: 80/100 (base 65 suspicious execution +15 external egress in same host timeline)
- Tactic: Command and Control
- Rationale: A suspicious shell command was followed by outbound web traffic to a non-internal test-network address in the same host timeline. This is useful as a triage pivot, but still needs endpoint/network enrichment before containment.
- Evidence IDs: ev-011, ev-014
- Detection hint: `suspicious_process followed by external zeek_conn/web egress on same host`
- Evidence snippets:
  - `ev-011` line 11: `{"_source_line": 11, "command": "powershell.exe -enc SQBFAFgA", "decoded_command_preview": "IEX", "event_type": "process", "host": "srv01", "id": "ev-011", "parent": "wsmprovhost.exe", "ts": "2026-06-10T08:03:20Z", "user": "svc-backup"}`
  - `ev-014` line 14: `{"_source_line": 14, "artifact_type": "zeek_conn", "detail": "short outbound TLS session after encoded shell", "dst_ip": "203.0.113.77", "dst_port": 443, "event_type": "zeek_conn", "host": "srv01", "id": "ev-014", "proto": "tcp", "src_ip": "10.0.0.11", "ts": "2026-06-10T08:04:50Z", "user": "svc-backup"}`

### 4. Single source attempted multiple accounts (198.51.100.44)

- Severity: Medium
- Confidence: High
- Risk score: 65/100 (base 65 single-stage credential-access pattern; no confirmed-success bonus)
- Tactic: Credential Access
- Rationale: Source 198.51.100.44 attempted authentication against 5 distinct accounts.
- Evidence IDs: ev-001, ev-002, ev-003, ev-004, ev-005, ev-007, ev-008, ev-009
- Detection hint: `distinct_failed_users_by_src_ip >= 4`
- Evidence snippets:
  - `ev-001` line 1: `{"_source_line": 1, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-001", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:01Z", "user": "svc-backup"}`
  - `ev-002` line 2: `{"_source_line": 2, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-002", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:12Z", "user": "svc-backup"}`
  - `ev-003` line 3: `{"_source_line": 3, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-003", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:23Z", "user": "svc-backup"}`
  - `ev-004` line 4: `{"_source_line": 4, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-004", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:34Z", "user": "svc-backup"}`
  - `ev-005` line 5: `{"_source_line": 5, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-005", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:00:45Z", "user": "svc-backup"}`
  - `ev-007` line 7: `{"_source_line": 7, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-007", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:10Z", "user": "alice"}`
  - `ev-008` line 8: `{"_source_line": 8, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-008", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:11Z", "user": "bob"}`
  - `ev-009` line 9: `{"_source_line": 9, "detail": "bad password", "event_type": "auth_failure", "host": "dc01", "id": "ev-009", "src_ip": "198.51.100.44", "ts": "2026-06-10T08:02:12Z", "user": "carol"}`

## Self-Correction / Validation

Every finding was dropped unless each cited evidence ID existed in the input dataset. Medium-confidence findings explicitly say what additional evidence would be needed. Log content is rendered through a sanitizer so embedded text cannot alter this report's structure.
- No findings were dropped during evidence validation.

## Analyst Next Steps

- Confirm the time window and source host ownership.
- Pull surrounding authentication and endpoint telemetry for the cited evidence IDs.
- Convert validated detection hints into environment-specific SIEM rules.
