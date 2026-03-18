"""Simple web UI for launching Stratagem research queries.

Serves a single-page interface and streams agent output via Server-Sent Events.

Usage:
    stratagem --ui           # Launch at http://localhost:8420
    stratagem --ui --port 9000  # Custom port
"""

import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Port default
DEFAULT_PORT = 8420

# Model overrides persisted to .stratagem/agent_config.json
_model_overrides: dict[str, str] = {}


def _load_config():
    config_path = Path.cwd() / ".stratagem" / "agent_config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            _model_overrides.update(data.get("model_overrides", {}))
        except (json.JSONDecodeError, OSError):
            pass


def _save_config():
    config_path = Path.cwd() / ".stratagem" / "agent_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"model_overrides": _model_overrides}, indent=2), encoding="utf-8")

# Static HTML served inline (single file, no build step)
_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stratagem</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#x1F3AF;</text></svg>">
<style>
:root {
  --bg: #fafafa;
  --surface: #ffffff;
  --border: #e5e5e5;
  --text: #1a1a1a;
  --text-muted: #737373;
  --accent: #2563eb;
  --accent-hover: #1d4ed8;
  --success: #16a34a;
  --error: #dc2626;
  --warn: #d97706;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --mono: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0a0a0a;
    --surface: #171717;
    --border: #262626;
    --text: #e5e5e5;
    --text-muted: #a3a3a3;
    --accent: #3b82f6;
    --accent-hover: #60a5fa;
    --success: #22c55e;
    --warn: #f59e0b;
  }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
}
.header h1 { font-size: 18px; font-weight: 600; letter-spacing: -0.01em; }
.header .version { font-size: 11px; color: var(--text-muted); font-family: var(--mono); }
.main {
  flex: 1;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.input-area { display: flex; flex-direction: column; gap: 12px; }
.input-area textarea {
  width: 100%;
  min-height: 80px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-family: var(--font);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}
.input-area textarea:focus { border-color: var(--accent); }
.input-area textarea::placeholder { color: var(--text-muted); }
.controls { display: flex; align-items: center; gap: 12px; }
.controls select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-family: var(--font);
  outline: none;
  cursor: pointer;
}
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
  font-family: var(--font);
}
.btn-primary { background: var(--accent); color: white; }
.btn-primary:hover { background: var(--accent-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-stop { background: var(--error); color: white; }
.btn-stop:hover { opacity: 0.85; }
.status {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--mono);
  display: flex;
  align-items: center;
  gap: 8px;
}
.status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.status .dot.running { background: var(--accent); animation: pulse 1.5s infinite; }
.status .dot.done { background: var(--success); }
.status .dot.error { background: var(--error); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

/* -- Progress Panel -- */
.progress-panel {
  display: none;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.progress-panel.visible { display: flex; }
.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-bar-track {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  width: 0%;
  transition: width 0.4s ease;
}
.progress-bar-fill.done { background: var(--success); }
.progress-label {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--mono);
  white-space: nowrap;
  min-width: 100px;
  text-align: right;
}
.phase-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}

.output-area {
  flex: 1;
  min-height: 250px;
  max-height: 500px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  overflow-y: auto;
  font-family: var(--mono);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.output-area:empty::before { content: "Output will appear here..."; color: var(--text-muted); }
.output-area .tool-use { color: var(--accent); font-weight: 500; }
.output-area .error { color: var(--error); }
.output-area .meta { color: var(--text-muted); font-size: 12px; }

/* -- Phase Diagram -- */
.phase-diagram {
  display: flex;
  align-items: flex-start;
  padding: 20px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow-x: auto;
}
.phase-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 100px;
}
.phase-header {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  padding-bottom: 8px;
}
.phase-arrow {
  display: flex;
  align-items: center;
  padding: 24px 6px 0;
  color: var(--border);
  font-size: 20px;
  user-select: none;
}
.phase-node {
  width: 100%;
  max-width: 130px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 12px;
  text-align: center;
  cursor: default;
  transition: all 0.3s ease;
}
.phase-node:hover {
  border-color: var(--text-muted);
  color: var(--text);
}
.phase-node .node-label { font-weight: 500; }
.phase-node .node-model {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-top: 2px;
  opacity: 0.5;
}
.phase-node.model-opus { border-left: 3px solid #7c3aed; }
.phase-node.model-sonnet { border-left: 3px solid #0891b2; }

/* -- Live Node States -- */
.phase-node.active {
  background: var(--accent);
  border-color: var(--accent-hover);
  color: white;
  border-left-color: var(--accent-hover);
  animation: pulse 1.5s ease-in-out infinite;
}
.phase-node.active .node-model { opacity: 0.8; color: inherit; }
.phase-node.completed {
  border-color: #93c5fd;
  color: #1d4ed8;
  background: #dbeafe;
}
.phase-node.completed.model-opus,
.phase-node.completed.model-sonnet { border-left-color: #93c5fd; }
@media (prefers-color-scheme: dark) {
  .phase-node.completed {
    background: #1e3a5f;
    color: #93c5fd;
  }
}
.phase-node.completed .node-model { opacity: 0.7; }
.phase-node.dimmed { opacity: 0.25; }

/* -- Agent Detail Panel -- */
.detail-panel {
  position: fixed;
  top: 0; right: -400px; width: 400px; height: 100vh;
  background: var(--surface);
  border-left: 1px solid var(--border);
  z-index: 100;
  display: flex; flex-direction: column;
  transition: right 0.25s ease;
  box-shadow: -4px 0 24px rgba(0,0,0,0.08);
}
.detail-panel.open { right: 0; }
.detail-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.detail-panel-header h2 { font-size: 16px; font-weight: 600; margin: 0; }
.detail-close {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border: none; background: none;
  font-size: 20px; color: var(--text-muted);
  cursor: pointer; border-radius: 4px;
}
.detail-close:hover { background: var(--border); color: var(--text); }
.detail-panel-body { flex: 1; overflow-y: auto; padding: 20px; }
.detail-field { margin-bottom: 16px; }
.detail-label {
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 4px;
}
.detail-model-select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-family: var(--font);
  outline: none;
  cursor: pointer;
  width: 100%;
}
.detail-prompt {
  font-family: var(--mono); font-size: 12px; line-height: 1.6;
  white-space: pre-wrap; color: var(--text);
  max-height: 400px; overflow-y: auto;
  background: var(--bg); padding: 12px;
  border-radius: 6px; border: 1px solid var(--border);
  margin: 0;
}
.detail-overlay {
  position: fixed; inset: 0; z-index: 99;
  background: transparent; display: none;
}
.detail-overlay.open { display: block; }

/* -- Config Section (collapsible) -- */
.config-toggle {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-muted);
  cursor: pointer; user-select: none;
  padding: 4px 0;
}
.config-toggle:hover { color: var(--text); }
.config-toggle .arrow { transition: transform 0.2s; font-size: 10px; }
.config-toggle .arrow.open { transform: rotate(90deg); }
.config-section {
  display: none;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.config-section.visible { display: flex; flex-direction: column; gap: 12px; }
.config-row {
  display: flex; align-items: center; gap: 12px;
}
.config-row label {
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted);
  min-width: 100px;
}
.config-row input, .config-row select {
  flex: 1; padding: 6px 10px;
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text);
  font-size: 13px; font-family: var(--font);
  outline: none;
}
.config-row input:focus { border-color: var(--accent); }
.config-save {
  align-self: flex-end;
  padding: 6px 16px;
  border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text-muted);
  font-size: 12px; cursor: default;
  transition: all 0.15s;
}
.config-save.active {
  background: var(--accent); color: white;
  border-color: var(--accent); cursor: pointer;
}

