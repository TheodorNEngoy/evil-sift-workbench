#!/usr/bin/env python3
"""Minimal stdio MCP server exposing the Splunk-export triage pipeline.

This is the agentic-ops surface for Splunk-shaped data: an MCP-capable agent
(Claude Code, or any MCP client) can convert a Splunk search-result JSON
export into normalized events, run the deterministic Evil Sift triage, and
get back validated findings plus HEC-ready events for the return trip into
Splunk. No live Splunk connection is made; consuming exports and emitting
HEC-ready files keeps the whole loop local and reproducible.

This server is additive: it imports and reuses the FIND EVIL submission's
`mcp/evil_sift_mcp_server.py` without modifying it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.evil_sift_mcp_server import (  # noqa: E402
    display_path,
    resolve_path,
    triage_jsonl,
    write_response,
)
from scripts.findings_to_hec import write_hec_events  # noqa: E402
from splunk_export_adapter import convert_export, write_jsonl  # noqa: E402

SERVER_VERSION = "0.1.0"

TOOLS = [
    {
        "name": "convert_splunk_export",
        "description": (
            "Convert a local Splunk search-result JSON export (REST results document, "
            "export stream, or flat NDJSON) into Evil Sift's normalized JSONL event shape. "
            "No live Splunk connection is made."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Path to a local Splunk JSON export, relative to repo root or absolute.",
                },
                "out": {
                    "type": "string",
                    "description": "Optional output path for the normalized JSONL.",
                },
            },
            "required": ["file"],
            "additionalProperties": False,
        },
    },
    {
        "name": "triage_splunk_export",
        "description": (
            "Full Splunk-export pipeline: convert a local Splunk JSON export to normalized "
            "events, run deterministic evidence-validated triage, and emit report, findings, "
            "detections, audit trail, execution log, and HEC-ready evil_sift:finding events "
            "for the documented return path into Splunk."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Path to a local Splunk JSON export, relative to repo root or absolute.",
                },
                "out_dir": {
                    "type": "string",
                    "description": "Optional output directory for generated artifacts.",
                },
            },
            "required": ["file"],
            "additionalProperties": False,
        },
    },
]


def convert_splunk_export(file: str, out: str | None = None) -> dict[str, Any]:
    input_path = resolve_path(file)
    if not input_path.exists():
        raise ValueError(f"input file does not exist: {input_path}")
    output_path = resolve_path(out or f"out/splunk/{input_path.stem}_normalized.jsonl")
    events = convert_export(input_path)
    write_jsonl(events, output_path)
    return {
        "input_file": display_path(input_path),
        "normalized_events": display_path(output_path),
        "event_count": len(events),
        "event_types": sorted({e["event_type"] for e in events}),
        "note": "Local conversion only; no Splunk connection was made.",
    }


def triage_splunk_export(file: str, out_dir: str | None = None) -> dict[str, Any]:
    input_path = resolve_path(file)
    if not input_path.exists():
        raise ValueError(f"input file does not exist: {input_path}")
    output_dir = resolve_path(out_dir or f"out/splunk/{input_path.stem}")
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = output_dir / "normalized_events.jsonl"
    events = convert_export(input_path)
    write_jsonl(events, normalized_path)

    packet = triage_jsonl(str(normalized_path), str(output_dir))
    hec_path = write_hec_events(output_dir)

    packet["splunk_export_file"] = display_path(input_path)
    packet["artifacts"]["normalized_events"] = display_path(normalized_path)
    packet["artifacts"]["hec_events"] = display_path(hec_path)
    packet["splunk_integration"] = {
        "status": "Splunk-export-ready offline tool; localhost live proof is scripts/splunk_live_loop.py.",
        "ingest_path": "Run the searches in samples/splunk/searches.spl, export as JSON, pass the file here.",
        "return_path": (
            "hec_events.jsonl rows use the HEC /services/collector event envelope with "
            "sourcetype evil_sift:finding; POSTing them to a live HEC endpoint is the "
            "documented next integration step."
        ),
        "mcp_path": (
            "Connecting this workbench alongside a Splunk MCP server, so an agent can run "
            "SPL and triage the results in one loop, is the documented next integration step."
        ),
    }
    return packet


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
                    "serverInfo": {"name": "evil-sift-splunk", "version": SERVER_VERSION},
                },
            )
        elif method == "tools/list":
            write_response(message_id, {"tools": TOOLS})
        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name == "convert_splunk_export":
                packet = convert_splunk_export(
                    file=str(arguments.get("file", "")),
                    out=arguments.get("out"),
                )
            elif name == "triage_splunk_export":
                packet = triage_splunk_export(
                    file=str(arguments.get("file", "")),
                    out_dir=arguments.get("out_dir"),
                )
            else:
                raise ValueError(f"unknown tool: {name}")
            write_response(
                message_id,
                {
                    "content": [{"type": "text", "text": json.dumps(packet, indent=2)}],
                    "structuredContent": packet,
                },
            )
        else:
            write_response(message_id, error={"code": -32601, "message": f"method not found: {method}"})
    except (Exception, SystemExit) as exc:
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
