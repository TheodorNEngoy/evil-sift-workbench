# FIND EVIL Submission Checklist

Devpost says all eight components are required. This project now has a local artifact for each one.

| Required component | Project artifact | Status |
| --- | --- | --- |
| Code repository, public, MIT or Apache 2.0 | `README.md`, `evil_sift_workbench.py`, `tests.py`, `LICENSE`, <https://github.com/TheodorNEngoy/evil-sift-workbench> | Ready |
| Demo video, 5 minutes max | <https://www.youtube.com/watch?v=5z3JEZb1wKI>, generated from `video/find-evil-demo-narrated.webm` | Ready |
| Architecture diagram | `docs/architecture.svg`, `docs/architecture.md` | Ready |
| Written project description | `docs/devpost-story.md` | Ready to paste into Devpost |
| Dataset documentation | `docs/dataset-documentation.md`, `samples/*.jsonl` | Ready |
| Accuracy report | `docs/accuracy-report.md`, `tests.py`, `out/*/audit_trail.json` | Ready |
| Try-it-out instructions | `README.md`, `docs/claude-code-runbook.md` | Ready; SIFT workstation verification still recommended |
| Agent execution logs | `out/claude-agent/agent_execution_log.md`, `out/claude-agent/mcp_jsonrpc_transcript.jsonl`, `out/agent/agent_execution_log.json` | Ready |

## Final Manual Steps

1. Run `./demo.sh` one last time.
2. Paste the public video link into Devpost: <https://www.youtube.com/watch?v=5z3JEZb1wKI>.
3. Upload `docs/architecture.svg` as the architecture diagram.
4. Paste `docs/devpost-story.md` into the Devpost story fields.
5. Link or mention `docs/dataset-documentation.md`, `docs/accuracy-report.md`, `out/claude-agent/agent_execution_log.md`, `out/claude-agent/mcp_jsonrpc_transcript.jsonl`, and `out/agent/agent_execution_log.json` in the project description.
