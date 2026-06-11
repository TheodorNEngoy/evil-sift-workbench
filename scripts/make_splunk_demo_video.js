#!/usr/bin/env node
// Generates the sub-3-minute Splunk Agentic Ops demo video locally:
// canvas-rendered scenes + macOS `say` narration, recorded in local Chrome.
// No paid services; refreshes ./demo-splunk.sh artifacts first.

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const VIDEO_DIR = path.join(ROOT, "video");
const NARRATION_TXT = path.join(VIDEO_DIR, "splunk-narration.txt");
const NARRATION_AIFF = path.join(VIDEO_DIR, "splunk-narration.aiff");
const NARRATION_M4A = path.join(VIDEO_DIR, "splunk-narration.m4a");
const WEBM_OUT = path.join(VIDEO_DIR, "splunk-agentic-ops-demo.webm");
const MP4_OUT = path.join(VIDEO_DIR, "splunk-agentic-ops-demo.mp4");
const DEMO_OUTPUT = path.join(VIDEO_DIR, "splunk-demo-output.txt");
const LOCAL_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function run(cmd, args, options = {}) {
  return execFileSync(cmd, args, {
    cwd: ROOT,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });
}

function runInherited(cmd, args, options = {}) {
  execFileSync(cmd, args, {
    cwd: ROOT,
    stdio: "inherit",
    ...options,
  });
}

function findLines(lines, patterns, context = 0) {
  const indexes = [];
  for (const pattern of patterns) {
    const idx = lines.findIndex((line) => line.toLowerCase().includes(pattern.toLowerCase()));
    if (idx >= 0) indexes.push(idx);
  }
  const selected = new Set();
  for (const idx of indexes) {
    for (let i = Math.max(0, idx - context); i <= Math.min(lines.length - 1, idx + context); i += 1) {
      selected.add(i);
    }
  }
  return [...selected].sort((a, b) => a - b).map((idx) => lines[idx]);
}

function trimLines(lines, maxLines) {
  if (lines.length <= maxLines) return lines;
  return [...lines.slice(0, maxLines - 1), "..."];
}

