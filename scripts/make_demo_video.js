#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const VIDEO_DIR = path.join(ROOT, "video");
const NARRATION_TXT = path.join(VIDEO_DIR, "narration.txt");
const NARRATION_AIFF = path.join(VIDEO_DIR, "narration.aiff");
const NARRATION_M4A = path.join(VIDEO_DIR, "narration.m4a");
const WEBM_OUT = path.join(VIDEO_DIR, "find-evil-demo-narrated.webm");
const MP4_OUT = path.join(VIDEO_DIR, "find-evil-demo-narrated.mp4");
const DEMO_OUTPUT = path.join(VIDEO_DIR, "demo-output.txt");
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
  <title>Evil Sift Demo Recorder</title>
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
    let recordingDuration = 90;

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
      text("FIND EVIL submission demo", 54, 88, 16, COLORS.muted, "500");
      fillRound(992, 38, 228, 42, 21, "#10291f", "#28684f");
      text("local fake data only", 1023, 66, 15, COLORS.accent, "800");
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
        const color = line.includes("PASS") || line.includes("OK") || line.includes("SELF-CORRECTION PASS")
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
      if (p < 0.15) return 0;
      if (p < 0.36) return 1;
      if (p < 0.50) return 2;
      if (p < 0.64) return 3;
      if (p < 0.80) return 4;
      return 5;
    }

    function drawArchitecture() {
      const steps = [
        ["JSONL", "fake local events"],
        ["Ingest", "strict parser"],
        ["Detect", "deterministic chains"],
        ["Validate", "evidence required"],
        ["Render", "sanitized artifacts"]
      ];
      let x = 76;
      for (let i = 0; i < steps.length; i += 1) {
        fillRound(x, 322, 190, 96, 10, i === 3 ? "#103428" : COLORS.panel2, i === 3 ? "#3bbb8a" : COLORS.border);
        text(steps[i][0], x + 22, 358, 21, COLORS.ink, "800");
        text(steps[i][1], x + 22, 386, 14, COLORS.muted, "600");
        if (i < steps.length - 1) {
          text("->", x + 204, 377, 28, COLORS.accent, "800", "Menlo, Consolas, monospace");
        }
        x += 238;
      }
      card("Trust boundary", "Log content is data, never an instruction. The injection sample tries to steer the tool and fails.", 120, 462, 500, 104, COLORS.accent);
      card("Judge artifact", "Every run emits report.md, findings.json, detections.yml, audit_trail.json, and execution_log.json.", 660, 462, 500, 104, COLORS.amber);
    }

    function drawReportPanel() {
      fillRound(62, 230, 560, 330, 10, COLORS.panel, COLORS.border);
      text("out/incident/report.md", 88, 266, 19, COLORS.ink, "800", "Menlo, Consolas, monospace");
      const lines = DATA.reportExcerpt;
      ctx.font = "15px Menlo, Consolas, monospace";
      let yy = 302;
      for (const line of lines.slice(0, 10)) {
        ctx.fillStyle = line.includes("Risk score") ? COLORS.amber : line.includes("decoded_command_preview") ? COLORS.accent : COLORS.ink;
        ctx.fillText(String(line).slice(0, 72), 88, yy);
        yy += 24;
      }
      card("Evidence integrity", "Evidence IDs, source lines, and score basis are visible in the human report. Encoded PowerShell is decoded only as a safe preview.", 676, 250, 470, 130, COLORS.accent);
      card("Reproducible packet", "audit_trail.json records the input hash and evidence map. execution_log.json records deterministic tool steps for the agent.", 676, 410, 470, 130, COLORS.blue);
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
        drawHeader("Custom MCP Server for autonomous triage", "Claude Code or OpenClaw can orchestrate the triage_jsonl tool while deterministic guardrails enforce evidence integrity.");
        drawArchitecture();
        caption("The agent decides what to investigate; the evidence layer decides what can be claimed.");
      } else if (scene === 1) {
        drawHeader("One command runs the whole packet", "./demo.sh regenerates the outputs, runs tests, and asserts the expected behavior.");
        const local = DATA.demoLines.filter((line) => !line.includes("SELF-CORRECTION") && !line.includes("Ran 12"));
        const reveal = 2 + ((p - 0.15) / 0.21) * local.length;
        terminal(local, 60, 220, 1160, 360, reveal, "$ ./demo.sh");
        caption("The incident control produces four ranked findings from fake local data.");
      } else if (scene === 2) {
        drawHeader("Self-correction: no evidence, no finding", "A fabricated finding is injected into validation and dropped before it can reach the report.");
        terminal(DATA.selfCorrectionLines, 80, 250, 1120, 214, 5, "self-correction guard");
        card("Why judges care", "This is the anti-hallucination contract: a claim cannot survive unless every cited evidence ID exists in the input.", 186, 500, 908, 92, COLORS.accent);
        caption("The self-correction guard rejects fabricated evidence before report rendering.");
      } else if (scene === 3) {
        drawHeader("Report-grade evidence, not just labels", "The analyst report shows score basis, source lines, evidence snippets, and decoded preview text.");
        drawReportPanel();
        caption("Every finding is traceable to concrete local evidence.");
      } else if (scene === 4) {
        drawHeader("Benign and injection controls", "The negative control stays clean. The adversarial control cannot suppress the verdict.");
        card("Benign control", "0 findings. The detector does not flag ordinary admin activity just to look busy.", 96, 240, 500, 128, COLORS.accent);
        card("Injection control", "Logs contain 'do not flag' and 'ignore previous instructions'. The attack chain still fires, and manipulation is flagged.", 684, 240, 500, 128, COLORS.red);
        terminal(DATA.injectionLines, 160, 408, 960, 148, 8, "injection output");
        caption("Hostile log text is treated as data, not as instructions.");
      } else {
        drawHeader("Submission-ready artifacts", "The repo now includes the required Devpost package: docs, diagram, dataset notes, accuracy report, and execution logs.");
        card("Audit trail", "input_sha256: " + DATA.auditHash.slice(0, 24) + "...\\n" + DATA.eventCount + " events, " + DATA.findingCount + " validated findings.", 90, 250, 520, 132, COLORS.amber);
        card("Execution log", DATA.executionSteps.join("\\n"), 670, 250, 520, 132, COLORS.blue);
        card("Submission shape", "Custom MCP Server is the core pattern. The Claude Code agent trace and raw MCP transcript are preserved under out/claude-agent/.", 230, 430, 820, 110, COLORS.accent);
        caption("The result is intentionally small: local, reproducible, and defensible.");
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

  console.log("[video] refreshing demo artifacts");
  const demoOutput = run("/bin/bash", ["-lc", "./demo.sh"], { maxBuffer: 1024 * 1024 * 10 });
  fs.writeFileSync(DEMO_OUTPUT, demoOutput, "utf8");

  console.log("[video] generating narration audio");
  runInherited("/usr/bin/say", ["-o", NARRATION_AIFF, "-f", NARRATION_TXT]);
  runInherited("/usr/bin/afconvert", ["-f", "m4af", "-d", "aac", NARRATION_AIFF, NARRATION_M4A]);

  const demoLines = demoOutput.trim().split(/\\r?\\n/).filter(Boolean);
  const reportLines = fs.readFileSync(path.join(ROOT, "out/incident/report.md"), "utf8").split(/\\r?\\n/);
  const audit = JSON.parse(fs.readFileSync(path.join(ROOT, "out/incident/audit_trail.json"), "utf8"));
  const execution = JSON.parse(fs.readFileSync(path.join(ROOT, "out/incident/execution_log.json"), "utf8"));
  const data = {
    demoLines: trimLines(demoLines, 42),
    selfCorrectionLines: findLines(demoLines, ["Self-correction guard", "SELF-CORRECTION PASS", "SELF-CORRECTION NOTE"], 0),
    injectionLines: findLines(demoLines, ["Prompt-injection control", "Embedded analyst/AI manipulation", "verdicts unchanged"], 1),
    reportExcerpt: trimLines(findLines(reportLines, ["Suspicious command execution", "Risk score", "decoded_command_preview", "Evidence IDs"], 1), 12),
    auditHash: audit.input_sha256,
    eventCount: audit.event_count,
    findingCount: audit.finding_count,
    executionSteps: execution.steps.map((step) => `${step.seq}. ${step.operation}: ${step.status}`),
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
