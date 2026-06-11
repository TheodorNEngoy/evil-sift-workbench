# Splunk Agentic Ops Hackathon — Fit/Gap Analysis

Verified against <https://splunk.devpost.com/> and <https://splunk.devpost.com/rules>
on June 11, 2026. Deadline: **June 15, 2026 @ 9:00am PDT**.

## What the hackathon requires

| Requirement (verbatim or paraphrased from rules) | Status for this repo |
| --- | --- |
| Public code repository with all source, assets, run instructions, and an open source license file | **Ready locally — push pending.** MIT license, stdlib-only Python; the repo at github.com/TheodorNEngoy/evil-sift-workbench is public, but the Splunk layer is not pushed yet (manual step 1 in the checklist) |
| Clear README with setup/run instructions, dependencies, example configs or datasets | **Fit.** Root `README.md` + `docs/splunk-agentic-ops/README.md`; fake datasets in `samples/` and `samples/splunk/` |
| Architecture diagram **at the repo root**, named `architecture_diagram.(md\|pdf\|png)`, showing how the app interacts with Splunk, how AI models/agents are integrated, and data flow | **Ready locally — push pending.** `architecture_diagram.md` added at the repo root and includes the agent/MCP client layer, Splunk data flow, and trust boundaries |
| Demo video **under 3 minutes**, publicly posted on YouTube/Vimeo/Youku, showing the project working and how AI is used | **Ready locally — upload pending.** A Splunk-specific 153.3s video is generated locally by `scripts/make_splunk_demo_video.js`; uploading it publicly is a manual step |
| Text description identifying one of three tracks (Observability, Security, Platform & Developer Experience) | **Fit.** Track: **Security**. Paste-ready text in `devpost-fields.md` |
| Project must be new, or significantly updated after May 18, 2026 (Submission Period start) | **Fit.** The entire repo history is June 10–11, 2026, and the Splunk layer (adapter, MCP tools, HEC output, tests, docs) is new work |
| Teams of up to 2 individuals | Fit (solo entry) |

## What "using Splunk" means under the rules — the honest gap

The rules say the project "should leverage one or more of Splunk's latest AI
capabilities"; the hackathon overview page enumerates them as "AI agents for
Splunk apps, **Splunk MCP Server**, Splunk hosted models, AI Assistant, and
AI-powered app development tools". No rule explicitly mandates a live Splunk Enterprise/Cloud
instance, but consuming Splunk-*format* data alone is not on that list.

**What this repo truthfully is today:**

- **Splunk-export-ready, live-tested** — it consumes real Splunk export shapes
  (REST `results` documents, `/jobs/export` streams, flat NDJSON) with
  CIM-aligned field mapping, verified against Splunk's documented formats and
  **tested end-to-end against a local Splunk Enterprise trial in Docker**
  (`live-loop-proof.md`: HEC ingest → real export endpoint → identical 4
  findings → findings searchable back in Splunk).
- **HEC-ready on the return path, live-tested** — findings are emitted as
  `evil_sift:finding` events in the documented HTTP Event Collector envelope;
  a real local HEC accepted them and they are searchable in Splunk.
- **Splunk MCP integration path** — the workbench exposes its triage as MCP
  tools (`mcp/splunk_ops_mcp_server.py`), designed to sit alongside the
  official Splunk MCP Server (Splunkbase app 7931, streamable HTTP, GA) in one
  agent loop: the agent runs `splunk_run_query` there and
  `triage_splunk_export` here. This pairing is documented, not demonstrated.

**What it is not (and must not claim):** connected to Splunk Cloud or any
production Splunk, or a live user of the Splunk MCP Server / AI Assistant /
hosted models. The live test used a local Docker trial container only.

**Risk assessment:** judges could read the "leverage Splunk AI capabilities"
guidance strictly. The live local-trial proof closes most of the data-plane
gap (real HEC, real search/export pipeline); the remaining gap is that no
listed Splunk AI capability (MCP Server, AI Assistant, hosted models) is
exercised live. The description and video say "tested against a local Splunk
Enterprise trial in Docker" and "integration path" explicitly.

**Remaining optional close (needs owner approval, $0):** the local Splunk
Enterprise trial container is already running (`evil-sift-splunk`). Installing
the Splunk MCP Server app (Splunkbase 7931) on it, generating an encrypted MCP
token, and recording one real `splunk_run_query → triage_splunk_export → HEC`
loop would convert the MCP "integration path" into "demonstrated integration"
and make the **Best Use of Splunk MCP Server** $1,000 bonus credible. Note:
downloading a Splunkbase app requires a free splunk.com account login —
owner decision. The app needs token auth, which the trial license supports.

## Judging criteria mapping (four equally weighted criteria)

| Criterion | Position |
| --- | --- |
| Technological Implementation | Strong: deterministic evidence-validated core, 49 unit tests (12 core + 37 Splunk layer), reproducible one-command demos, MCP tool surface, injection-resistance controls |
| Design | Moderate: CLI + markdown reports, no GUI. Mitigated by a clear architecture diagram, polished video, and well-structured analyst reports |
| Potential Impact | Strong story: SOC triage is drowning in alerts; agentic triage with an anti-hallucination evidence layer addresses the trust problem that blocks agentic-SOC adoption |
| Quality of the Idea | Strong: "the agent orchestrates, the evidence layer decides" is a distinctive answer to hostile-telemetry prompt injection and LLM fabrication in security operations |

## Prize targets (realistic)

- Primary: **Best of Security** track ($3,000 + .conf26 pass).
- Secondary: Grand Prize ($7,000) — possible but competitive.
- **Best Use of Splunk MCP Server** ($1,000 bonus): only credible if the
  optional live-trial step above is taken; do not claim it from the
  export-only package.
- A project can win at most one grand/track prize plus one bonus prize.
