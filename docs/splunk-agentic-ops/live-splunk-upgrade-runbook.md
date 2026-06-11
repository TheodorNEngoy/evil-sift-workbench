# Live Splunk Proof Runbook

Status on 2026-06-11: **completed locally**.

What happened on this machine:

- Installed Docker CLI and Colima locally.
- The first `splunk/splunk:latest` container attempt on Apple Silicon failed
  under qemu-style amd64 emulation: `splunkd` started, then disappeared during
  provisioning, and the container exited unhealthy.
- Installing Rosetta and restarting Colima with Rosetta-backed virtualization
  fixed the amd64 runtime issue. The same Splunk image then provisioned cleanly:
  container healthy, Splunk REST answering, HEC token enabled, and KV store
  ready.
- `scripts/splunk_live_loop.py` proved the full localhost-only loop:
  fake events -> HEC ingest -> real Splunk export endpoint -> Evil Sift triage
  -> findings posted back through HEC and searchable as
  `sourcetype=evil_sift:finding`.
- Machine-readable proof: `out/splunk-live/live_loop_proof.json`.
- Human proof: `docs/splunk-agentic-ops/live-loop-proof.md`.

## Why This Matters

The submission package is now stronger than export-ready only: the quick judge
demo remains dependency-free, while the proof artifact shows the same pipeline
working against a local Splunk Enterprise trial.

- Security track fit.
- "How the app interacts with Splunk" architecture claims.
- HEC-ready return-path credibility.

## Safe Claims

Use:

- "Splunk-export-ready"
- "HEC-ready"
- "Tested against a local Splunk Enterprise trial in Docker"
- "Official Splunk MCP Server pairing is a documented integration path"

Do not use:

- "Integrated with Splunk"
- "Uses the Splunk MCP Server live"
- "Connected to Splunk Cloud"
- "Production deployment"

## Option A: Local Docker Path

Prerequisites:

- Free 20-25 GiB disk.
- Install a local container runtime.
- On Apple Silicon, install Rosetta and use Colima's Rosetta support.

Suggested no-cost runtime setup on Apple Silicon:

```bash
softwareupdate --install-rosetta --agree-to-license
brew install docker colima
colima start --cpu 4 --memory 8 --disk 30 --vz-rosetta
docker version
```

Then run Splunk Enterprise trial/free container:

```bash
docker run -d --name evil-sift-splunk \
  --platform linux/amd64 \
  -p 8000:8000 -p 8088:8088 -p 8089:8089 \
  -e SPLUNK_GENERAL_TERMS='--accept-sgt-current-at-splunk-com' \
  -e SPLUNK_START_ARGS='--accept-license' \
  -e SPLUNK_PASSWORD='<local-test-password>' \
  -e SPLUNK_HEC_TOKEN='<local-hec-token>' \
  splunk/splunk:latest
```

Wait for Splunk readiness:

```bash
docker logs -f evil-sift-splunk
```

Run the full local proof loop:

```bash
SPLUNK_PASSWORD='<local-test-password>' \
SPLUNK_HEC_TOKEN='<local-hec-token>' \
python3 scripts/splunk_live_loop.py
```

Expected result:

```text
[splunk-live-loop] HEC accepted 14 fake incident events
[splunk-live-loop] all 14 events searchable in Splunk
[splunk-live-loop] Evil Sift produced the expected 4 findings from the live export
[splunk-live-loop] 4 findings posted back to HEC and searchable as sourcetype=evil_sift:finding
[splunk-live-loop] PASS: full loop proven
```

## Stop Rule

If reproducing this on another machine takes more than 60-90 minutes, submit
the existing quick demo and committed live proof artifacts rather than burning
the deadline.