function buildHtml(data, audioDataUri) {
  const payload = JSON.stringify(data).replace(/</g, "\\u003c");
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Splunk Agentic Ops Demo Recorder</title>
  <style>
    html, body { margin: 0; padding: 0; width: 100%; height: 100%; background: #0c1220; }
    canvas { display: block; width: 1280px; height: 720px; }
  </style>
</head>
<body>
  <canvas id="stage" width="1280" height="720"></canvas>
  <script>
    const DATA = ${payload};
    const AUDIO_DATA_URI = "${audioDataUri}";
    const canvas = document.getElementById("stage");
    const ctx = canvas.getContext("2d");
    let recordingDuration = 160;

    const COLORS = {
      bg: "#0c1220",
      panel: "#111a2e",
      panel2: "#16233b",
      ink: "#eef4ff",
      muted: "#9fb0c8",
      accent: "#51d1a7",
      amber: "#f5c542",
      red: "#ff6b6b",
      blue: "#77b7ff",
      border: "#30405f",
      code: "#07111f"
    };

    function roundRect(x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    function fillRound(x, y, w, h, r, fill, stroke) {
      roundRect(x, y, w, h, r);
      ctx.fillStyle = fill;
      ctx.fill();
      if (stroke) {
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    function text(value, x, y, size, color = COLORS.ink, weight = "400", font = "Inter, Arial, sans-serif") {
      ctx.font = weight + " " + size + "px " + font;
      ctx.fillStyle = color;
      ctx.fillText(value, x, y);
    }

    function wrap(value, x, y, maxWidth, lineHeight, size, color = COLORS.ink, weight = "400") {
      ctx.font = weight + " " + size + "px Inter, Arial, sans-serif";
      const words = String(value).split(/\\s+/);
      let line = "";
      let yy = y;
      for (const word of words) {
        const next = line ? line + " " + word : word;
        if (ctx.measureText(next).width > maxWidth && line) {
          ctx.fillStyle = color;
          ctx.fillText(line, x, yy);
          line = word;
          yy += lineHeight;
        } else {
          line = next;
        }
      }
      if (line) {
        ctx.fillStyle = color;
        ctx.fillText(line, x, yy);
      }
      return yy + lineHeight;
    }

    function drawHeader(title, subtitle) {
      text("Evil Sift Workbench", 54, 58, 28, COLORS.ink, "800");
      text("for Splunk Agentic Ops", 54, 88, 16, COLORS.muted, "500");
      fillRound(902, 38, 318, 42, 21, "#10291f", "#28684f");
      text("all data fake - local only - no cloud", 926, 65, 15, COLORS.accent, "800");
      text(title, 54, 138, 38, COLORS.ink, "800");
      wrap(subtitle, 56, 171, 920, 25, 18, COLORS.muted, "500");
    }

    function terminal(lines, x, y, w, h, reveal, title = "terminal") {
      fillRound(x, y, w, h, 10, COLORS.code, COLORS.border);
      ctx.fillStyle = "#ff5f56"; ctx.beginPath(); ctx.arc(x + 24, y + 24, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#ffbd2e"; ctx.beginPath(); ctx.arc(x + 44, y + 24, 6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#27c93f"; ctx.beginPath(); ctx.arc(x + 64, y + 24, 6, 0, Math.PI * 2); ctx.fill();
      text(title, x + 88, y + 30, 14, COLORS.muted, "700", "Menlo, Consolas, monospace");
      const shown = lines.slice(0, Math.max(1, Math.floor(reveal)));
      ctx.font = "15px Menlo, Consolas, monospace";
      let yy = y + 60;
      for (const line of shown.slice(-17)) {
        const color = line.includes("PASS") || line.includes("OK")
          ? COLORS.accent
          : line.includes("Critical")
            ? COLORS.red
            : line.includes("High")
              ? COLORS.amber
              : COLORS.ink;
        ctx.fillStyle = color;
        ctx.fillText(String(line).slice(0, 104), x + 24, yy);
        yy += 23;
      }
    }

    function card(title, body, x, y, w, h, accent = COLORS.blue) {
      fillRound(x, y, w, h, 10, COLORS.panel, COLORS.border);
      ctx.fillStyle = accent;
      ctx.fillRect(x, y, 6, h);
      text(title, x + 22, y + 34, 18, COLORS.ink, "800");
      wrap(body, x + 22, y + 68, w - 44, 22, 15, COLORS.muted, "500");
    }

    function caption(value) {
      fillRound(80, 626, 1120, 58, 12, "rgba(7, 17, 31, 0.88)", "#2b3b59");
      wrap(value, 108, 658, 1066, 25, 18, COLORS.ink, "700");
    }

    function sceneFor(p) {
      if (p < 0.14) return 0;
      if (p < 0.37) return 1;
      if (p < 0.56) return 2;
      if (p < 0.73) return 3;
      if (p < 0.90) return 4;
      return 5;
    }

    function drawPipeline() {
      const steps = [
        ["SPL export", "your Splunk, 3 shapes"],
        ["Adapter", "CIM-aligned mapping"],
        ["Detect", "deterministic chains"],
        ["Validate", "evidence required"],
        ["HEC-ready", "back toward Splunk"]
      ];
      let x = 76;
      for (let i = 0; i < steps.length; i += 1) {
        fillRound(x, 322, 190, 96, 10, i === 3 ? "#103428" : COLORS.panel2, i === 3 ? "#3bbb8a" : COLORS.border);
        text(steps[i][0], x + 18, 358, 20, COLORS.ink, "800");
        text(steps[i][1], x + 18, 386, 13, COLORS.muted, "600");
        if (i < steps.length - 1) {
          text("->", x + 200, 377, 28, COLORS.accent, "800", "Menlo, Consolas, monospace");
        }
        x += 238;
      }
      card("Agent on top, evidence below", "An MCP-capable agent orchestrates the tools; verdicts come only from the deterministic evidence layer.", 120, 462, 500, 104, COLORS.blue);
      card("Trust boundary", "Splunk-ingested logs are attacker-influenced text. Here, log content is data - not an instruction to follow.", 660, 462, 500, 104, COLORS.accent);
    }

    function drawHecPanel() {
      fillRound(62, 230, 600, 330, 10, COLORS.panel, COLORS.border);
      text("out/splunk/incident/hec_events.jsonl", 88, 266, 17, COLORS.ink, "800", "Menlo, Consolas, monospace");
      ctx.font = "14px Menlo, Consolas, monospace";
      let yy = 298;
      for (const line of DATA.hecExcerpt.slice(0, 11)) {
        ctx.fillStyle = line.includes("sourcetype") || line.includes("evil_sift:finding") ? COLORS.accent : line.includes("severity") || line.includes("score") ? COLORS.amber : COLORS.ink;
        ctx.fillText(String(line).slice(0, 70), 88, yy);
        yy += 23;
      }
      card("Live-tested return path", "These envelopes were POSTed to a local Splunk Enterprise trial HEC, then: sourcetype=evil_sift:finding | sort - score", 700, 250, 470, 130, COLORS.amber);
      card("Splunk MCP pairing (documented path)", "Official Splunk MCP Server + this workbench in one agent session: splunk_run_query there, triage_splunk_export here, HEC back.", 700, 410, 470, 150, COLORS.blue);
    }

    let renderTime = 0;

    function drawFrame() {
      const duration = recordingDuration;
      const t = renderTime || 0;
      const p = Math.min(0.999, t / Math.max(1, duration));
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, 1280, 720);
      const scene = sceneFor(p);

      if (scene === 0) {
        drawHeader("Agentic ops with an evidence boundary", "The agent orchestrates the investigation; a deterministic evidence layer owns every verdict.");
        drawPipeline();
        caption("Splunk-export-ready in, HEC-ready out - full loop tested against a local Splunk Enterprise trial.");
      } else if (scene === 1) {
        drawHeader("Splunk export shapes in", "REST results document, export stream, plus flat NDJSON - normalized with CIM-aligned field mapping.");
        const reveal = 2 + ((p - 0.14) / 0.23) * DATA.demoLines.length;
        terminal(DATA.demoLines, 60, 220, 1160, 360, reveal, "$ ./demo-splunk.sh");
        caption("One command converts the export, runs triage, and asserts every expected behavior.");
      } else if (scene === 2) {
        drawHeader("Four validated findings - zero drift", "The Splunk-export path produces identical titles, severities, and scores to the native control.");
        terminal(DATA.findingLines, 60, 230, 720, 330, 8, "incident findings");
        card("Evidence or it doesn't exist", "Every finding cites concrete evidence IDs. Findings citing missing evidence are dropped before the report.", 820, 250, 380, 140, COLORS.accent);
        card("Benign control: 0 findings", "No false-positive theater. Input SHA-256: " + DATA.auditHash.slice(0, 20) + "...", 820, 410, 380, 130, COLORS.blue);
        caption("Validated chain: password spray, login, encoded PowerShell, lateral movement, callback.");
      } else if (scene === 3) {
        drawHeader("Hostile telemetry is treated as data", "This export hides 'do not flag' and 'ignore previous instructions' inside _raw.");
        terminal(DATA.injectionLines, 60, 230, 1160, 200, 8, "injection control");
        card("Verdicts unchanged", "The attack chain is still reported at full severity.", 120, 470, 500, 96, COLORS.accent);
        card("Manipulation flagged", "Instruction-like log content becomes its own Defense Evasion finding.", 660, 470, 500, 96, COLORS.red);
        caption("Log content is flagged as data, not followed as instruction - and reports are sanitized on render.");
      } else if (scene === 4) {
        drawHeader("HEC-ready findings + the MCP pairing path", "Findings return toward Splunk in the documented collector envelope.");
        drawHecPanel();
        caption("Proven live: findings posted to a local trial HEC and searchable as sourcetype=evil_sift:finding.");
      } else {
        drawHeader("Reproducible, truthful, ready to judge", "MIT-licensed, stdlib-only Python. Every claim reproduces with one command.");
        card("Open source repo", "github.com/TheodorNEngoy/evil-sift-workbench - README, root architecture_diagram.md, fake datasets.", 80, 238, 520, 110, COLORS.accent);
        card("49 unit tests", "12 core + 37 Splunk-layer tests: export shapes, CIM mapping, parity, injection resistance, HEC envelopes.", 680, 238, 520, 110, COLORS.blue);
        card("Honest claim boundary", "Loop tested against a local Splunk Enterprise trial in Docker; official Splunk MCP Server pairing stays a documented path. No cloud claims.", 80, 388, 520, 110, COLORS.amber);
        card("Track: Security", "Agentic triage your SOC can trust: the agent investigates, the evidence layer decides.", 680, 388, 520, 110, COLORS.red);
        caption("./demo-splunk.sh - five PASS lines in seconds. Thanks for watching.");
      }
    }

    window.startRecording = async function startRecording() {
      const audioContext = new AudioContext();
      const audioResponse = await fetch(AUDIO_DATA_URI);
      const audioBytes = await audioResponse.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(audioBytes.slice(0));
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      const destination = audioContext.createMediaStreamDestination();
      source.connect(destination);

      const canvasStream = canvas.captureStream(30);
      const stream = new MediaStream([
        ...canvasStream.getVideoTracks(),
        ...destination.stream.getAudioTracks()
      ]);

      const mimeCandidates = [
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8,opus",
        "video/webm"
      ];
      const mimeType = mimeCandidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || "";
      const chunks = [];
      const recorder = new MediaRecorder(stream, {
        mimeType,
        videoBitsPerSecond: 3500000,
        audioBitsPerSecond: 128000
      });
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunks.push(event.data);
      };
      const stopped = new Promise((resolve) => {
        recorder.onstop = resolve;
      });
      recorder.start(1000);
      await audioContext.resume();
      const duration = audioBuffer.duration + 0.8;
      recordingDuration = duration;
      const started = performance.now();
      let animating = true;
      function animate() {
        renderTime = Math.min(duration, (performance.now() - started) / 1000);
        drawFrame();
        if (animating) requestAnimationFrame(animate);
      }
      animate();
      source.start();
      await new Promise((resolve) => setTimeout(resolve, Math.ceil((duration + 0.8) * 1000)));
      animating = false;
      try {
        source.stop();
      } catch (error) {}
      recorder.stop();
      await stopped;

      const blob = new Blob(chunks, { type: mimeType || "video/webm" });
      const reader = new FileReader();
      const dataUrl = await new Promise((resolve) => {
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(blob);
      });
      const dataUrlText = String(dataUrl);
      const base64Marker = "base64,";
      const markerIndex = dataUrlText.indexOf(base64Marker);
      if (markerIndex < 0) {
        throw new Error("recording data URL did not contain base64 payload");
      }
      const outputPath = await window.saveRecording(dataUrlText.slice(markerIndex + base64Marker.length), mimeType || "video/webm");
      return { bytes: blob.size, duration, audioDuration: audioBuffer.duration, mimeType, outputPath };
    };
  </script>
</body>
</html>`;
}

async function main() {
  fs.mkdirSync(VIDEO_DIR, { recursive: true });

  console.log("[video] refreshing Splunk demo artifacts");
  const demoOutput = run("/bin/bash", ["-lc", "./demo-splunk.sh"], { maxBuffer: 1024 * 1024 * 10 });
  fs.writeFileSync(DEMO_OUTPUT, demoOutput, "utf8");

  console.log("[video] generating narration audio");
  runInherited("/usr/bin/say", ["-o", NARRATION_AIFF, "-f", NARRATION_TXT]);
  runInherited("/usr/bin/afconvert", ["-f", "m4af", "-d", "aac", NARRATION_AIFF, NARRATION_M4A]);

  const demoLines = demoOutput.trim().split(/\r?\n/).filter(Boolean);
  const findings = JSON.parse(fs.readFileSync(path.join(ROOT, "out/splunk/incident/findings.json"), "utf8"));
  const audit = JSON.parse(fs.readFileSync(path.join(ROOT, "out/splunk/incident/audit_trail.json"), "utf8"));
  const hecFirst = JSON.parse(
    fs.readFileSync(path.join(ROOT, "out/splunk/incident/hec_events.jsonl"), "utf8").split(/\r?\n/)[0]
  );
  const hecExcerpt = [
    "{",
    '  "time": ' + hecFirst.time + ",",
    '  "host": "' + hecFirst.host + '",',
    '  "source": "' + hecFirst.source + '",',
    '  "sourcetype": "' + hecFirst.sourcetype + '",',
    '  "event": {',
    '    "title": "' + String(hecFirst.event.title).slice(0, 44) + '...",',
    '    "severity": "' + hecFirst.event.severity + '", "score": ' + hecFirst.event.score + ",",
    '    "evidence_ids": [' + hecFirst.event.evidence_ids.map((id) => '"' + id + '"').join(", ") + "],",
    '    "input_sha256": "' + String(hecFirst.event.input_sha256).slice(0, 18) + '..." } }',
  ];
  const data = {
    demoLines: trimLines(
      demoLines.filter((line) => line.includes("[1/6]") || line.includes("[2/6]") || line.includes("[3/6]") || line.includes("splunk-adapter") || line.includes("evil-sift") || line.includes(" - [") || line.includes("findings-to-hec") || line.includes("clean:")),
      24
    ),
    findingLines: findings.map(
      (f) => "[" + f.severity + "/" + f.confidence + " conf, score " + f.score + "] " + f.title
    ),
    injectionLines: findLines(demoLines, ["injection export", "manipulation content", "verdicts unchanged"], 1),
    hecExcerpt,
    auditHash: audit.input_sha256,
  };
  const audioDataUri = `data:audio/mp4;base64,${fs.readFileSync(NARRATION_M4A).toString("base64")}`;
  const html = buildHtml(data, audioDataUri);

  console.log("[video] rendering narrated video in Chromium");
  const launchOptions = {
    headless: true,
    args: [
      "--autoplay-policy=no-user-gesture-required",
      "--mute-audio=false",
      "--allow-file-access-from-files",
    ],
  };
  if (fs.existsSync(LOCAL_CHROME)) {
    launchOptions.executablePath = LOCAL_CHROME;
  }
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.exposeFunction("saveRecording", async (base64, mimeType) => {
    const outputPath = String(mimeType).startsWith("video/mp4") ? MP4_OUT : WEBM_OUT;
    fs.writeFileSync(outputPath, Buffer.from(base64, "base64"));
    return outputPath;
  });
  await page.setContent(html, { waitUntil: "load" });
  const result = await page.evaluate(() => window.startRecording());
  await browser.close();
  console.log(
    `[video] wrote ${result.outputPath} (${result.bytes} bytes, ${result.duration.toFixed(1)}s, ` +
      `audio ${result.audioDuration.toFixed(1)}s, ${result.mimeType})`
  );
  if (result.duration >= 178) {
    throw new Error(`video duration ${result.duration.toFixed(1)}s is too close to the 3-minute limit; shorten the narration`);
  }

  try {
    console.log("[video] trying mp4 conversion with avconvert");
    runInherited("/usr/bin/avconvert", ["--source", WEBM_OUT, "--preset", "Preset1280x720", "--output", MP4_OUT, "--replace"]);
    console.log(`[video] wrote ${MP4_OUT}`);
  } catch (error) {
    if (fs.existsSync(MP4_OUT) && fs.statSync(MP4_OUT).size < 1024 * 1024) {
      fs.rmSync(MP4_OUT);
    }
    console.log("[video] mp4 conversion unavailable for this WebM source; keeping narrated WebM.");
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