/* -- File Input -- */
.file-input-area {
  display: flex; flex-wrap: wrap; gap: 6px;
  align-items: center; margin-top: 8px;
}
.file-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 4px;
  font-family: var(--mono); font-size: 12px; color: var(--text);
}
.file-chip .remove {
  cursor: pointer; color: var(--text-muted);
  font-size: 14px; line-height: 1;
}
.file-chip .remove:hover { color: var(--error); }
.add-file-btn {
  padding: 4px 10px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  background: none; color: var(--text-muted);
  font-size: 12px; cursor: pointer;
}
.add-file-btn:hover { border-color: var(--text-muted); color: var(--text); }

/* -- Topic Selector -- */
.topic-select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-family: var(--font);
  outline: none;
  cursor: pointer;
}

.footer {
  padding: 12px 24px;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
}
@media (max-width: 640px) {
  .main { padding: 16px; }
  .controls { flex-wrap: wrap; }
}
</style>
</head>
<body>
<div class="header">
  <h1>Stratagem</h1>
  <span class="version">v0.1.0</span>
</div>
<div class="main">
  <div class="input-area">
    <textarea id="prompt" placeholder="Enter your research question..." aria-label="Research question"></textarea>
    <div class="file-input-area" id="fileInputArea">
      <button class="add-file-btn" onclick="addFileInput()">+ Add files</button>
    </div>
    <div class="controls">
      <select id="model" aria-label="Orchestrator model">
        <option value="">Orchestrator: Opus (default)</option>
        <option value="sonnet">Orchestrator: Sonnet (fast)</option>
        <option value="haiku">Orchestrator: Haiku (fastest)</option>
      </select>
      <select id="topicSelect" class="topic-select" aria-label="Research topic">
        <option value="">No topic</option>
      </select>
      <button class="btn btn-primary" id="runBtn" onclick="runQuery()" aria-label="Run research query">Run Research</button>
      <button class="btn btn-stop" id="stopBtn" onclick="stopQuery()" style="display:none" aria-label="Stop running query">Stop</button>
      <div class="status" id="status" style="margin-left:auto">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">Ready</span>
      </div>
    </div>
  </div>

  <div class="config-toggle" onclick="toggleConfig()">
    <span class="arrow" id="configArrow">&#x25B6;</span>
    <span>Settings</span>
  </div>
  <div class="config-section" id="configSection">
    <div class="config-row">
      <label>Memory budget</label>
      <input type="number" id="cfgMemBudget" value="8000" min="1000" max="50000" step="1000">
    </div>
    <div class="config-row">
      <label>Output dir</label>
      <input type="text" id="cfgOutputDir" placeholder=".stratagem/reports/">
    </div>
    <button class="config-save" id="cfgSaveBtn" onclick="saveConfig()">Save</button>
  </div>

  <div class="phase-diagram" id="graphContainer">
    <div class="phase-column">
      <div class="phase-header">Plan</div>
      <div class="phase-node model-sonnet" data-name="research-planner" data-model="sonnet">
        <div class="node-label">Planner</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Execute</div>
      <div class="phase-node model-sonnet" data-name="data-extractor" data-model="sonnet">
        <div class="node-label">Extractor</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-opus" data-name="financial-analyst" data-model="opus">
        <div class="node-label">Financials</div>
        <div class="node-model">opus</div>
      </div>
      <div class="phase-node model-opus" data-name="research-synthesizer" data-model="opus">
        <div class="node-label">Synthesizer</div>
        <div class="node-model">opus</div>
      </div>
      <div class="phase-node model-sonnet" data-name="executive-synthesizer" data-model="sonnet">
        <div class="node-label">Exec Brief</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="flowchart-architect" data-model="sonnet">
        <div class="node-label">Visuals</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="prompt-optimizer" data-model="sonnet">
        <div class="node-label">Optimizer</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Quality</div>
      <div class="phase-node model-sonnet" data-name="plan-validator" data-model="sonnet">
        <div class="node-label">Validator</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="source-verifier" data-model="sonnet">
        <div class="node-label">Verifier</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Deliver</div>
      <div class="phase-node model-sonnet" data-name="report-critic" data-model="sonnet">
        <div class="node-label">Critic</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="design-agent" data-model="sonnet">
        <div class="node-label">Designer</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Learn</div>
      <div class="phase-node model-sonnet" data-name="after-action-analyst" data-model="sonnet">
        <div class="node-label">Debrief</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
  </div>

  <div class="progress-panel" id="progressPanel" aria-hidden="true">
    <div class="progress-bar-wrap">
      <span class="phase-label" id="phaseLabel">Starting...</span>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" id="progressFill"></div>
      </div>
      <span class="progress-label" id="progressLabel">0%</span>
    </div>
  </div>

  <div class="output-area" id="output"></div>

  <div class="detail-overlay" id="detailOverlay" onclick="closeDetail()"></div>
  <div class="detail-panel" id="detailPanel">
    <div class="detail-panel-header">
      <h2 id="detailName">Agent</h2>
      <button class="detail-close" onclick="closeDetail()" aria-label="Close panel">&times;</button>
    </div>
    <div class="detail-panel-body">
      <div class="detail-field">
        <div class="detail-label">Agent ID</div>
        <div id="detailId" style="font-family:var(--mono);font-size:13px"></div>
      </div>
      <div class="detail-field">
        <div class="detail-label">Phase</div>
        <div id="detailPhase" style="font-size:13px"></div>
      </div>
      <div class="detail-field">
        <div class="detail-label">Model</div>
        <select id="detailModel" class="detail-model-select" onchange="updateModel()">
          <option value="sonnet">Sonnet</option>
          <option value="opus">Opus</option>
          <option value="haiku">Haiku</option>
        </select>
      </div>
      <div class="detail-field">
        <div class="detail-label">System Prompt</div>
        <pre class="detail-prompt" id="detailPrompt">Loading...</pre>
      </div>
    </div>
  </div>
