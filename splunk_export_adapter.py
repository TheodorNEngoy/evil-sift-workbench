#!/usr/bin/env python3
"""
Splunk export adapter for Evil Sift Workbench.

Converts Splunk search-result JSON exports into the normalized JSONL event
shape that `evil_sift_workbench.py` triages. This is the offline
"Splunk-export-ready" adapter boundary: an analyst can run SPL in their own
Splunk environment, export the results as JSON, and feed the export file to
this adapter. The separate localhost live proof is implemented in
`scripts/splunk_live_loop.py`.

Accepted input shapes (all real Splunk export formats):
1. REST results document: one JSON object with a "results" list, as returned
   by GET /services/search/jobs/{sid}/results?output_mode=json.
2. Export stream: newline-delimited JSON objects each wrapping a row under a
   "result" key, as returned by /services/search/jobs/export?output_mode=json.
3. Flat NDJSON: newline-delimited flat result objects, the shape analysts get
   after post-processing an export with jq or similar.

Field mapping is aligned with Splunk CIM conventions (Authentication,
Endpoint.Processes, Network_Traffic) plus Zeek conn fields, and is documented
in docs/splunk-agentic-ops/. Splunk provenance (index, sourcetype, source) and
a truncated _raw copy are preserved on every normalized event so manipulation
content embedded in raw log text still reaches Evil Sift's detectors.

Design rules match the core engine: stdlib only, deterministic, fail fast with
file:line context, and log content is data — never an instruction.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evil_sift_workbench import MANIPULATION_PATTERNS

ADAPTER_VERSION = "0.1.0"

RAW_PRESERVE_LIMIT = 1000

EPOCH_RE = re.compile(r"^\d{9,13}(?:\.\d+)?$")


def epoch_to_utc(epoch: float, context: str) -> datetime:
    # Magnitude decides seconds vs milliseconds: 1e11 seconds is year 5138,
    # while millisecond timestamps only reach 11+ digits after 1973.
    if abs(epoch) >= 1e11:
        epoch /= 1000.0
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise SystemExit(f"{context}: _time epoch value {epoch!r} is out of range")


def normalize_time(value: Any, context: str) -> str:
    """Normalize a Splunk _time value (epoch or ISO-8601) to UTC ISO-8601 Z."""
    if isinstance(value, (int, float)):
        moment = epoch_to_utc(float(value), context)
    else:
        text = str(value).strip()
        if not text:
            raise SystemExit(f"{context}: empty _time value")
        if EPOCH_RE.match(text):
            moment = epoch_to_utc(float(text), context)
        else:
            iso_candidate = text.replace("Z", "+00:00")
            # Splunk export streams can render _time as "2026-06-10 08:04:50.000 GMT".
            if iso_candidate.endswith((" GMT", " UTC")):
                iso_candidate = iso_candidate[:-4] + "+00:00"
            try:
                moment = datetime.fromisoformat(iso_candidate)
            except ValueError:
                raise SystemExit(f"{context}: unrecognized _time value {text!r}")
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def first_value(row: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-empty value among keys (Splunk multivalue lists collapse to their first entry)."""
    for key in keys:
        value = row.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        if value not in (None, ""):
            return value
    return None


def classify(row: dict[str, Any]) -> tuple[str, str | None]:
    """Map a Splunk result row to an Evil Sift event_type.

    Decision ladder (first match wins):
    sourcetype zeek/bro conn -> zeek_conn; Sysmon EventCode 1/3 -> process/network;
    Windows EventCode 4625/4624 -> auth_failure/auth_success; CIM Authentication
    action failure/success -> auth_failure/auth_success; process fields present ->
    process; destination port present -> network; otherwise log_note.
    """
    # Splunk add-ons split provenance across sourcetype and source (e.g. the
    # Windows add-on uses sourcetype=XmlWinEventLog with the channel in source),
    # so classification checks both.
    provenance = " ".join(
        str(first_value(row, key) or "") for key in ("sourcetype", "_sourcetype", "source")
    ).lower()
    if ("zeek" in provenance or "bro" in provenance) and "conn" in provenance:
        return "zeek_conn", "zeek_conn"

    event_code = str(first_value(row, "EventCode", "EventID", "event_code") or "")
    if "sysmon" in provenance:
        if event_code == "1":
            return "process", None
        if event_code == "3":
            return "network", None
    if event_code == "4625":
        return "auth_failure", None
    if event_code == "4624":
        return "auth_success", None

    action = str(first_value(row, "action") or "").lower()
    if action in {"failure", "failed"}:
        return "auth_failure", None
    if action == "success":
        return "auth_success", None

    if first_value(row, "process", "CommandLine", "parent_process", "parent_process_name"):
        return "process", None
    if first_value(row, "dest_port", "dst_port", "id.resp_p"):
        return "network", None
    return str(first_value(row, "eventtype") or "log_note"), None


