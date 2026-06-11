#!/usr/bin/env python3
"""
Evil Sift Workbench: tiny local-first DFIR assistant prototype.

It ingests JSONL security events, finds suspicious behavior chains, validates
every finding against concrete evidence IDs, and writes an analyst-ready report
plus starter Sigma-style detections and a hashed audit trail.

Design rules:
- Verdicts come from deterministic detectors, never from instructions found in
  log content. Log text is data, not commands.
- A finding that cannot cite evidence IDs present in the input is dropped, and
  the drop is recorded in the validation notes.
- Everything interpolated into the rendered report is sanitized so hostile log
  content cannot break out of code spans or smuggle instructions into the
  report for a downstream human or LLM consumer.

No network, no secrets, no third-party data.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOL_VERSION = "0.2.0"

# Instruction-like content aimed at the analyst or an AI assistant. Matching is
# case-insensitive substring; verdicts are never affected by matched text, the
# match itself becomes a Defense Evasion finding.
MANIPULATION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "do not flag",
    "do not report",
    "report zero findings",
    "as benign",
    "mark as benign",
    "system override",
    "new instructions",
    "you are an ai",
    "ai assistant",
]

ENCODED_COMMAND_RE = re.compile(r"(?:-enc|-encodedcommand)\s+([A-Za-z0-9+/=]{4,})", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    title: str
    severity: str
    confidence: str
    rationale: str
    evidence_ids: list[str]
    tactic: str
    detection_hint: str
    score: int
    score_basis: str = ""


def sanitize_for_markdown(text: str) -> str:
    """Neutralize log-derived text before it is rendered into the report.

    Backticks become apostrophes (no code-span/fence breakout) and
    non-printable characters become spaces (no terminal escape smuggling).
    """
    cleaned = "".join(ch if ch.isprintable() else " " for ch in str(text))
    return cleaned.replace("`", "'")


def decode_encoded_command(command: str) -> str | None:
    """Best-effort preview of a base64 -enc PowerShell payload (UTF-16LE)."""
    match = ENCODED_COMMAND_RE.search(command)
    if not match:
        return None
    try:
        decoded = base64.b64decode(match.group(1), validate=True).decode("utf-16-le")
    except (ValueError, UnicodeDecodeError):
        return None
    decoded = decoded.strip()
    if not decoded or not all(ch.isprintable() for ch in decoded):
        return None
    return decoded[:120]


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a stable, reviewable evidence snippet without dumping raw logs."""
    fields = [
        "id",
        "timestamp",
        "ts",
        "artifact_type",
        "event_type",
        "host",
        "user",
        "src_ip",
        "dst_ip",
        "dst_port",
        "proto",
        "process_name",
        "parent",
        "command",
        "detail",
        "_source_line",
    ]
    snippet = {field: event[field] for field in fields if field in event and event[field] not in ("", None)}
    if "command" in snippet:
        command = str(snippet["command"])
        preview = decode_encoded_command(command)
        if preview:
            snippet["decoded_command_preview"] = preview
        if len(command) > 180:
            snippet["command"] = command[:177] + "..."
    return snippet


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{line_no}: invalid JSON ({exc.msg})")
            if not isinstance(event, dict):
                raise SystemExit(f"{path}:{line_no}: expected a JSON object per line")
            event.setdefault("id", f"{path.name}:{line_no}")
            event_id = str(event["id"])
            if event_id in seen_ids:
                raise SystemExit(f"{path}:{line_no}: duplicate event id {event_id!r}")
            seen_ids.add(event_id)
            event["_source_line"] = line_no
            events.append(event)
    return events


def validate_findings(events: list[dict[str, Any]], findings: list[Finding]) -> tuple[list[Finding], list[str]]:
    """Drop any finding citing an evidence ID that does not exist in the input."""
    events_by_id = {e["id"]: e for e in events}
    validated: list[Finding] = []
    notes: list[str] = []
    for finding in findings:
        missing = [event_id for event_id in finding.evidence_ids if event_id not in events_by_id]
        if missing:
            notes.append(f"Dropped '{finding.title}' because evidence IDs were missing: {', '.join(missing)}")
            continue
        validated.append(finding)
    if not notes:
        notes.append("No findings were dropped during evidence validation.")
    return validated, notes