</div>
<div class="footer">
  Stratagem &mdash; Strategic research agent powered by Claude
</div>
<script>
let eventSource = null;
const threadId = sessionStorage.getItem('threadId') || ('web_' + Date.now());
sessionStorage.setItem('threadId', threadId);

// Phase tracking
const PHASES = ['Plan', 'Execute', 'Validate', 'Report'];
let currentPhase = 0;

// Live diagram state
let nameToGroup = {};   // agent name -> phase-node div element

function setStatus(state, text) {
  document.getElementById('statusDot').className = 'dot ' + state;
  document.getElementById('statusText').textContent = text;
}

function showProgress(visible) {
  const panel = document.getElementById('progressPanel');
  panel.classList.toggle('visible', visible);
  panel.setAttribute('aria-hidden', !visible);
}

function updateProgress(phase, pct) {
  document.getElementById('phaseLabel').textContent = phase;
  const fill = document.getElementById('progressFill');
  fill.style.width = pct + '%';
  fill.classList.toggle('done', pct >= 100);
  document.getElementById('progressLabel').textContent = Math.round(pct) + '%';
}

function detectPhase(text) {
  const lower = text.toLowerCase();
  if (lower.includes('phase 1') || lower.includes('planning')) return { idx: 0, label: 'Phase 1: Planning' };
  if (lower.includes('phase 2') || lower.includes('gathering') || lower.includes('extracting')) return { idx: 1, label: 'Phase 2: Executing' };
  if (lower.includes('phase 3') || lower.includes('validat') || lower.includes('verif')) return { idx: 2, label: 'Phase 3: Validating' };
  if (lower.includes('phase 4') || lower.includes('report') || lower.includes('final')) return { idx: 3, label: 'Phase 4: Reporting' };
  return null;
}