def normalize_row(row: dict[str, Any], seq: int, context: str) -> dict[str, Any]:
    """Convert one Splunk result row into a normalized Evil Sift event."""
    if not isinstance(row, dict):
        raise SystemExit(f"{context}: expected a JSON object result row")
    time_value = first_value(row, "_time", "time")
    if time_value is None:
        raise SystemExit(f"{context}: result row is missing _time")

    event_type, artifact_type = classify(row)
    event: dict[str, Any] = {
        "id": f"spl-{seq:05d}",
        "ts": normalize_time(time_value, context),
        "event_type": event_type,
    }
    if artifact_type:
        event["artifact_type"] = artifact_type

    # Zeek conn rows prefer an asset-enriched orig_host (see samples/splunk/searches.spl);
    # everything else uses Splunk's host metadata, then CIM dest.
    if event_type == "zeek_conn":
        host = first_value(row, "orig_host", "host", "dest")
    else:
        host = first_value(row, "host", "dest")
    if host:
        event["host"] = str(host)

    user = first_value(row, "user", "src_user", "User")
    if user:
        event["user"] = str(user)

    src_ip = first_value(row, "src", "src_ip", "id.orig_h")
    if src_ip:
        event["src_ip"] = str(src_ip)

    dst_ip = first_value(row, "dest_ip", "dst_ip", "id.resp_h")
    if dst_ip is None and event_type in {"network", "zeek_conn"}:
        dst_ip = first_value(row, "dest")
    if dst_ip:
        event["dst_ip"] = str(dst_ip)

    dst_port = first_value(row, "dest_port", "dst_port", "id.resp_p")
    if dst_port is not None:
        event["dst_port"] = int(dst_port) if str(dst_port).isdigit() else str(dst_port)

    proto = first_value(row, "transport", "proto")
    if proto:
        event["proto"] = str(proto)

    command = first_value(row, "process", "CommandLine")
    if command:
        event["command"] = str(command)

    parent = first_value(row, "parent_process_name", "parent_process")
    if parent:
        event["parent"] = str(parent)

    detail = first_value(row, "signature", "detail")
    if detail:
        event["detail"] = str(detail)

    for provenance_key in ("index", "sourcetype", "source"):
        value = first_value(row, provenance_key)
        if value:
            event[provenance_key] = str(value)
    raw = first_value(row, "_raw")
    if raw:
        event["splunk_raw"] = preserve_raw(str(raw))
    return event


def preserve_raw(raw: str) -> str:
    """Truncate _raw for storage without losing manipulation evidence.

    The truncated copy is what downstream detectors scan, so any manipulation
    pattern occurring past the truncation limit is excerpted and appended —
    an attacker cannot evade the Defense Evasion detector by padding the log
    line. The preserved text stays data; it is never rendered unsanitized
    (it is not part of the report's evidence-snippet field list).
    """
    kept = raw[:RAW_PRESERVE_LIMIT]
    if len(raw) <= RAW_PRESERVE_LIMIT:
        return kept
    lowered_full = raw.lower()
    lowered_kept = kept.lower()
    excerpts = []
    for pattern in MANIPULATION_PATTERNS:
        if pattern in lowered_full and pattern not in lowered_kept:
            start = lowered_full.index(pattern)
            excerpts.append(raw[max(0, start - 40) : start + len(pattern) + 40])
    if excerpts:
        kept += " ...[truncated; instruction-like content preserved]... " + " ... ".join(excerpts)
    return kept


def read_export_rows(path: Path) -> list[tuple[dict[str, Any], str]]:
    """Read Splunk JSON export rows plus a file:line context string for each."""
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise SystemExit(f"{path}: export file is empty")

    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        document = None

    if isinstance(document, dict) and isinstance(document.get("results"), list):
        rows = [(row, f"{path}:results[{idx}]") for idx, row in enumerate(document["results"])]
        if not rows:
            raise SystemExit(f"{path}: no result rows found in export")
        return rows
    if isinstance(document, list):
        if not document:
            raise SystemExit(f"{path}: no result rows found in export")
        return [(row, f"{path}:[{idx}]") for idx, row in enumerate(document)]
    if isinstance(document, dict) and isinstance(document.get("result"), dict):
        return [(document["result"], f"{path}:result")]
    if isinstance(document, dict) and ("_time" in document or "time" in document):
        # A one-row flat NDJSON export parses as a single JSON document.
        return [(document, f"{path}:1")]
    if document is not None:
        raise SystemExit(f"{path}: unrecognized Splunk export shape (no results list or result rows)")

    rows: list[tuple[dict[str, Any], str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON ({exc.msg})")
        if not isinstance(obj, dict):
            raise SystemExit(f"{path}:{line_no}: expected a JSON object per line")
        if "result" in obj:
            if not isinstance(obj["result"], dict):
                raise SystemExit(f"{path}:{line_no}: 'result' wrapper is not an object")
            rows.append((obj["result"], f"{path}:{line_no}"))
        elif set(obj) <= {"preview", "offset", "lastrow", "messages", "fields", "init_offset"}:
            continue  # export-stream bookkeeping lines carry no result row
        else:
            rows.append((obj, f"{path}:{line_no}"))
    if not rows:
        raise SystemExit(f"{path}: no result rows found in export")
    return rows


def convert_export(path: Path) -> list[dict[str, Any]]:
    """Convert a Splunk JSON export file into normalized Evil Sift events."""
    rows = read_export_rows(path)
    return [normalize_row(row, seq, context) for seq, (row, context) in enumerate(rows, start=1)]


def write_jsonl(events: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("input", type=Path, help="Splunk JSON export (REST results, export stream, or flat NDJSON)")
    parser.add_argument("--out", type=Path, required=True, help="normalized JSONL output path")
    args = parser.parse_args()

    events = convert_export(args.input)
    write_jsonl(events, args.out)
    type_counts = sorted({e["event_type"] for e in events})
    print(
        f"[splunk-adapter] {args.input} -> {args.out} | rows={len(events)} "
        f"event_types={','.join(type_counts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
