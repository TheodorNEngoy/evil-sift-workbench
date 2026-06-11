# Architecture Diagram — Evil Sift Workbench for Splunk Agentic Ops

Pattern: **agent orchestrates, deterministic evidence layer decides.** An
MCP-capable agent (Claude Code or any MCP client) drives the investigation
through typed MCP tools; verdicts are computed by deterministic, tested code
that validates every cited piece of evidence.

Splunk interaction boundary, stated precisely: this build consumes **Splunk
search-result JSON exports** (Splunk-export-ready), emits **HEC-ready**
findings, and includes a local live-Splunk proof loop; the live pairing with
the official Splunk MCP Server is a documented integration path, not a
demonstrated connection.

![Architecture](docs/splunk-agentic-ops/architecture.svg)

```mermaid
flowchart LR
    subgraph SPLUNK["Splunk environment (local trial or yours)"]
        SPL["SPL searches\nsamples/splunk/searches.spl"]
        HEC["HTTP Event Collector\n/services/collector"]
        SMCP["Splunk MCP Server\n(Splunkbase 7931, streamable HTTP)"]
    end

    subgraph AGENT["Agent layer (AI)"]
        A["MCP-capable agent\nClaude Code / any MCP client\nplans, calls tools, self-corrects"]
    end

    subgraph WORKBENCH["Evil Sift Workbench (this repo, local, stdlib-only)"]
        T1["MCP tools\nconvert_splunk_export / triage_splunk_export\nmcp/splunk_ops_mcp_server.py"]
        AD["Splunk export adapter\n3 export shapes, CIM-aligned mapping\nsplunk_export_adapter.py"]
        CORE["Deterministic triage core\nstrict ingest -> chain detectors ->\nevidence validator -> sanitized render\nevil_sift_workbench.py"]
        OUT["Artifacts: report.md, findings.json,\ndetections.yml, audit_trail.json,\nexecution_log.json"]
        HECOUT["HEC-ready findings\nhec_events.jsonl (evil_sift:finding)\nscripts/findings_to_hec.py"]
    end

    SPL -- "JSON export (file)" --> AD
    A -- "MCP (stdio JSON-RPC)" --> T1
    T1 --> AD --> CORE --> OUT
    CORE --> HECOUT
    HECOUT -. "documented return path: POST" .-> HEC
    A -. "documented integration path:\nsplunk_run_query via mcp-remote" .-> SMCP
```

## Data flow

1. **Splunk → workbench (file boundary).** An analyst runs the documented SPL
   in their own Splunk and exports results as JSON (REST `results` document,
   `/jobs/export` stream, or flat NDJSON). Fake stand-ins ship in
   `samples/splunk/`.
2. **Agent → tools (MCP boundary).** The agent calls `triage_splunk_export`;
   it never computes verdicts itself. Tool responses include validation notes
   the agent must act on (self-correction).
3. **Adapter → core.** CIM-aligned normalization preserves Splunk provenance
   (`index`, `sourcetype`, `source`, truncated `_raw`) so manipulation
   content embedded in raw log text still reaches the detectors.
4. **Core → artifacts.** Deterministic detectors find behavior chains; the
   evidence validator drops any finding citing nonexistent evidence; the
   renderer sanitizes all log-derived text. Output includes a hashed audit
   trail and execution log.
5. **Workbench → Splunk (documented return/integration paths, dashed).**
   `hec_events.jsonl` is ready to POST to a HEC endpoint; pairing the agent
   with the official Splunk MCP Server would close the loop in one session.

## Trust boundaries

| Boundary | Enforcement |
| --- | --- |
| Agent vs. verdicts | The agent orchestrates via MCP tools; verdicts come only from deterministic detectors in `evil_sift_workbench.py` |
| Telemetry vs. instructions | Log/`_raw` content is data; instruction-like content is itself flagged as a Defense Evasion finding |
| Evidence integrity | `validate_findings()` drops any finding whose evidence IDs are absent from the input |
| Rendering | `sanitize_for_markdown()` neutralizes backticks/control chars before any log text enters a report |
| Network | The quick judge demo makes no external network calls; optional live proof uses localhost-only Splunk HEC/REST |
