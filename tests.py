"""Regression tests for Evil Sift Workbench. Run: python3 -m unittest -v tests"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from evil_sift_workbench import (
    Finding,
    build_audit_payload,
    build_execution_log,
    compact_event,
    detect,
    load_events,
    sanitize_for_markdown,
    summarize,
    validate_findings,
)
from mcp.evil_sift_mcp_server import triage_jsonl

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT / "samples"


def run_pipeline(sample: str):
    events = load_events(SAMPLES / sample)
    findings, notes = validate_findings(events, detect(events))
    return events, findings, notes


class IncidentDetectionTests(unittest.TestCase):
    def test_incident_sample_finds_the_full_chain(self):
        _, findings, _ = run_pipeline("incident.jsonl")
        titles = [f.title for f in findings]
        self.assertEqual(len(findings), 4)
        self.assertTrue(any("Password-spray" in t for t in titles))
        self.assertTrue(any("multiple accounts" in t for t in titles))
        self.assertTrue(any("lateral-movement" in t for t in titles))
        self.assertTrue(any("external callback" in t for t in titles))

    def test_every_finding_cites_resolvable_evidence(self):
        events, findings, _ = run_pipeline("incident.jsonl")
        ids = {e["id"] for e in events}
        for finding in findings:
            self.assertTrue(finding.evidence_ids)
            self.assertTrue(set(finding.evidence_ids) <= ids)

    def test_encoded_command_gets_decoded_preview(self):
        events, _, _ = run_pipeline("incident.jsonl")
        process = next(e for e in events if e["id"] == "ev-011")
        snippet = compact_event(process)
        self.assertEqual(snippet.get("decoded_command_preview"), "IEX")


class BenignControlTests(unittest.TestCase):
    def test_benign_sample_produces_zero_findings(self):
        _, findings, _ = run_pipeline("benign.jsonl")
        self.assertEqual(findings, [])


class EvidenceValidationTests(unittest.TestCase):
    def test_finding_with_fabricated_evidence_is_dropped_and_logged(self):
        events = load_events(SAMPLES / "benign.jsonl")
        fabricated = Finding(
            title="Fabricated finding",
            severity="High",
            confidence="High",
            rationale="cites evidence that does not exist",
            evidence_ids=["nope-999"],
            tactic="n/a",
            detection_hint="n/a",
            score=50,
        )
        validated, notes = validate_findings(events, [fabricated])
        self.assertEqual(validated, [])
        self.assertTrue(any("nope-999" in note for note in notes))


class PromptInjectionResistanceTests(unittest.TestCase):
    def test_verdicts_unchanged_and_manipulation_flagged(self):
        _, findings, _ = run_pipeline("injection.jsonl")
        titles = [f.title for f in findings]
        # The attack chain is still detected despite "do not flag" instructions.
        self.assertTrue(any("lateral-movement" in t for t in titles))
        self.assertTrue(any("external callback" in t for t in titles))
        # The manipulation attempt is itself surfaced as a finding.
        self.assertTrue(any("manipulation" in t.lower() for t in titles))

    def test_report_rendering_neutralizes_code_fence_breakout(self):
        events, findings, notes = run_pipeline("injection.jsonl")
        report = summarize(events, findings, notes)
        self.assertNotIn("```", report)
        self.assertIn("manipulation", report.lower())

    def test_sanitizer_strips_backticks_and_control_chars(self):
        self.assertEqual(sanitize_for_markdown("a`b\x07c"), "a'b c")


class AuditTrailTests(unittest.TestCase):
    def test_audit_payload_hashes_input_and_links_evidence(self):
        path = SAMPLES / "incident.jsonl"
        events = load_events(path)
        findings, notes = validate_findings(events, detect(events))
        payload = build_audit_payload(events, findings, notes, path)
        self.assertEqual(len(payload["input_sha256"]), 64)
        self.assertEqual(payload["finding_count"], len(findings))
        self.assertEqual(payload["event_count"], len(events))
        for entry in payload["findings"]:
            self.assertEqual(len(entry["evidence"]), len(entry["evidence_ids"]))
            self.assertTrue(entry["score_basis"])


class ExecutionLogTests(unittest.TestCase):
    def test_execution_log_records_steps_and_zero_token_usage(self):
        path = SAMPLES / "incident.jsonl"
        events = load_events(path)
        raw_findings = detect(events)
        findings, notes = validate_findings(events, raw_findings)
        audit = build_audit_payload(events, findings, notes, path)
        log = build_execution_log(events, raw_findings, findings, notes, path, ROOT / "out" / "incident", audit, datetime.now(timezone.utc))
        self.assertEqual(log["input_sha256"], audit["input_sha256"])
        self.assertEqual(log["token_usage"]["input_tokens"], 0)
        self.assertEqual(log["token_usage"]["output_tokens"], 0)
        self.assertGreaterEqual(len(log["steps"]), 4)
        self.assertEqual([step["seq"] for step in log["steps"]], list(range(1, len(log["steps"]) + 1)))
        self.assertTrue(any(step["operation"] == "validate_evidence_links" for step in log["steps"]))


class McpToolTests(unittest.TestCase):
    def test_triage_jsonl_returns_packet_and_artifacts(self):
        with TemporaryDirectory() as tmp:
            packet = triage_jsonl("samples/incident.jsonl", tmp)
            self.assertEqual(packet["finding_count"], 4)
            self.assertEqual(packet["dropped_finding_count"], 0)
            self.assertTrue(Path(packet["artifacts"]["report"]).is_absolute())
            self.assertTrue(Path(packet["artifacts"]["report"]).exists())

    def test_triage_jsonl_self_correction_probe_drops_fabricated_finding(self):
        with TemporaryDirectory() as tmp:
            packet = triage_jsonl("samples/benign.jsonl", tmp, inject_fabricated_finding=True)
            self.assertEqual(packet["finding_count"], 0)
            self.assertEqual(packet["dropped_finding_count"], 1)
            self.assertTrue(any("fabricated-999" in note for note in packet["validation_notes"]))


if __name__ == "__main__":
    unittest.main()
