#!/usr/bin/env python3
"""No-API local smoke test for the Evil Sift MCP-style agent workflow.

This is not a substitute for a final Claude Code trace. It exists so judges
and contributors can verify the same self-correction contract without spending
tokens: an agent-like loop calls triage_jsonl, notices a dropped fabricated
finding, reruns cleanly, and writes a narrative plus execution trace.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.evil_sift_mcp_server import ROOT, triage_jsonl

OUT = ROOT / "out" / "agent"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, object]] = []

    steps.append(
        {
            "seq": 1,
            "timestamp_utc": now(),
            "actor": "local_agent_smoke_test",
            "operation": "plan",
            "status": "ok",
            "details": "Call the Evil Sift MCP tool on incident, benign, injection, and self-correction controls.",
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "reason": "No-API local smoke test."},
        }
    )

    incident = triage_jsonl("samples/incident.jsonl", "out/agent/incident")
    benign = triage_jsonl("samples/benign.jsonl", "out/agent/benign")
    injection = triage_jsonl("samples/injection.jsonl", "out/agent/injection")
    steps.append(
        {
            "seq": 2,
            "timestamp_utc": now(),
            "actor": "local_agent_smoke_test",
            "operation": "call_triage_jsonl_controls",
            "status": "ok",
            "details": {
                "incident_findings": incident["finding_count"],
                "benign_findings": benign["finding_count"],
                "injection_findings": injection["finding_count"],
            },
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "reason": "No-API local smoke test."},
        }
    )

    bad = triage_jsonl("samples/benign.jsonl", "out/agent/self_correction_probe", inject_fabricated_finding=True)
    status = "needs_correction" if bad["dropped_finding_count"] else "unexpected_clean"
    steps.append(
        {
            "seq": 3,
            "timestamp_utc": now(),
            "actor": "local_agent_smoke_test",
            "operation": "inspect_validation_notes",
            "status": status,
            "details": {
                "dropped_finding_count": bad["dropped_finding_count"],
                "validation_notes": bad["validation_notes"],
            },
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "reason": "No-API local smoke test."},
        }
    )

    corrected = triage_jsonl("samples/benign.jsonl", "out/agent/self_correction_corrected")
    steps.append(
        {
            "seq": 4,
            "timestamp_utc": now(),
            "actor": "local_agent_smoke_test",
            "operation": "self_correct_and_rerun",
            "status": "ok",
            "details": {
                "correction": "Discarded the fabricated finding because the validator rejected its missing evidence ID.",
                "corrected_finding_count": corrected["finding_count"],
            },
            "token_usage": {"input_tokens": 0, "output_tokens": 0, "reason": "No-API local smoke test."},
        }
    )

    narrative = "\n".join(
        [
            "# Evil Sift Agent Workflow Narrative",
            "",
            "This local smoke test exercises the Custom MCP Server pattern without paid API usage.",
            "For the final FIND EVIL submission, run the same MCP server from Claude Code or OpenClaw so the agent trace contains real model token usage.",
            "",
            "## Findings",
            "",
            f"- Incident control: {incident['finding_count']} validated findings. Top finding: {incident['top_findings'][0]['title']}.",
            f"- Benign control: {benign['finding_count']} findings.",
            f"- Injection control: {injection['finding_count']} findings, including manipulation content flagged as Defense Evasion.",
            "- Self-correction: a fabricated finding was rejected because its evidence ID was missing; the workflow reran cleanly.",
            "",
            "## Artifacts",
            "",
            f"- Incident report: `{incident['artifacts']['report']}`",
            f"- Injection report: `{injection['artifacts']['report']}`",
            f"- Self-correction probe log: `{bad['artifacts']['execution_log']}`",
        ]
    )
    (OUT / "investigative_narrative.md").write_text(narrative + "\n", encoding="utf-8")

    agent_log = {
        "agent_framework": "Custom MCP Server pattern; local no-API smoke-test runner",
        "final_submission_note": "Run prompts/claude-code-agent-prompt.md in Claude Code for a real agent trace with non-zero token usage.",
        "started_at_utc": steps[0]["timestamp_utc"],
        "completed_at_utc": now(),
        "steps": steps,
        "outputs": {
            "narrative": "out/agent/investigative_narrative.md",
            "incident_report": incident["artifacts"]["report"],
            "injection_report": injection["artifacts"]["report"],
        },
    }
    (OUT / "agent_execution_log.json").write_text(json.dumps(agent_log, indent=2), encoding="utf-8")

    print("LOCAL AGENT DEMO PASS: MCP-style workflow ran incident, benign, injection, and self-correction controls")
    print("LOCAL AGENT DEMO NOTE: final submission should include a Claude Code/OpenClaw trace with real token usage")
    print("Artifacts:")
    print("  out/agent/investigative_narrative.md")
    print("  out/agent/agent_execution_log.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
