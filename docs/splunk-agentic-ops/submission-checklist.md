# Splunk Agentic Ops Submission Checklist

Official Rules verified June 11, 2026 at <https://splunk.devpost.com/rules>.
Deadline: **June 15, 2026 @ 9:00am PDT**.

## Required components

| Requirement | Artifact | Status |
| --- | --- | --- |
| Public repo, all source + instructions, open source license file | <https://github.com/TheodorNEngoy/evil-sift-workbench>, MIT `LICENSE` | Ready (push latest) |
| README with setup/run instructions, dependencies, example datasets | Root `README.md` (Splunk section) + `docs/splunk-agentic-ops/README.md` + `samples/splunk/` | Ready |
| Architecture diagram at repo root named `architecture_diagram.(md\|pdf\|png)` showing Splunk interaction, AI/agent integration, data flow | `architecture_diagram.md` (root) | Ready |
| Demo video < 3 minutes, publicly visible on YouTube/Vimeo/Youku, shows project working + how AI is used, no unlicensed third-party marks/music/material | `video/splunk-agentic-ops-demo.webm` → https://www.youtube.com/watch?v=OmYQSXujy5Y | Uploaded Public |
| Text description identifying a track | `docs/splunk-agentic-ops/devpost-story.md` (Track: Security) | Ready to paste |

## Eligibility checks

- [x] Project significantly updated after May 18, 2026 (entire repo is June 10–11, 2026; the Splunk layer is new work).
- [x] Open source license file present (MIT).
- [x] Solo entry (rules allow teams of up to 2).
- [ ] Confirm Devpost registration for the Splunk Agentic Ops Hackathon.

## Live local proof (done June 11, 2026)

The ingest → export → triage → HEC loop ran against a local Splunk Enterprise
trial in Docker: see `docs/splunk-agentic-ops/live-loop-proof.md` and
`out/splunk-live/live_loop_proof.json`. Commit `scripts/splunk_live_loop.py`,
the proof doc, and `out/splunk-live/` with the Splunk layer.

## Final pre-submit commands

```bash
./demo-splunk.sh        # all 5 PASS lines
./demo.sh               # core evidence-integrity package still fully green
python3 -m unittest -q tests tests_splunk
```

## Manual steps (owner only)

1. Commit and push the Splunk layer to the public repo, then re-verify with a fresh clone + `./demo-splunk.sh`. Superseded draft files were deleted; `architecture_diagram.md` is the required root architecture artifact.
2. Generate/refresh the video: `node scripts/make_splunk_demo_video.js`; confirm duration is under 3:00.
3. YouTube video uploaded Public: https://www.youtube.com/watch?v=OmYQSXujy5Y. Paste this URL into Devpost.
4. Paste `docs/splunk-agentic-ops/devpost-story.md` into the Devpost story; select the Security track.
5. Fill remaining fields from `docs/splunk-agentic-ops/devpost-fields.md`.
6. Use the approved local-proof wording in `devpost-fields.md`: tested against a local Splunk Enterprise trial in Docker. Do NOT claim Splunk Cloud, production deployment, or live use of the official Splunk MCP Server.
7. Confirm the final video visibly shows the agent/MCP tool role, contains no background music, and uses no unlicensed third-party footage, trademarks, or copyrighted material.

## Optional EV-raising step (owner decision; ~$0, a few hours)

Free 60-day Splunk Enterprise trial + Splunk MCP Server app (Splunkbase 7931)
+ encrypted MCP token → record one real `splunk_run_query` →
`triage_splunk_export` → HEC POST loop. Converts "integration path" into
"demonstrated integration" and makes the Best Use of Splunk MCP Server $1,000
bonus credible. Requires account signup — not done in this packaging pass.
