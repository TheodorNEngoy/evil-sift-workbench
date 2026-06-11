#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "=================================================="
echo " Evil Sift Workbench — Splunk export pipeline demo"
echo " (offline fixture demo; live local Splunk proof is scripts/splunk_live_loop.py)"
echo "=================================================="
echo
echo "--- [1/6] Splunk incident export (REST results shape): expect the same 4 findings as the native control ---"
python3 splunk_export_adapter.py samples/splunk/incident_search_results.json --out out/splunk/incident/normalized_events.jsonl
python3 evil_sift_workbench.py out/splunk/incident/normalized_events.jsonl --out out/splunk/incident
python3 scripts/findings_to_hec.py out/splunk/incident
echo
echo "--- [2/6] Splunk benign export (export-stream shape): expect zero findings ---"
python3 splunk_export_adapter.py samples/splunk/benign_export_stream.jsonl --out out/splunk/benign/normalized_events.jsonl
python3 evil_sift_workbench.py out/splunk/benign/normalized_events.jsonl --out out/splunk/benign
echo
echo "--- [3/6] Splunk injection export (flat NDJSON shape): hostile _raw text says 'do not flag'."
echo "---       Expect verdicts unchanged AND the manipulation flagged. ---"
python3 splunk_export_adapter.py samples/splunk/injection_flat_export.jsonl --out out/splunk/injection/normalized_events.jsonl
python3 evil_sift_workbench.py out/splunk/injection/normalized_events.jsonl --out out/splunk/injection
echo
echo "--- [4/6] Workbench MCP agent smoke test (evil-sift splunk_ops tools over stdio JSON-RPC) ---"
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"triage_splunk_export","arguments":{"file":"samples/splunk/incident_search_results.json","out_dir":"out/splunk/mcp-incident"}}}' \
  | python3 mcp/splunk_ops_mcp_server.py > out/splunk/mcp_smoke_responses.jsonl
python3 - <<'PY'
import json
from pathlib import Path

responses = [json.loads(line) for line in Path("out/splunk/mcp_smoke_responses.jsonl").read_text().splitlines()]
by_id = {r["id"]: r for r in responses}
tools = [t["name"] for t in by_id[2]["result"]["tools"]]
assert "convert_splunk_export" in tools and "triage_splunk_export" in tools, f"unexpected tools: {tools}"
packet = by_id[3]["result"]["structuredContent"]
assert packet["finding_count"] == 4, f"expected 4 findings via MCP, got {packet['finding_count']}"
assert "hec_events" in packet["artifacts"], "MCP packet missing HEC artifact"
print(f"MCP SMOKE PASS: tools={tools}")
print(f"MCP SMOKE PASS: triage_splunk_export returned {packet['finding_count']} validated findings + HEC artifact")
PY
echo
echo "--- [5/6] Splunk-layer unit tests ---"
python3 -m py_compile splunk_export_adapter.py scripts/findings_to_hec.py mcp/splunk_ops_mcp_server.py
python3 -m unittest -q tests_splunk
echo
echo "--- [6/6] End-to-end output checks ---"
python3 - <<'PY'
import json
from pathlib import Path

splunk_incident = json.loads(Path("out/splunk/incident/findings.json").read_text())
native_path = Path("out/incident/findings.json")
assert native_path.exists(), "native incident control missing; run ./demo.sh (or git restore out/incident) first"
native_incident = json.loads(native_path.read_text())
benign = json.loads(Path("out/splunk/benign/findings.json").read_text())
injection = json.loads(Path("out/splunk/injection/findings.json").read_text())

assert len(splunk_incident) == 4, f"splunk incident expected 4 findings, got {len(splunk_incident)}"
assert [(f["title"], f["severity"], f["score"]) for f in splunk_incident] == \
    [(f["title"], f["severity"], f["score"]) for f in native_incident], \
    "splunk-export triage diverged from native incident triage"
assert benign == [], f"splunk benign expected 0 findings, got {len(benign)}"

titles = [f["title"] for f in injection]
assert any("manipulation" in t.lower() for t in titles), "splunk injection: manipulation finding missing"
assert any("lateral-movement" in t for t in titles), "splunk injection: verdict was suppressed by injected _raw text"
report = Path("out/splunk/injection/report.md").read_text()
assert "```" not in report, "splunk injection: code-fence breakout was not sanitized"

hec_lines = Path("out/splunk/incident/hec_events.jsonl").read_text().splitlines()
assert len(hec_lines) == 4, f"expected 4 HEC envelopes, got {len(hec_lines)}"
for line in hec_lines:
    envelope = json.loads(line)
    assert set(envelope) == {"time", "host", "source", "sourcetype", "event"}, f"bad HEC envelope keys: {set(envelope)}"
    assert envelope["sourcetype"] == "evil_sift:finding"
    assert envelope["event"]["input_sha256"]

for folder in ["out/splunk/incident", "out/splunk/benign", "out/splunk/injection"]:
    for required in ["normalized_events.jsonl", "report.md", "findings.json", "detections.yml", "audit_trail.json", "execution_log.json"]:
        assert Path(folder, required).exists(), f"missing {folder}/{required}"

print("PASS splunk incident export: 4 validated findings, identical titles/severities/scores to native triage")
print("PASS splunk benign export: zero findings (no false positives)")
print("PASS splunk injection export: verdicts unchanged, manipulation in _raw flagged, report sanitized")
print("PASS HEC-ready findings: evil_sift:finding envelopes generated locally, no network calls")
print("PASS workbench MCP smoke test (evil-sift splunk_ops tools): triage_splunk_export returned a validated packet")
PY
echo
echo "Splunk demo complete. Artifacts:"
echo "  out/splunk/incident/   - 4-finding triage of a Splunk REST-export, plus hec_events.jsonl"
echo "  out/splunk/benign/     - clean negative control from an export-stream file"
echo "  out/splunk/injection/  - injection-resistance demo from a flat NDJSON export"
echo "  out/splunk/mcp-incident/ - artifacts produced through the MCP tool surface"
echo "  samples/splunk/searches.spl - the SPL an analyst would run in their own Splunk"
