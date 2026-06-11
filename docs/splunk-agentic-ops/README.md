# Evil Sift Workbench — Splunk Agentic Ops Layer

Evil Sift Workbench is a local agentic security-investigation workbench: an
MCP-capable agent (Claude Code or any MCP client) orchestrates triage while a
deterministic evidence-integrity core makes the final calls. This layer makes
the workbench **Splunk-export-ready** with **HEC-ready output** and a
documented **Splunk MCP integration path** — without requiring a live Splunk
connection. The full ingest → export → triage → HEC loop has additionally been
**tested against a local Splunk Enterprise trial in Docker**
([live-loop-proof.md](live-loop-proof.md)); the core demo below stays fully
local and Splunk-free.

Everything runs locally, free, with fake data, in seconds:

```bash
./demo-splunk.sh
```

Expected final lines:

```
PASS splunk incident export: 4 validated findings, identical titles/severities/scores to native triage
PASS splunk benign export: zero findings (no false positives)
PASS splunk injection export: verdicts unchanged, manipulation in _raw flagged, report sanitized
PASS HEC-ready findings: evil_sift:finding envelopes generated locally, no network calls
PASS workbench MCP smoke test (evil-sift splunk_ops tools): triage_splunk_export returned a validated packet
```

## The loop

1. **SPL out.** An analyst runs the documented searches in
   [`samples/splunk/searches.spl`](../../samples/splunk/searches.spl) in their
   own Splunk environment and exports the results as JSON. This repo ships
   fake stand-ins for those exports in `samples/splunk/`, one per supported
   input shape:
   - `incident_search_results.json` — REST `results` document
     (`/services/search/v2/jobs/{sid}/results?output_mode=json`)
   - `benign_export_stream.jsonl` — newline-delimited `{"result": {...}}`
     stream (Splunk Web "Export > JSON" and `/jobs/export`)
   - `injection_flat_export.jsonl` — flat NDJSON (the common
     `jq '.result'`-post-processed idiom)
2. **Normalize.** [`splunk_export_adapter.py`](../../splunk_export_adapter.py)
   converts any of those shapes into the workbench's normalized JSONL using
   CIM-aligned field mapping (Authentication `action/user/src/dest`,
   Endpoint.Processes `process/parent_process_name`, Network_Traffic
   `dest_ip/dest_port/transport`, plus Zeek conn `id.orig_h`-style fields).
   Splunk provenance (`index`, `sourcetype`, `source`) and a truncated `_raw`
   copy are preserved on every event.
3. **Triage.** The unchanged Evil Sift core detects behavior chains, drops any
   finding whose cited evidence does not exist in the input, and renders
   sanitized evidence-linked artifacts (`report.md`, `findings.json`,
   `detections.yml`, `audit_trail.json`, `execution_log.json`).
4. **HEC back.** [`scripts/findings_to_hec.py`](../../scripts/findings_to_hec.py)
   emits each validated finding as an `evil_sift:finding` event in the
   documented HTTP Event Collector envelope (`hec_events.jsonl`). POSTing that
   file to a HEC endpoint — then viewing findings with
   `sourcetype=evil_sift:finding` — is the documented return path into Splunk.
   The quick judge demo does not make network calls; the optional live proof
   exercises this path against localhost only.
5. **Agentic surface.** [`mcp/splunk_ops_mcp_server.py`](../../mcp/splunk_ops_mcp_server.py)
   exposes the pipeline as MCP tools so an agent can drive steps 2–4 itself:
   - `convert_splunk_export(file, out)` — normalize an export
   - `triage_splunk_export(file, out_dir)` — full pipeline: normalize →
     evidence-validated triage → HEC-ready findings

## Why hostile telemetry is contained

Splunk-ingested logs are attacker-influenced text. The injection control
(`samples/splunk/injection_flat_export.jsonl`) hides "do not flag",
"ignore previous instructions", and a code-fence breakout inside `_raw`:

- Verdicts come from deterministic detectors; the attack chain is still
  reported at full severity.
- The manipulation content is itself flagged as a Defense Evasion finding.
- Rendered reports pass through a sanitizer, so `_raw` text cannot reshape the
  report or smuggle instructions to a downstream LLM.

## Splunk MCP integration path (documented, not demonstrated)

The official Splunk MCP Server (Splunkbase app 7931, GA) runs inside a Splunk
instance and speaks streamable HTTP with encrypted MCP-only tokens. Pairing it
with this workbench in one agent session is the designed next step:

```jsonc
// Example pairing config. The evil-sift-splunk entry matches this repo's
// .mcp.json and works today; add the "splunk" entry only with YOUR Splunk
// instance + MCP token (it is intentionally absent from the committed file).
{
  "mcpServers": {
    "evil-sift-splunk": {
      "command": "python3",
      "args": ["mcp/splunk_ops_mcp_server.py"]
    },
    "splunk": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://<your-splunk-host>:8089/services/mcp",
        "--header", "Authorization: Bearer <your-encrypted-mcp-token>"
      ]
    }
  }
}
```

With both connected, one agent can run `splunk_run_query` → save the JSON →
`triage_splunk_export` → POST `hec_events.jsonl` back, closing the loop in a
single agentic session. Splunk's free 60-day Enterprise trial is sufficient to
exercise this; it is intentionally **not** exercised in this repo, which stays
local, free, and reproducible.

## Honest claim boundary

Safe wording:

- "Splunk-export-ready: consumes real Splunk export shapes with CIM-aligned mapping."
- "HEC-ready: emits `evil_sift:finding` events in the documented HEC envelope."
- "Tested against a local Splunk Enterprise trial in Docker."
- "Designed to pair with the Splunk MCP Server — documented integration path."

Avoid:

- "Integrated with Splunk" / "Integrated with Splunk Cloud."
- "Uses the Splunk MCP Server live."
- "Runs SPL against customer environments."

## Verify everything

```bash
./demo-splunk.sh                      # full Splunk-layer demo + assertions
python3 -m unittest -v tests_splunk   # 37 Splunk-layer tests
./demo.sh                             # core evidence-integrity controls still pass
```

## Submission documents

- [`fit-gap-analysis.md`](fit-gap-analysis.md) — verified hackathon rules vs. this repo
- [`devpost-story.md`](devpost-story.md) — paste-ready project story
- [`devpost-fields.md`](devpost-fields.md) — every Devpost form field
- [`demo-script.md`](demo-script.md) — sub-3-minute video narration and scene plan
- [`submission-checklist.md`](submission-checklist.md) — final pre-submit steps
- [`live-loop-proof.md`](live-loop-proof.md) — live local Splunk trial loop proof
- [`../../architecture_diagram.md`](../../architecture_diagram.md) — required root-level architecture diagram