// -- Live Graph Functions --

function stripPrefix(name) {
  // mcp__stratagem__parse_pdf -> parse_pdf
  if (name.startsWith('mcp__stratagem__')) return name.slice(16);
  if (name.startsWith('mcp__')) return name.split('__').pop();
  return name;
}

function activateNode(name) {
  const g = nameToGroup[name];
  if (!g) return;
  g.classList.remove('completed', 'flash');
  g.classList.add('active');
}

function completeNode(name) {
  const g = nameToGroup[name];
  if (!g) return;
  g.classList.remove('active', 'flash');
  g.classList.add('completed');
}

function flashTool(name) {
  const g = nameToGroup[name];
  if (!g || g.classList.contains('active') || g.classList.contains('completed')) return;
  g.classList.add('flash');
  setTimeout(function() { g.classList.remove('flash'); }, 600);
}

function activateEdge() {}
function completeEdge() {}

function resetNodes() {
  document.querySelectorAll('.phase-node').forEach(function(el) {
    el.classList.remove('active', 'completed', 'flash');
  });
}

function runQuery() {
  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) return;

  const model = document.getElementById('model').value;
  const output = document.getElementById('output');
  output.innerHTML = '';
  currentPhase = 0;

  // Reset graph nodes to idle
  resetNodes();

  document.getElementById('runBtn').disabled = true;
  document.getElementById('runBtn').style.display = 'none';
  document.getElementById('stopBtn').style.display = 'inline-block';
  setStatus('running', 'Running...');
  showProgress(true);
  updateProgress('Starting...', 2);

  const params = new URLSearchParams({ prompt, thread_id: threadId });
  if (model) params.set('model', model);
  var topic = document.getElementById('topicSelect').value;
  if (topic) params.set('topic_id', topic);
  if (inputFiles.length) params.set('input_files', inputFiles.join(','));
  eventSource = new EventSource('/api/research?' + params.toString());

  eventSource.onmessage = function(e) {
    const data = JSON.parse(e.data);

    if (data.type === 'text') {
      output.innerHTML += escapeHtml(data.content);
      // Detect phase transitions from text
      const phase = detectPhase(data.content);
      if (phase && phase.idx >= currentPhase) {
        currentPhase = phase.idx;
        updateProgress(phase.label, ((phase.idx + 1) / PHASES.length) * 85 + 5);
      }
    } else if (data.type === 'agent_start') {
      activateNode(data.name);
      activateNode('control-agent');
      activateEdge('control-agent', data.name);
      if (currentPhase === 0 && data.name !== 'research-planner') {
        currentPhase = 1;
        updateProgress('Phase 2: Executing', 30);
      }
    } else if (data.type === 'agent_end') {
      completeNode(data.name);
      completeEdge('control-agent', data.name);
    } else if (data.type === 'tool') {
      if (!data.is_agent) {
        const toolName = stripPrefix(data.name);
        flashTool(toolName);
        output.innerHTML += '<span class="tool-use">[' + escapeHtml(data.name) + ']</span>\\n';
      }
    } else if (data.type === 'agent_created') {
      addDynamicNode(data.name, data.display_name, data.model);
    } else if (data.type === 'done') {
      updateProgress('Complete', 100);
      completeNode('control-agent');
      // Complete any remaining active nodes
      Object.keys(nameToGroup).forEach(function(name) {
        const g = nameToGroup[name];
        if (g.classList.contains('active')) completeNode(name);
      });
      const meta = '\\n<span class="meta">--- Done (' + data.turns + ' turns, ' + data.duration_ms + 'ms)';
      const meta_str = data.cost ? meta + ' | $' + data.cost + '</span>' : meta + '</span>';
      output.innerHTML += meta_str;
      finish('done', 'Complete');
    } else if (data.type === 'error') {
      output.innerHTML += '<span class="error">Error: ' + escapeHtml(data.message) + '</span>\\n';
      finish('error', 'Error');
    }

    output.scrollTop = output.scrollHeight;
  };

  eventSource.onerror = function() {
    finish('error', 'Connection lost');
  };
}

