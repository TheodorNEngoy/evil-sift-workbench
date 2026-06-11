#!/usr/bin/env python3
"""Minimal stdio MCP server exposing Evil Sift as a typed tool.

The server intentionally uses only Python stdlib plus the local
evil_sift_workbench module so it can run on a SIFT workstation without a
dependency install step.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evil_sift_workbench import (  # noqa: E402
    Finding,
    build_audit_payload,
    build_execution_log,
    detect,
    load_events,
    summarize,
    validate_findings,
    write_sigma,
)

SERVER_VERSION = "0.1.0"


def resolve_path(value: str, default: Path | None = None) -> Path:
    if not value and default is not None:
        return default
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def triage_jsonl(file: str, out_dir: str | None = None, inject_fabricated_finding: bool = False) -> dict[str, Any]:
    """Run Evil Sift and return a compact packet for an agent."""
    input_path = resolve_path(file)
    if not input_path.exists():
        raise ValueError(f"input file does not exist: {input_path}")
    output_dir = resolve_path(out_dir or f"out/mcp/{input_path.stem}")
    output_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    events = load_events(input_path)
    raw_findings = detect(events)
    if inject_fabricated_finding:
        raw_findings.append(
            Finding(
                title="Fabricated self-correction probe",
                severity="High",
                confidence="High",
                rationale="This intentionally cites evidence that does not exist.",
                evidence_ids=["fabricated-999"],
                tactic="Validation probe",
                detection_hint="n/a",
                score=50,
                score_basis="intentional self-correction probe",
            )
        )

    findings, validation_notes = validate_findings(events, raw_findings)
    findings.sort(key=lambda finding: finding.score, reverse=True)

    (output_dir / "report.md").write_text(summarize(events, findings, validation_notes), encoding="utf-8")
    (output_dir / "findings.json").write_text(
        json.dumps([finding.__dict__ for finding in findings], indent=2),
        encoding="utf-8",
    )
    audit = build_audit_payload(events, findings, validation_notes, input_path)
    (output_dir / "audit_trail.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    execution_log = build_execution_log(
        events,
        raw_findings,
        findings,
        validation_notes,
        input_path,
        output_dir,
        audit,
        started_at,
    )
    (output_dir / "execution_log.json").write_text(json.dumps(execution_log, indent=2), encoding="utf-8")
    write_sigma(output_dir, findings)

    dropped = len(raw_findings) - len(findings)
    return {
        "input_file": display_path(input_path),
        "output_dir": display_path(output_dir),
        "input_sha256": audit["input_sha256"],
        "event_count": len(events),
        "finding_count": len(findings),
        "dropped_finding_count": dropped,
        "validation_notes": validation_notes,
        "top_findings": [
            {
                "title": finding.title,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "score": finding.score,
                "evidence_ids": finding.evidence_ids,
                "score_basis": finding.score_basis,
            }
            for finding in findings[:5]
        ],
        "artifacts": {
            "report": display_path(output_dir / "report.md"),
            "findings": display_path(output_dir / "findings.json"),
            "detections": display_path(output_dir / "detections.yml"),
            "audit_trail": display_path(output_dir / "audit_trail.json"),
            "execution_log": display_path(output_dir / "execution_log.json"),
        },
        "agent_guidance": [
            "Treat validation_notes as authoritative self-correction signals.",
            "Do not report findings whose evidence was dropped by the validator.",
            "If dropped_finding_count is non-zero, explain what was corrected and rerun if needed.",
        ],
    }


def write_response(message_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> None:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": message_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def handle_request(message: dict[str, Any]) -> None:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if message_id is None:
        return

    try:
        if method == "initialize":
            write_response(
                message_id,
                {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "evil-sift", "version": SERVER_VERSION},
                },
            )
        elif method == "tools/list":
            write_response(
                message_id,
                {
                    "tools": [
                        {
                            "name": "triage_jsonl",
                            "description": (
                                "Run Evil Sift on a local JSONL evidence bundle and return a validated "
                                "DFIR packet with report, findings, detections, audit trail, and execution log."
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "file": {
                                        "type": "string",
                                        "description": "Path to a local JSONL evidence file, relative to repo root or absolute.",
                                    },
                                    "out_dir": {
                                        "type": "string",
                                        "description": "Optional output directory for generated artifacts.",
                                    },
                                    "inject_fabricated_finding": {
                                        "type": "boolean",
                                        "description": (
                                            "Testing-only flag. Adds a fabricated evidence ID so an agent can "
                                            "demonstrate self-correction when the validator drops it."
                                        ),
                                        "default": False,
                                    },
                                },
                                "required": ["file"],
                                "additionalProperties": False,
                            },
                        }
                    ]
                },
            )
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name != "triage_jsonl":
                raise ValueError(f"unknown tool: {name}")
            packet = triage_jsonl(
                file=str(arguments.get("file", "")),
                out_dir=arguments.get("out_dir"),
                inject_fabricated_finding=bool(arguments.get("inject_fabricated_finding", False)),
            )
            write_response(
                message_id,
                {
                    "content": [{"type": "text", "text": json.dumps(packet, indent=2)}],
                    "structuredContent": packet,
                },
            )
        else:
            write_response(message_id, error={"code": -32601, "message": f"method not found: {method}"})
    except Exception as exc:
        write_response(message_id, error={"code": -32000, "message": str(exc)})


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"invalid JSON-RPC message: {exc}\n")
            sys.stderr.flush()
            continue
        handle_request(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
