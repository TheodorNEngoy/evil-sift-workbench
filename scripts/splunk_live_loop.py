#!/usr/bin/env python3
"""Optional live-loop proof against a LOCAL Splunk Enterprise trial in Docker.

This script is NOT part of the core demo (./demo-splunk.sh stays fully local
and Splunk-free). It exists to prove the documented integration paths against
a real, locally-running Splunk Enterprise trial container (splunk/splunk in
Docker), using only the fake sample data in this repo:

  1. POST the fake incident rows to the HTTP Event Collector (HEC).
  2. Search them back via the real /services/search/v2/jobs/export endpoint
     (the same export-stream shape the adapter supports).
  3. Feed the export to splunk_export_adapter.py + evil_sift_workbench.py.
  4. POST the validated findings back to HEC as evil_sift:finding events.
  5. Verify the findings are searchable in Splunk.

Connection settings come from the environment; nothing is hardcoded:
  SPLUNK_PASSWORD   admin password of the local trial container (required)
  SPLUNK_HEC_TOKEN  HEC token of the local trial container (required)
  SPLUNK_MGMT       management API base (default https://127.0.0.1:8089)
  SPLUNK_HEC        HEC base (default https://127.0.0.1:8088)
  SPLUNK_USER       admin user (default admin)

Local-only by design: it talks to localhost, uses an unverified TLS context
(the trial container generates self-signed certs), and never contacts any
external service. All data is fake.
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from splunk_export_adapter import convert_export, write_jsonl  # noqa: E402

OUT = ROOT / "out" / "splunk-live"
SAMPLE = ROOT / "samples" / "splunk" / "incident_search_results.json"

MGMT = os.environ.get("SPLUNK_MGMT", "https://127.0.0.1:8089")
HEC = os.environ.get("SPLUNK_HEC", "https://127.0.0.1:8088")
USER = os.environ.get("SPLUNK_USER", "admin")
PASSWORD = os.environ.get("SPLUNK_PASSWORD")
HEC_TOKEN = os.environ.get("SPLUNK_HEC_TOKEN")

EXPORT_FIELDS = (
    "_time host source sourcetype index EventCode action app user src dest Logon_Type "
    "signature process process_name parent_process_name src_ip dest_ip dest_port transport "
    "orig_host id.orig_h id.resp_h id.resp_p proto service conn_state orig_bytes resp_bytes "
    "evil_sift_run _raw"
)

SSL_CONTEXT = ssl._create_unverified_context()  # local self-signed trial certs only


def fail(message: str) -> None:
    raise SystemExit(f"[splunk-live-loop] FAIL: {message}")


def http(url: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(request, context=SSL_CONTEXT, timeout=timeout) as response:
        return response.read()


def mgmt_get(path: str, **params: str) -> dict:
    params.setdefault("output_mode", "json")
    url = f"{MGMT}{path}?{urllib.parse.urlencode(params)}"
    auth = b64encode(f"{USER}:{PASSWORD}".encode()).decode()
    return json.loads(http(url, headers={"Authorization": f"Basic {auth}"}))


def export_search(spl: str) -> str:
    """Run a search through the real export endpoint; returns the raw NDJSON stream."""
    url = f"{MGMT}/services/search/v2/jobs/export"
    data = urllib.parse.urlencode(
        {"search": spl, "output_mode": "json", "earliest_time": "0", "latest_time": "now"}
    ).encode()
    auth = b64encode(f"{USER}:{PASSWORD}".encode()).decode()
    return http(url, data=data, headers={"Authorization": f"Basic {auth}"}, timeout=120).decode()


def export_single_value(spl: str, field: str) -> str | None:
    for line in export_search(spl).splitlines():
        obj = json.loads(line)
        if isinstance(obj.get("result"), dict) and field in obj["result"]:
            return obj["result"][field]
    return None


def hec_post(payload: bytes) -> dict:
    return json.loads(
        http(
            f"{HEC}/services/collector/event",
            data=payload,
            headers={"Authorization": f"Splunk {HEC_TOKEN}", "Content-Type": "application/json"},
        )
    )


def iso_to_epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def main() -> int:
    if not PASSWORD or not HEC_TOKEN:
        fail("set SPLUNK_PASSWORD and SPLUNK_HEC_TOKEN in the environment (local trial credentials)")
    OUT.mkdir(parents=True, exist_ok=True)
    proof: dict = {"steps": []}
    run_id = f"evil-sift-live-{int(time.time())}"
    proof["run_id"] = run_id

    # 1. Confirm the local Splunk trial answers and record its identity.
    info = mgmt_get("/services/server/info")["entry"][0]["content"]
    proof["steps"].append(
        {
            "step": "server_info",
            "splunk_version": info["version"],
            "server_name": info["serverName"],
            "license_labels": info.get("activeLicenseSubgroup", "") or info.get("licenseLabels", ""),
            "os": f"{info.get('os_name', '?')} {info.get('cpu_arch', '?')}",
        }
    )
    print(f"[splunk-live-loop] local Splunk {info['version']} answering at {MGMT}")

    # 2. Ingest the fake incident rows through HEC, tagged with this run id.
    # Sourcetype is the pretrained `_json` (index-time JSON field extraction):
    # the bare trial container has no Windows/Sysmon/Zeek add-ons, and their
    # pretrained sourcetype props would suppress JSON field extraction. The
    # original channel stays in `source`, which is what the adapter's
    # classification uses (plus EventCode/action payload fields).
    rows = json.loads(SAMPLE.read_text(encoding="utf-8"))["results"]
    batch = []
    for row in rows:
        payload = {k: v for k, v in row.items() if k not in {"_time", "_raw", "host", "source", "sourcetype", "index"}}
        payload["evil_sift_run"] = run_id
        batch.append(
            json.dumps(
                {
                    "time": iso_to_epoch(row["_time"]),
                    "host": row["host"],
                    "source": row["source"],
                    "sourcetype": "_json",
                    "event": payload,
                }
            )
        )
    ack = hec_post("".join(batch).encode())
    if ack.get("code") != 0:
        fail(f"HEC ingest rejected: {ack}")
    proof["steps"].append({"step": "hec_ingest", "events_sent": len(batch), "hec_response": ack})
    print(f"[splunk-live-loop] HEC accepted {len(batch)} fake incident events: {ack}")

    # 3. Wait until all events are searchable.
    count_spl = f"search index=* evil_sift_run={run_id} | stats count"
    deadline = time.time() + 180
    count = "0"
    while time.time() < deadline:
        count = export_single_value(count_spl, "count") or "0"
        if count == str(len(batch)):
            break
        time.sleep(5)
    if count != str(len(batch)):
        fail(f"only {count}/{len(batch)} events searchable after 180s")
    proof["steps"].append({"step": "indexed", "searchable_events": int(count)})
    print(f"[splunk-live-loop] all {count} events searchable in Splunk")

    # 4. Export the rows through the real export endpoint (export-stream shape).
    export_spl = f"search index=* evil_sift_run={run_id} | fields {EXPORT_FIELDS}"
    stream = export_search(export_spl)
    export_path = OUT / "live_export.jsonl"
    export_path.write_text(stream, encoding="utf-8")
    proof["steps"].append({"step": "export", "spl": export_spl, "export_file": "out/splunk-live/live_export.jsonl"})
    print(f"[splunk-live-loop] export stream written to {export_path}")

    # 5. Adapter -> Evil Sift triage on the real export.
    events = convert_export(export_path)
    normalized_path = OUT / "normalized_events.jsonl"
    write_jsonl(events, normalized_path)
    subprocess.run(
        [sys.executable, str(ROOT / "evil_sift_workbench.py"), str(normalized_path), "--out", str(OUT / "triage")],
        check=True,
        cwd=ROOT,
    )
    findings = json.loads((OUT / "triage" / "findings.json").read_text(encoding="utf-8"))
    expected_titles = {
        "Suspicious command execution with lateral-movement traffic on srv01",
        "Password-spray followed by successful login for svc-backup",
        "Suspicious command followed by external callback on srv01",
        "Single source attempted multiple accounts (198.51.100.44)",
    }
    got_titles = {finding["title"] for finding in findings}
    if got_titles != expected_titles:
        fail(f"live-loop findings diverged from the native control: {sorted(got_titles)}")
    proof["steps"].append({"step": "triage", "finding_count": len(findings), "titles": sorted(got_titles)})
    print(f"[splunk-live-loop] Evil Sift produced the expected {len(findings)} findings from the live export")

    # 6. Return trip: POST validated findings back to HEC and verify searchable.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "findings_to_hec.py"), str(OUT / "triage")],
        check=True,
        cwd=ROOT,
    )
    hec_lines = (OUT / "triage" / "hec_events.jsonl").read_text(encoding="utf-8").splitlines()
    tagged = []
    for line in hec_lines:
        envelope = json.loads(line)
        envelope["event"]["evil_sift_run"] = run_id
        tagged.append(json.dumps(envelope))
    ack2 = hec_post("".join(tagged).encode())
    if ack2.get("code") != 0:
        fail(f"HEC findings ingest rejected: {ack2}")
    finding_count_spl = f'search index=* sourcetype="evil_sift:finding" evil_sift_run={run_id} | stats count'
    deadline = time.time() + 180
    fcount = "0"
    while time.time() < deadline:
        fcount = export_single_value(finding_count_spl, "count") or "0"
        if fcount == str(len(tagged)):
            break
        time.sleep(5)
    if fcount != str(len(tagged)):
        fail(f"only {fcount}/{len(tagged)} findings searchable after 180s")
    proof["steps"].append(
        {
            "step": "hec_return_trip",
            "findings_posted": len(tagged),
            "findings_searchable_as": "sourcetype=evil_sift:finding",
        }
    )
    print(f"[splunk-live-loop] {fcount} findings posted back to HEC and searchable as sourcetype=evil_sift:finding")

    proof["completed_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    proof["honest_wording"] = (
        "Tested against a local Splunk Enterprise trial (splunk/splunk Docker container). "
        "No Splunk Cloud, no external services, all data fake. The official Splunk MCP Server "
        "remains a documented integration path, not exercised here."
    )
    (OUT / "live_loop_proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(f"[splunk-live-loop] PASS: full loop proven; proof written to {OUT / 'live_loop_proof.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