function stopQuery() {
  if (eventSource) { eventSource.close(); eventSource = null; }
  finish('error', 'Stopped');
}

function finish(state, text) {
  if (eventSource) { eventSource.close(); eventSource = null; }
  document.getElementById('runBtn').disabled = false;
  document.getElementById('runBtn').style.display = 'inline-block';
  document.getElementById('stopBtn').style.display = 'none';
  setStatus(state, text);
  if (state === 'done') {
    // Complete all remaining active nodes
    Object.keys(nameToGroup).forEach(function(name) {
      const g = nameToGroup[name];
      if (g.classList.contains('active')) completeNode(name);
    });
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function escapeAttr(str) {
  return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

document.getElementById('prompt').addEventListener('keydown', function(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); runQuery(); }
});

// -- Phase Diagram --

var AGENT_META = {
  'research-planner':      { display: 'Planner',     phase: 'Plan' },
  'data-extractor':        { display: 'Extractor',   phase: 'Execute' },
  'financial-analyst':     { display: 'Financials',  phase: 'Execute' },
  'research-synthesizer':  { display: 'Synthesizer', phase: 'Execute' },
  'executive-synthesizer': { display: 'Exec Brief',  phase: 'Execute' },
  'flowchart-architect':   { display: 'Visuals',     phase: 'Execute' },
  'prompt-optimizer':      { display: 'Optimizer',   phase: 'Execute' },
  'plan-validator':        { display: 'Validator',   phase: 'Quality' },
  'source-verifier':       { display: 'Verifier',    phase: 'Quality' },
  'report-critic':         { display: 'Critic',      phase: 'Deliver' },
  'design-agent':          { display: 'Designer',    phase: 'Deliver' },
  'after-action-analyst':  { display: 'Debrief',     phase: 'Learn' },
};

var currentDetailAgent = null;

function openDetail(agentName) {
  currentDetailAgent = agentName;
  var meta = AGENT_META[agentName] || { display: agentName.replace(/-/g, ' ').replace(/\\b\\w/g, function(c){return c.toUpperCase();}), phase: 'Dynamic' };
  document.getElementById('detailName').textContent = meta.display;
  document.getElementById('detailId').textContent = agentName;
  document.getElementById('detailPhase').textContent = meta.phase;
  document.getElementById('detailPrompt').textContent = 'Loading...';
  document.getElementById('detailPanel').classList.add('open');
  document.getElementById('detailOverlay').classList.add('open');

  var node = nameToGroup[agentName];
  var currentModel = node ? (node.dataset.model || 'sonnet') : 'sonnet';
  document.getElementById('detailModel').value = currentModel;

  fetch('/api/agents/' + encodeURIComponent(agentName) + '/prompt')
    .then(function(r) { return r.json(); })
    .then(function(d) { document.getElementById('detailPrompt').textContent = d.prompt || 'No prompt found'; })
    .catch(function() { document.getElementById('detailPrompt').textContent = 'Failed to load prompt'; });
}

function closeDetail() {
  currentDetailAgent = null;
  document.getElementById('detailPanel').classList.remove('open');
  document.getElementById('detailOverlay').classList.remove('open');
}

function updateModel() {
  if (!currentDetailAgent) return;
  var newModel = document.getElementById('detailModel').value;
  fetch('/api/agents/' + encodeURIComponent(currentDetailAgent) + '/model', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: newModel })
  }).then(function(r) { return r.json(); }).then(function(d) {
    if (d.ok) {
      var node = nameToGroup[currentDetailAgent];
      if (node) {
        node.dataset.model = newModel;
        node.className = node.className.replace(/model-\\w+/, 'model-' + newModel);
        node.querySelector('.node-model').textContent = newModel;
      }
    }
  });
}

