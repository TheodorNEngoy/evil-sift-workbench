# Live Local Splunk Loop — Proof

Date: June 11, 2026. Machine-readable trail: `out/splunk-live/live_loop_proof.json`.

The full loop documented by this package was exercised against a **local
Splunk Enterprise trial running in Docker** (`splunk/splunk:latest`,
Splunk 10.4.0, trial license, container name `evil-sift-splunk`). No Splunk
Cloud, no external services, no paid components; all data is the fake sample
data from this repo.

## What ran

```
samples/splunk/incident_search_results.json (14 fake rows)
  → HEC POST /services/collector/event          (accepted: {"text":"Success","code":0})
  → searchable in index main (14/14)
  → POST /services/search/v2/jobs/export        (real export-stream shape)
  → splunk_export_adapter.py                    (normalization)
  → evil_sift_workbench.py                      (deterministic triage)
  → 4 validated findings — identical titles to the native control
  → scripts/findings_to_hec.py → HEC POST       (return trip)
  → searchable as sourcetype=evil_sift:finding  (4/4)
```

Runner: [`scripts/splunk_live_loop.py`](../../scripts/splunk_live_loop.py)
(stdlib only; credentials via `SPLUNK_PASSWORD` / `SPLUNK_HEC_TOKEN` env vars,
never hardcoded). Outputs land in `out/splunk-live/`.

## Reproduction

```bash
# 1. Local Splunk Enterprise trial (you must accept Splunk's terms yourself):
docker run -d --name evil-sift-splunk --platform linux/amd64 \
  -p 8000:8000 -p 8088:8088 -p 8089:8089 \
  -e SPLUNK_GENERAL_TERMS='--accept-sgt-current-at-splunk-com' \
  -e SPLUNK_START_ARGS='--accept-license' \
  -e SPLUNK_PASSWORD='<your-local-test-password>' \
  -e SPLUNK_HEC_TOKEN='<your-local-hec-token>' \
  splunk/splunk:latest
# wait for: docker inspect evil-sift-splunk --format '{{.State.Health.Status}}' == healthy

# 2. Run the loop:
SPLUNK_PASSWORD='<your-local-test-password>' \
SPLUNK_HEC_TOKEN='<your-local-hec-token>' \
python3 scripts/splunk_live_loop.py
```

### Apple Silicon note (this cost us a container crash)

The `splunk/splunk` image is amd64. Under qemu binfmt emulation (Colima/Lima
default when Rosetta is absent) splunkd 10.4 starts and then dies silently —
the container's ansible provisioning fails at "Start Splunk via CLI" after 5
retries and the container exits. Fix: install Rosetta
(`softwareupdate --install-rosetta --agree-to-license`) and run the VM with it
(`colima start --vz-rosetta`). Under Rosetta the same container provisions
cleanly, health goes green, and the KV store reaches `ready`.

### Ingest detail

Events are HEC-ingested with sourcetype `_json` (pretrained, index-time JSON
field extraction) with the original channel kept in `source`. The bare trial
container has no Windows/Sysmon/Zeek add-ons, and their pretrained sourcetype
props suppress JSON field extraction (observed: only 4/14 events matched
field-based search when ingested under those sourcetypes). In a production
Splunk, the add-ons provide that extraction; `_json` is the faithful
equivalent for a bare container. Classification in the adapter keys off
`source` plus `EventCode`/`action` payload fields, so triage results are
unchanged. The export also surfaced a `_time` render
(`2026-06-10 08:04:50.000 GMT`) the adapter now parses (regression-tested).

## Verified claims this proof upgrades

- "Splunk-export-ready" → **demonstrated against a live local Splunk export
  endpoint**, not just against saved fixture files.
- "HEC-ready" → **demonstrated**: findings were accepted by a real HEC and
  are searchable as `sourcetype=evil_sift:finding`.

## Still NOT claimed (unchanged)

- No Splunk Cloud, no production deployment.
- The official **Splunk MCP Server** (Splunkbase 7931) was **not** exercised;
  pairing with it remains a documented integration path.
- The core demo (`./demo-splunk.sh`, 49 unit tests) remains fully local and
  does not require Splunk at all.

Approved wording: "tested against a local Splunk Enterprise trial in Docker."
