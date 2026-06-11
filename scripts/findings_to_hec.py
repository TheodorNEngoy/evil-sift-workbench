#!/usr/bin/env python3
"""Convert validated Evil Sift findings into Splunk HEC-ready events.

Reads findings.json and audit_trail.json from a triage output directory and
writes hec_events.jsonl: one HTTP Event Collector envelope per finding, using
the documented /services/collector event JSON shape
({"time": ..., "host": ..., "source": ..., "sourcetype": ..., "event": {...}}).

This produces HEC-ready files locally; it never makes a network call. Posting
the file to a live HEC endpoint is the documented integration path:

  # In your own Splunk environment (requires a HEC token; not run by this repo):
  # while read -r line; do
  #   curl -s https://splunk.example:8088/services/collector/event \
  #     -H "Authorization: Splunk ${HEC_TOKEN}" -d "$line"
  # done < out/splunk/incident/hec_events.jsonl

Determinism: each envelope's time is the latest timestamp among the finding's
cited evidence events (taken from the audit trail), never wall-clock time, so
reruns produce byte-identical output for the same input.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HEC_SOURCE = "evil_sift_workbench"
HEC_SOURCETYPE = "evil_sift:finding"


def iso_to_epoch(value: str) -> float:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def build_hec_events(out_dir: Path) -> list[dict[str, Any]]:
    """Build HEC envelopes from a triage output directory's artifacts."""
    findings_path = out_dir / "findings.json"
    audit_path = out_dir / "audit_trail.json"
    for required in (findings_path, audit_path):
        if not required.exists():
            raise SystemExit(f"{required}: missing; run a triage into {out_dir} first")

    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_findings = audit.get("findings", [])
    if len(findings) != len(audit_findings):
        raise SystemExit(
            f"{out_dir}: findings.json and audit_trail.json disagree "
            f"({len(findings)} vs {len(audit_findings)} findings); rerun the triage"
        )

    envelopes: list[dict[str, Any]] = []
    # findings.json and audit_trail.json are written from the same sorted list
    # in the same run, so positions correspond; the title check guards drift.
    for finding, audit_entry in zip(findings, audit_findings):
        if finding["title"] != audit_entry["title"]:
            raise SystemExit(
                f"{out_dir}: finding order mismatch between findings.json and audit_trail.json "
                f"({finding['title']!r} vs {audit_entry['title']!r}); rerun the triage"
            )
        evidence = audit_entry.get("evidence", [])
        timestamps = [iso_to_epoch(e.get("ts") or e["timestamp"]) for e in evidence if e.get("ts") or e.get("timestamp")]
        if not timestamps:
            raise SystemExit(f"{out_dir}: no evidence timestamps for finding {finding['title']!r}")
        hosts = Counter(str(e["host"]) for e in evidence if e.get("host"))
        envelopes.append(
            {
                "time": max(timestamps),
                "host": hosts.most_common(1)[0][0] if hosts else HEC_SOURCE,
                "source": HEC_SOURCE,
                "sourcetype": HEC_SOURCETYPE,
                "event": {
                    "title": finding["title"],
                    "severity": finding["severity"],
                    "confidence": finding["confidence"],
                    "score": finding["score"],
                    "score_basis": finding.get("score_basis", ""),
                    "tactic": finding["tactic"],
                    "detection_hint": finding["detection_hint"],
                    "rationale": finding["rationale"],
                    "evidence_ids": finding["evidence_ids"],
                    "input_file": audit.get("input_file", ""),
                    "input_sha256": audit.get("input_sha256", ""),
                    "tool": audit.get("tool", "evil_sift_workbench"),
                    "tool_version": audit.get("tool_version", ""),
                },
            }
        )
    return envelopes


def write_hec_events(out_dir: Path) -> Path:
    envelopes = build_hec_events(out_dir)
    hec_path = out_dir / "hec_events.jsonl"
    hec_path.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in envelopes), encoding="utf-8")
    return hec_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("out_dir", type=Path, help="triage output directory containing findings.json and audit_trail.json")
    args = parser.parse_args()
    hec_path = write_hec_events(args.out_dir)
    count = len(hec_path.read_text(encoding="utf-8").splitlines())
    print(f"[findings-to-hec] {args.out_dir} -> {hec_path} | hec_events={count} sourcetype={HEC_SOURCETYPE}")
    print("[findings-to-hec] no network calls made; see module docstring for the documented HEC POST path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
