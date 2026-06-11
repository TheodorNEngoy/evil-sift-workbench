# Devpost Submission Fields — Splunk Agentic Ops Hackathon

Hackathon: <https://splunk.devpost.com/> · Deadline: June 15, 2026 @ 9:00am PDT

## Project Name

Evil Sift Workbench for Splunk Agentic Ops

## Elevator Pitch (tagline)

Evidence-locked agentic triage for Splunk security data: the agent
orchestrates, a deterministic evidence layer decides — log text is data to
be flagged, never instructions to follow.

## Track

Security

## Repository

```text
https://github.com/TheodorNEngoy/evil-sift-workbench
```

## Demo Video

Upload `video/splunk-agentic-ops-demo.webm` to YouTube (convert to .mp4
first only if YouTube rejects the WebM), confirm
the duration is under 3:00, then paste the public URL here:

```text
https://www.youtube.com/watch?v=OmYQSXujy5Y
```

## Architecture Diagram

Required at repo root: `architecture_diagram.md` (already in place). If the
form also wants an image upload, use `docs/splunk-agentic-ops/architecture.svg`.

## Story / Description

Paste from:

```text
docs/splunk-agentic-ops/devpost-story.md
```

## "How it uses Splunk" — approved wording

> Evil Sift Workbench is **Splunk-export-ready**: it consumes Splunk
> search-result JSON exports in both documented shapes (REST results document
> and export stream) plus the common flat-NDJSON post-processing idiom, with
> CIM-aligned field mapping, and
> the SPL an analyst would run is documented in the repo. Validated findings
> are emitted **HEC-ready** in the documented HTTP Event Collector envelope
> (`sourcetype=evil_sift:finding`) for the return trip into Splunk. The
> workbench exposes its triage as MCP tools, and pairing it with the official
> Splunk MCP Server in a single agent session is the documented **integration
> path**. The full ingest → search/export → triage → HEC loop was **tested
> against a local Splunk Enterprise trial in Docker** (proof committed in the
> repo: `docs/splunk-agentic-ops/live-loop-proof.md`). This submission does
> not claim Splunk Cloud, production deployment, or live Splunk MCP Server
> use.

Never write: "integrated with Splunk", "uses the Splunk MCP Server live",
"connected to Splunk Cloud".

## Built With (Devpost tags)

`python` · `mcp` · `splunk-cim` · `splunk-hec-format` · `claude-code` ·
`security` · `dfir`

## Try-it-out instructions (for judges)

```bash
git clone https://github.com/TheodorNEngoy/evil-sift-workbench
cd evil-sift-workbench
./demo-splunk.sh        # Splunk-export pipeline: 5 PASS lines, ~10 seconds
./demo.sh               # original evidence-integrity controls
python3 -m unittest -v tests tests_splunk   # 49 tests
```

No dependencies beyond Python 3 standard library for the quick judge demo. No external network. All data fake. The optional live proof in `scripts/splunk_live_loop.py` uses only localhost against a local Splunk Enterprise trial container.

## Final pre-submit command

```bash
./demo-splunk.sh
```

Expected:

```text
PASS splunk incident export: 4 validated findings, identical titles/severities/scores to native triage
PASS splunk benign export: zero findings (no false positives)
PASS splunk injection export: verdicts unchanged, manipulation in _raw flagged, report sanitized
PASS HEC-ready findings: evil_sift:finding envelopes generated locally, no network calls
PASS workbench MCP smoke test (evil-sift splunk_ops tools): triage_splunk_export returned a validated packet
```