function addDynamicNode(name, displayName, model) {
  if (nameToGroup[name]) return;
  var execCol = document.querySelectorAll('.phase-column')[1];
  var node = document.createElement('div');
  node.className = 'phase-node model-' + model;
  node.dataset.name = name;
  node.dataset.model = model;
  node.innerHTML = '<div class="node-label">' + escapeHtml(displayName) + '</div>'
    + '<div class="node-model">' + model + ' \\u2726</div>';
  node.style.cursor = 'pointer';
  node.addEventListener('click', function() { openDetail(name); });
  node.addEventListener('mouseenter', function() {
    var col = node.closest('.phase-column');
    document.querySelectorAll('.phase-node').forEach(function(n) {
      if (n !== node && !col.contains(n)) n.classList.add('dimmed');
    });
  });
  node.addEventListener('mouseleave', function() {
    document.querySelectorAll('.phase-node.dimmed').forEach(function(n) {
      n.classList.remove('dimmed');
    });
  });
  execCol.appendChild(node);
  nameToGroup[name] = node;
  node.classList.add('active');
  setTimeout(function() { node.classList.remove('active'); }, 1500);
}

function loadConfig() {
  fetch('/api/agents/config')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var overrides = data.model_overrides || {};
      Object.keys(overrides).forEach(function(name) {
        var node = nameToGroup[name];
        if (node) {
          var model = overrides[name];
          node.dataset.model = model;
          node.className = node.className.replace(/model-\\w+/, 'model-' + model);
          node.querySelector('.node-model').textContent = model;
        }
      });
    }).catch(function() {});
}

function initDiagram() {
  nameToGroup = {};
  document.querySelectorAll('.phase-node[data-name]').forEach(function(el) {
    nameToGroup[el.dataset.name] = el;
  });

  document.querySelectorAll('.phase-node').forEach(function(node) {
    node.style.cursor = 'pointer';
    node.addEventListener('click', function() {
      if (node.dataset.name) openDetail(node.dataset.name);
    });
    node.addEventListener('mouseenter', function() {
      var col = node.closest('.phase-column');
      document.querySelectorAll('.phase-node').forEach(function(n) {
        if (n !== node && !col.contains(n)) n.classList.add('dimmed');
      });
    });
    node.addEventListener('mouseleave', function() {
      document.querySelectorAll('.phase-node.dimmed').forEach(function(n) {
        n.classList.remove('dimmed');
      });
    });
  });

  loadConfig();
}

// -- Topic selector --
var inputFiles = [];

function loadTopics() {
  fetch('/api/topics')
    .then(function(r) { return r.json(); })
    .then(function(topics) {
      var sel = document.getElementById('topicSelect');
      while (sel.options.length > 1) sel.remove(1);
      topics.forEach(function(t) {
        var opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.title || t.id;
        sel.appendChild(opt);
      });
    }).catch(function() {});
}

// -- File input --
function addFileInput() {
  var path = prompt('Enter file path:');
  if (!path || !path.trim()) return;
  inputFiles.push(path.trim());
  renderFiles();
}

function removeFile(idx) {
  inputFiles.splice(idx, 1);
  renderFiles();
}

function renderFiles() {
  var area = document.getElementById('fileInputArea');
  area.innerHTML = '';
  inputFiles.forEach(function(f, i) {
    var chip = document.createElement('span');
    chip.className = 'file-chip';
    chip.innerHTML = escapeHtml(f.split('/').pop())
      + ' <span class="remove" onclick="removeFile(' + i + ')">&times;</span>';
    chip.title = f;
    area.appendChild(chip);
  });
  var btn = document.createElement('button');
  btn.className = 'add-file-btn';
  btn.textContent = '+ Add files';
  btn.onclick = addFileInput;
  area.appendChild(btn);
}

// -- Config section --
var configDirty = false;

function toggleConfig() {
  var section = document.getElementById('configSection');
  var arrow = document.getElementById('configArrow');
  section.classList.toggle('visible');
  arrow.classList.toggle('open');
}

function markConfigDirty() {
  configDirty = true;
  document.getElementById('cfgSaveBtn').classList.add('active');
}

function saveConfig() {
  if (!configDirty) return;
  var body = {
    memory_budget: parseInt(document.getElementById('cfgMemBudget').value) || 8000,
    output_dir: document.getElementById('cfgOutputDir').value.trim() || null,
  };
  fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  }).then(function(r) { return r.json(); }).then(function(d) {
    if (d.ok) {
      configDirty = false;
      document.getElementById('cfgSaveBtn').classList.remove('active');
    }
  });
}

function loadFullConfig() {
  fetch('/api/config')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.memory_budget) document.getElementById('cfgMemBudget').value = data.memory_budget;
      if (data.output_dir) document.getElementById('cfgOutputDir').value = data.output_dir;
    }).catch(function() {});
}