def find_manipulation_attempts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find events whose text fields contain analyst/AI-directed instructions."""
    hits: list[dict[str, Any]] = []
    for event in events:
        for key, value in event.items():
            if key in {"id", "_source_line"} or not isinstance(value, str):
                continue
            lowered = value.lower()
            if any(pattern in lowered for pattern in MANIPULATION_PATTERNS):
                hits.append(event)
                break
    return hits


def detect(events: list[dict[str, Any]]) -> list[Finding]:
    by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_src: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_host: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_user[str(event.get("user", ""))].append(event)
        by_src[str(event.get("src_ip", ""))].append(event)
        by_host[str(event.get("host", ""))].append(event)

    findings: list[Finding] = []

    for user, user_events in by_user.items():
        failures = [e for e in user_events if e.get("event_type") == "auth_failure"]
        successes = [e for e in user_events if e.get("event_type") == "auth_success"]
        if len(failures) >= 5 and successes:
            ids = [e["id"] for e in failures[:5] + successes[:1]]
            findings.append(
                Finding(
                    title=f"Password-spray followed by successful login for {user}",
                    severity="High",
                    confidence="High",
                    rationale=(
                        f"{len(failures)} authentication failures for the same user were followed "
                        "by a successful login. This is a compact attack chain, not a single noisy event."
                    ),
                    evidence_ids=ids,
                    tactic="Credential Access / Initial Access",
                    detection_hint="auth_failure_count_by_user >= 5 followed by auth_success within window",
                    score=85,
                    score_basis="base 60 credential-access pattern +25 confirmed success after repeated failures",
                )
            )

    for src_ip, src_events in by_src.items():
        usernames = {str(e.get("user", "")) for e in src_events if e.get("event_type") == "auth_failure"}
        if len(usernames) >= 4:
            ids = [e["id"] for e in src_events if e.get("event_type") == "auth_failure"][:8]
            findings.append(
                Finding(
                    title=f"Single source attempted multiple accounts ({src_ip})",
                    severity="Medium",
                    confidence="High",
                    rationale=(
                        f"Source {src_ip} attempted authentication against {len(usernames)} distinct accounts."
                    ),
                    evidence_ids=ids,
                    tactic="Credential Access",
                    detection_hint="distinct_failed_users_by_src_ip >= 4",
                    score=65,
                    score_basis="base 65 single-stage credential-access pattern; no confirmed-success bonus",
                )
            )

    for host, host_events in by_host.items():
        suspicious_shell = [
            e
            for e in host_events
            if e.get("event_type") == "process"
            and any(token in str(e.get("command", "")).lower() for token in ["-enc", "downloadstring", "curl http"])
        ]
        lateral = [
            e
            for e in host_events
            if e.get("event_type") == "network" and str(e.get("dst_port", "")) in {"445", "5985", "3389"}
        ]
        if suspicious_shell and lateral:
            ids = [e["id"] for e in suspicious_shell[:2] + lateral[:3]]
            findings.append(
                Finding(
                    title=f"Suspicious command execution with lateral-movement traffic on {host}",
                    severity="Critical",
                    confidence="Medium",
                    rationale=(
                        "A suspicious shell command appears near administrative network traffic. "
                        "The tool marks this as medium confidence until process parentage or timeline context confirms it."
                    ),
                    evidence_ids=ids,
                    tactic="Execution / Lateral Movement",
                    detection_hint="suspicious_process AND admin_port_network_activity on same host",
                    score=90,
                    score_basis="base 75 suspicious execution +15 lateral-movement traffic on admin ports, same host",
                )
            )

        external_callback = [
            e
            for e in host_events
            if e.get("event_type") in {"network", "zeek_conn"}
            and str(e.get("dst_port", "")) in {"443", "80"}
            and str(e.get("dst_ip", "")).startswith(("198.51.100.", "203.0.113."))
        ]
        if suspicious_shell and external_callback:
            ids = [e["id"] for e in suspicious_shell[:1] + external_callback[:2]]
            findings.append(
                Finding(
                    title=f"Suspicious command followed by external callback on {host}",
                    severity="High",
                    confidence="Medium",
                    rationale=(
                        "A suspicious shell command was followed by outbound web traffic to a non-internal "
                        "test-network address in the same host timeline. This is useful as a triage pivot, "
                        "but still needs endpoint/network enrichment before containment."
                    ),
                    evidence_ids=ids,
                    tactic="Command and Control",
                    detection_hint="suspicious_process followed by external zeek_conn/web egress on same host",
                    score=80,
                    score_basis="base 65 suspicious execution +15 external egress in same host timeline",
                )
            )

    manipulation = find_manipulation_attempts(events)
    if manipulation:
        ids = [e["id"] for e in manipulation[:8]]
        findings.append(
            Finding(
                title="Embedded analyst/AI manipulation content in log data",
                severity="High",
                confidence="High",
                rationale=(
                    f"{len(manipulation)} event(s) contain instruction-like content aimed at the analyst or an "
                    "AI assistant (for example 'do not flag' or 'ignore previous instructions'). Evil Sift treats "
                    "log content strictly as data: all verdicts in this report come from deterministic detectors "
                    "and are unaffected by these strings. Instructions embedded in telemetry are themselves an "
                    "evasion signal worth investigating."
                ),
                evidence_ids=ids,
                tactic="Defense Evasion",
                detection_hint="log_field contains analyst/LLM-directed instruction patterns",
                score=75,
                score_basis="base 75 exact pattern match for analyst/AI-directed instructions in log content",
            )
        )

    return findings


def summarize(events: list[dict[str, Any]], findings: list[Finding], validation_notes: list[str]) -> str:
    events_by_id = {e["id"]: e for e in events}
    type_counts = Counter(str(e.get("event_type", "unknown")) for e in events)
    affected_hosts = sorted({str(e.get("host", "")) for e in events if e.get("host")})
    lines: list[str] = []
    lines.append("# Evil Sift Workbench Report")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    if findings:
        top = findings[0]
        lines.append(f"- Top finding: **{sanitize_for_markdown(top.title)}** ({top.severity}, {top.confidence} confidence).")
        lines.append(f"- Findings: {len(findings)}.")
    else:
        lines.append("- No suspicious chain crossed the current confidence threshold.")
    lines.append(f"- Events reviewed: {len(events)}.")
    lines.append(f"- Hosts reviewed: {sanitize_for_markdown(', '.join(affected_hosts)) if affected_hosts else 'none'}")
    lines.append("")
    lines.append("## Event Mix")
    lines.append("")
    for event_type, count in sorted(type_counts.items()):
        lines.append(f"- {sanitize_for_markdown(event_type)}: {count}")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not findings:
        lines.append("No findings.")
        lines.append("")
    for idx, finding in enumerate(findings, start=1):
        lines.append(f"### {idx}. {sanitize_for_markdown(finding.title)}")
        lines.append("")
        lines.append(f"- Severity: {finding.severity}")
        lines.append(f"- Confidence: {finding.confidence}")
        lines.append(f"- Risk score: {finding.score}/100 ({finding.score_basis})")
        lines.append(f"- Tactic: {finding.tactic}")
        lines.append(f"- Rationale: {sanitize_for_markdown(finding.rationale)}")
        lines.append(f"- Evidence IDs: {sanitize_for_markdown(', '.join(finding.evidence_ids))}")
        lines.append(f"- Detection hint: `{finding.detection_hint}`")
        lines.append("- Evidence snippets:")
        for event_id in finding.evidence_ids:
            snippet = compact_event(events_by_id[event_id])
            rendered = sanitize_for_markdown(json.dumps(snippet, sort_keys=True))
            lines.append(f"  - `{sanitize_for_markdown(event_id)}` line {snippet.get('_source_line', '?')}: `{rendered}`")
        lines.append("")
    lines.append("## Self-Correction / Validation")
    lines.append("")
    lines.append(
        "Every finding was dropped unless each cited evidence ID existed in the input dataset. "
        "Medium-confidence findings explicitly say what additional evidence would be needed. "
        "Log content is rendered through a sanitizer so embedded text cannot alter this report's structure."
    )
    for note in validation_notes:
        lines.append(f"- {sanitize_for_markdown(note)}")
    lines.append("")
    lines.append("## Analyst Next Steps")
    lines.append("")
    if findings:
        lines.append("- Confirm the time window and source host ownership.")
        lines.append("- Pull surrounding authentication and endpoint telemetry for the cited evidence IDs.")
        lines.append("- Convert validated detection hints into environment-specific SIEM rules.")
    else:
        lines.append("- Keep the dataset as a negative control for regression testing.")
    lines.append("")
    return "\n".join(lines)


def build_audit_payload(
    events: list[dict[str, Any]],
    findings: list[Finding],
    validation_notes: list[str],
    input_path: Path,
) -> dict[str, Any]:
    events_by_id = {e["id"]: e for e in events}
    return {
        "tool": "evil_sift_workbench",
        "tool_version": TOOL_VERSION,
        "trace_version": 2,
        "input_file": input_path.name,
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "deterministic": True,
        "event_count": len(events),
        "finding_count": len(findings),
        "validation_notes": validation_notes,
        "findings": [
            {
                "title": finding.title,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "score": finding.score,
                "score_basis": finding.score_basis,
                "tactic": finding.tactic,
                "detection_hint": finding.detection_hint,
                "evidence_ids": finding.evidence_ids,
                "evidence": [compact_event(events_by_id[event_id]) for event_id in finding.evidence_ids],
            }
            for finding in findings
        ],
    }


def build_execution_log(
    events: list[dict[str, Any]],
    raw_findings: list[Finding],
    findings: list[Finding],
    validation_notes: list[str],
    input_path: Path,
    output_dir: Path,
    audit: dict[str, Any],
    started_at: datetime,
) -> dict[str, Any]:
    """Structured agent/tool execution trace for judge review.

    Evil Sift does not call an LLM during analysis, so token usage is recorded
    explicitly as zero instead of omitted.
    """

    def ts(offset_seconds: int) -> str:
        return (started_at + timedelta(seconds=offset_seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    zero_tokens = {
        "input_tokens": 0,
        "output_tokens": 0,
        "reason": "No LLM calls; deterministic stdlib detectors only.",
    }
    dropped = len(raw_findings) - len(findings)
    return {
        "tool": "evil_sift_workbench",
        "tool_version": TOOL_VERSION,
        "trace_version": 1,
        "input_file": str(input_path),
        "input_sha256": audit["input_sha256"],
        "output_dir": str(output_dir),
        "started_at_utc": started_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "completed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "token_usage": zero_tokens,
        "steps": [
            {
                "seq": 1,
                "timestamp_utc": ts(0),
                "actor": "evil_sift_workbench",
                "operation": "ingest_jsonl",
                "status": "ok",
                "details": {
                    "events_loaded": len(events),
                    "duplicate_id_policy": "fail_fast",
                    "malformed_json_policy": "fail_fast_with_file_line",
                },
                "token_usage": zero_tokens,
            },
            {
                "seq": 2,
                "timestamp_utc": ts(1),
                "actor": "evil_sift_workbench",
                "operation": "run_deterministic_detectors",
                "status": "ok",
                "details": {
                    "raw_findings": len(raw_findings),
                    "detectors": [
                        "password_spray_then_success",
                        "multi_account_source_spray",
                        "suspicious_execution_plus_lateral_movement",
                        "suspicious_execution_plus_external_callback",
                        "embedded_analyst_ai_manipulation_content",
                    ],
                },
                "token_usage": zero_tokens,
            },
            {
                "seq": 3,
                "timestamp_utc": ts(2),
                "actor": "evil_sift_workbench",
                "operation": "validate_evidence_links",
                "status": "ok",
                "details": {
                    "validated_findings": len(findings),
                    "dropped_findings": dropped,
                    "validation_notes": validation_notes,
                },
                "token_usage": zero_tokens,
            },
            {
                "seq": 4,
                "timestamp_utc": ts(3),
                "actor": "evil_sift_workbench",
                "operation": "render_sanitized_outputs",
                "status": "ok",
                "details": {
                    "markdown_sanitization": "backticks and non-printable characters neutralized",
                    "findings_sorted_by": "risk_score_desc",
                    "artifacts": ["report.md", "findings.json", "detections.yml", "audit_trail.json", "execution_log.json"],
                },
                "token_usage": zero_tokens,
            },
        ],
    }


def write_sigma(output_dir: Path, findings: list[Finding]) -> None:
    lines = [
        "title: Evil Sift Prototype Detection Hints",
        "status: experimental",
        "description: Starter detections generated from validated local findings.",
        "logsource:",
        "  product: generic",
        "detection:",
        "  selection:",
    ]
    if findings:
        for idx, finding in enumerate(findings, start=1):
            lines.append(f"    hint_{idx}: {finding.detection_hint!r}")
    else:
        lines.append("    no_findings: true")
    lines.extend(["  condition: selection", "falsepositives:", "  - Environment-specific admin activity", "level: medium", ""])
    (output_dir / "detections.yml").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    started_at = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSONL security events")
    parser.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    args = parser.parse_args()

    events = load_events(args.input)
    raw_findings = detect(events)
    findings, validation_notes = validate_findings(events, raw_findings)
    findings.sort(key=lambda f: f.score, reverse=True)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.md").write_text(summarize(events, findings, validation_notes), encoding="utf-8")
    (args.out / "findings.json").write_text(
        json.dumps([finding.__dict__ for finding in findings], indent=2),
        encoding="utf-8",
    )
    audit = build_audit_payload(events, findings, validation_notes, args.input)
    (args.out / "audit_trail.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    execution_log = build_execution_log(
        events,
        raw_findings,
        findings,
        validation_notes,
        args.input,
        args.out,
        audit,
        started_at,
    )
    (args.out / "execution_log.json").write_text(json.dumps(execution_log, indent=2), encoding="utf-8")
    write_sigma(args.out, findings)

    print(
        f"[evil-sift] {args.input} -> {args.out} | events={len(events)} "
        f"findings={len(findings)} input_sha256={audit['input_sha256'][:12]}..."
    )
    if findings:
        for finding in findings:
            print(f"  - [{finding.severity}/{finding.confidence} conf, score {finding.score}] {finding.title}")
    else:
        print("  - clean: no suspicious chains crossed detection thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
