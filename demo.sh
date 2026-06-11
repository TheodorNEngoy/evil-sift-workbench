#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "=============================================="
echo " Evil Sift Workbench demo (local fake data)"
echo "=============================================="
echo
echo "--- [1/7] Incident sample: expect a 4-finding attack chain ---"
python3 evil_sift_workbench.py samples/incident.jsonl --out out/incident
echo
echo "--- [2/7] Benign control: expect zero findings ---"
python3 evil_sift_workbench.py samples/benign.jsonl --out out/benign
echo
echo "--- [3/7] Prompt-injection control: logs tell the tool 'do not flag'."
echo "---       Expect verdicts unchanged AND the manipulation flagged. ---"
python3 evil_sift_workbench.py samples/injection.jsonl --out out/injection
echo
echo "--- [4/7] Self-correction guard: fabricated evidence must be dropped ---"
python3 - <<'PY'
from pathlib import Path
from evil_sift_workbench import Finding, load_events, validate_findings

events = load_events(Path("samples/benign.jsonl"))
fabricated = Finding(
    title="Fabricated finding",
    severity="High",
    confidence="High",
    rationale="This finding cites evidence that does not exist.",
    evidence_ids=["fake-999"],
    tactic="Validation test",
    detection_hint="n/a",
    score=50,
)
validated, notes = validate_findings(events, [fabricated])
assert validated == []
assert any("fake-999" in note for note in notes)
print("SELF-CORRECTION PASS: fabricated finding dropped before report rendering")
print(f"SELF-CORRECTION NOTE: {notes[0]}")
PY
echo
echo "--- [5/7] Local Custom MCP Server agent workflow smoke test ---"
python3 scripts/local_agent_demo.py
echo
echo "--- [6/7] Unit tests ---"
python3 -m py_compile evil_sift_workbench.py
python3 -m unittest -q tests
echo
echo "--- [7/7] End-to-end output checks ---"
python3 - <<'PY'
import json
from pathlib import Path

incident = json.loads(Path("out/incident/findings.json").read_text())
benign = json.loads(Path("out/benign/findings.json").read_text())
injection = json.loads(Path("out/injection/findings.json").read_text())

assert len(incident) == 4, f"incident expected 4 findings, got {len(incident)}"
assert benign == [], f"benign control expected 0 findings, got {len(benign)}"

titles = [f["title"] for f in injection]
assert any("manipulation" in t.lower() for t in titles), "injection control: manipulation finding missing"
assert any("lateral-movement" in t for t in titles), "injection control: verdict was suppressed by injected text"

report = Path("out/injection/report.md").read_text()
assert "```" not in report, "injection control: code-fence breakout was not sanitized"

for folder in ["out/incident", "out/benign", "out/injection"]:
    for required in ["report.md", "findings.json", "detections.yml", "audit_trail.json", "execution_log.json"]:
        assert Path(folder, required).exists(), f"missing {folder}/{required}"
    audit = json.loads(Path(folder, "audit_trail.json").read_text())
    assert len(audit["input_sha256"]) == 64, f"{folder}: audit trail missing input hash"
    execution_log = json.loads(Path(folder, "execution_log.json").read_text())
    assert execution_log["token_usage"]["input_tokens"] == 0, f"{folder}: unexpected input token usage"
    assert execution_log["token_usage"]["output_tokens"] == 0, f"{folder}: unexpected output token usage"
    assert len(execution_log["steps"]) >= 4, f"{folder}: execution log missing steps"

agent_log = Path("out/agent/agent_execution_log.json")
agent_narrative = Path("out/agent/investigative_narrative.md")
assert agent_log.exists(), "missing local MCP-style agent execution log"
assert agent_narrative.exists(), "missing local MCP-style investigative narrative"

print("PASS incident: 4 validated findings, each citing concrete evidence IDs")
print("PASS benign control: zero findings (no false positives)")
print("PASS injection control: verdicts unchanged, manipulation attempt flagged, report sanitized")
print("PASS MCP agent smoke test: tool workflow produced narrative and self-correction log")
print("PASS audit trails + execution logs: input SHA-256 and deterministic traces recorded")
PY
echo
echo "Demo complete. Artifacts:"
echo "  out/incident/report.md   - 4-finding attack-chain report"
echo "  out/benign/report.md     - clean negative control"
echo "  out/injection/report.md  - injection-resistance demonstration"
echo "  out/*/execution_log.json - structured tool execution traces"
echo "  out/agent/               - Custom MCP Server workflow smoke-test artifacts"