// Wire change detection
document.getElementById('cfgMemBudget').addEventListener('input', markConfigDirty);
document.getElementById('cfgOutputDir').addEventListener('input', markConfigDirty);

// Init on page load
initDiagram();
loadTopics();
loadFullConfig();
</script>
</body>
</html>"""


# Agent action lookup
_AGENT_ACTIONS = {
    "research-planner": "planning research approach",
    "data-extractor": "extracting data",
    "financial-analyst": "analyzing financials",
    "research-synthesizer": "synthesizing findings",
    "executive-synthesizer": "creating executive brief",
    "flowchart-architect": "designing visuals",
    "design-agent": "designing layout",
    "prompt-optimizer": "refining prompts",
    "plan-validator": "checking for drift",
    "source-verifier": "verifying sources",
    "report-critic": "evaluating report quality",
    "after-action-analyst": "running after-action review",
}

# Model assigned to each subagent (from definitions.py)
_AGENT_MODELS = {
    "research-planner": "sonnet",
    "data-extractor": "sonnet",
    "financial-analyst": "opus",
    "research-synthesizer": "opus",
    "executive-synthesizer": "sonnet",
    "flowchart-architect": "sonnet",
    "design-agent": "sonnet",
    "prompt-optimizer": "sonnet",
    "plan-validator": "sonnet",
    "source-verifier": "sonnet",
    "report-critic": "sonnet",
    "after-action-analyst": "sonnet",
}


class StratagemHandler(BaseHTTPRequestHandler):
    """HTTP handler for the Stratagem web UI."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self._serve_html()
        elif parsed.path == "/api/research":
            self._handle_research(parsed)
        elif parsed.path == "/api/graph":
            self._handle_graph()
        elif parsed.path == "/api/threads":
            self._handle_threads()
        elif parsed.path == "/api/health":
            self._json_response({"status": "ok", "version": "0.1.0"})
        elif parsed.path == "/api/topics":
            self._handle_topics()
        elif parsed.path == "/api/config":
            self._handle_get_config()
        elif parsed.path == "/api/agents/config":
            self._handle_agents_config()
        elif parsed.path.startswith("/api/agents/") and parsed.path.endswith("/prompt"):
            name = parsed.path.split("/")[3]
            self._handle_agent_prompt(name)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/agents/") and parsed.path.endswith("/model"):
            name = parsed.path.split("/")[3]
            self._handle_set_model(name)
        elif parsed.path == "/api/config":
            self._handle_save_config()
        else:
            self.send_error(404)

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_UI_HTML.encode("utf-8"))

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _handle_graph(self):
        """Return architecture graph data."""
        cwd = Path.cwd()
        graph_path = cwd / ".claude" / "architecture" / "graph.json"

        if not graph_path.exists():
            # Generate if missing
            try:
                from stratagem.navgator import generate_architecture
                generate_architecture(cwd)
            except Exception:
                pass

        if graph_path.exists():
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            # Enrich nodes with tag info from components
            comp_dir = cwd / ".claude" / "architecture" / "components"
            if comp_dir.exists():
                for node in data.get("nodes", []):
                    comp_file = comp_dir / f"{node['id']}.json"
                    if comp_file.exists():
                        try:
                            comp = json.loads(comp_file.read_text(encoding="utf-8"))
                            node["tags"] = comp.get("tags", [])
                        except Exception:
                            pass
            self._json_response(data)
        else:
            self._json_response({"nodes": [], "edges": []})

    def _handle_threads(self):
        """Return thread list."""
        from stratagem.threads import list_threads
        threads = list_threads(Path.cwd())
        self._json_response(threads)

    def _handle_agents_config(self):
        """Return current agent config (model overrides)."""
        self._json_response({"model_overrides": _model_overrides})

    def _handle_agent_prompt(self, name):
        """Return agent system prompt."""
        from stratagem.subagents.definitions import SUBAGENTS
        agent = SUBAGENTS.get(name)
        if not agent:
            self._json_response({"error": "Unknown agent"}, 404)
            return
        self._json_response({"name": name, "prompt": agent.prompt})

    def _handle_set_model(self, name):
        """Set model override for an agent."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))
        model = body.get("model")
        if model not in ("sonnet", "opus", "haiku"):
            self._json_response({"error": "Invalid model"}, 400)
            return
        _model_overrides[name] = model
        _save_config()
        self._json_response({"ok": True, "name": name, "model": model})

    def _handle_topics(self):
        from stratagem.topics import list_topics
        topics = list_topics(cwd=Path.cwd())
        self._json_response(topics)

    def _handle_get_config(self):
        config_path = Path.cwd() / ".stratagem" / "agent_config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                self._json_response(data)
                return
            except Exception:
                pass
        self._json_response({"model_overrides": _model_overrides, "memory_budget": 8000, "output_dir": None})

    def _handle_save_config(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))
        config_path = Path.cwd() / ".stratagem" / "agent_config.json"
        existing = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        if "memory_budget" in body:
            existing["memory_budget"] = body["memory_budget"]
        if "output_dir" in body:
            existing["output_dir"] = body["output_dir"]
        existing["model_overrides"] = _model_overrides
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        self._json_response({"ok": True})

    def _handle_research(self, parsed):
        """Stream research results as Server-Sent Events."""
        params = parse_qs(parsed.query)
        prompt = params.get("prompt", [None])[0]

        if not prompt:
            self._json_response({"error": "No prompt provided"}, 400)
            return

        model = params.get("model", [None])[0]
        thread_id = params.get("thread_id", [None])[0]
        topic_id = params.get("topic_id", [None])[0]
        input_files_str = params.get("input_files", [None])[0]
        input_files = input_files_str.split(",") if input_files_str else None

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def send_event(data: dict):
            try:
                line = f"data: {json.dumps(data)}\n\n"
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                raise

        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self._stream_research(prompt, model, thread_id, send_event, topic_id, input_files))
            loop.close()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            import traceback
            detail = traceback.format_exc()
            try:
                send_event({"type": "error", "message": f"{e}\n\n{detail}"})
            except Exception:
                pass

    async def _stream_research(self, prompt: str, model: str | None, thread_id: str | None, send_event, topic_id=None, input_files=None):
        """Run research and stream events with agent tracking."""
        from stratagem.agent import run_research, AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

        cwd = Path.cwd()
        stratagem_dir = cwd / ".stratagem"
        for subdir in ["cache", "filings", "extractions", "reports", "threads", "artifacts", "topics", "agents"]:
            (stratagem_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create thread if specified
        if thread_id:
            from stratagem.threads import create_thread
            create_thread(thread_id, cwd)

        # Create topic if specified
        if topic_id:
            from stratagem.topics import create_topic
            create_topic(topic_id, cwd=cwd)

        active_agents = set()

        async for message in run_research(
            prompt=prompt,
            cwd=cwd,
            model=model,
            model_overrides=_model_overrides or None,
            thread_id=thread_id,
            topic_id=topic_id,
            input_files=input_files,
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        send_event({"type": "text", "content": block.text})
                    elif isinstance(block, ToolUseBlock):
                        # Detect Agent tool calls — extract subagent name
                        if block.name == "Agent":
                            agent_name = _extract_agent_name(block.input)
                            if agent_name:
                                action = _AGENT_ACTIONS.get(agent_name, "working")
                                effective_model = _model_overrides.get(agent_name, _AGENT_MODELS.get(agent_name, "sonnet"))
                                send_event({
                                    "type": "agent_start",
                                    "name": agent_name,
                                    "action": action,
                                    "model": effective_model,
                                })
                                active_agents.add(agent_name)
                        elif block.name == "mcp__stratagem__create_specialist":
                            spec = block.input if isinstance(block.input, dict) else {}
                            send_event({
                                "type": "agent_created",
                                "name": spec.get("name", "unknown"),
                                "display_name": spec.get("name", "unknown").replace("-", " ").title(),
                                "model": spec.get("model", "sonnet"),
                            })
                        else:
                            send_event({
                                "type": "tool",
                                "name": block.name,
                                "is_agent": False,
                            })
            elif isinstance(message, ResultMessage):
                # Mark all active agents as complete
                for name in active_agents:
                    send_event({"type": "agent_end", "name": name})
                send_event({
                    "type": "done",
                    "turns": message.num_turns,
                    "duration_ms": message.duration_ms,
                    "cost": f"{message.total_cost_usd:.4f}" if message.total_cost_usd else None,
                })


def _extract_agent_name(tool_input) -> str | None:
    """Extract the agent/subagent name from an Agent tool call input."""
    if isinstance(tool_input, dict):
        # SDK passes agent name in various fields
        for key in ("agent", "name", "agent_name", "subagent"):
            if key in tool_input:
                return tool_input[key]
        # Check prompt field for agent name pattern
        prompt = tool_input.get("prompt", "")
        if isinstance(prompt, str):
            for name in _AGENT_ACTIONS:
                if name in prompt.lower():
                    return name
    return None


def start_ui(port: int = DEFAULT_PORT):
    """Start the Stratagem web UI server."""
    _load_config()
    server = HTTPServer(("127.0.0.1", port), StratagemHandler)
    print(f"Stratagem UI running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
