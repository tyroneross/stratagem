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

/* ── Progress + Agent Panel ── */
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
.agents-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.agent-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-family: var(--mono);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
  transition: opacity 0.3s;
}
.agent-chip .agent-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse 1.2s infinite;
}
.agent-chip.completed {
  opacity: 0.5;
  background: color-mix(in srgb, var(--success) 8%, transparent);
  color: var(--success);
  border-color: color-mix(in srgb, var(--success) 15%, transparent);
}
.agent-chip.completed .agent-dot {
  background: var(--success);
  animation: none;
}
.agent-model {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 500;
}
.agent-model.opus {
  background: color-mix(in srgb, var(--warn) 15%, transparent);
  color: var(--warn);
}
.agent-model.sonnet {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  color: var(--accent);
}
.agent-model.haiku {
  background: color-mix(in srgb, var(--success) 10%, transparent);
  color: var(--success);
}
.agent-action {
  font-size: 11px;
  color: var(--text-muted);
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
/* ── Tab Navigation ── */
.tab-nav {
  display: flex;
  gap: 24px;
  margin-left: auto;
}
.tab-nav button {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 4px 0;
  font-family: var(--font);
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.tab-nav button.active {
  color: var(--text);
  font-weight: 500;
  border-bottom: 2px solid var(--accent);
}
.tab-panel { display: none; }
.tab-panel.active { display: flex; flex-direction: column; gap: 20px; }

/* ── Architecture graph ── */
.graph-container {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px;
  overflow: auto;
}
.graph-container svg { width: 100%; height: auto; }
.graph-container svg text {
  font-family: var(--mono);
  fill: var(--text);
}
.graph-container svg .layer-label {
  font-size: 11px;
  fill: var(--text-muted);
  font-weight: 500;
}
.graph-container svg .node-rect {
  stroke-width: 2;
  rx: 6;
  ry: 6;
  fill: var(--surface);
  transition: opacity 0.2s;
}
.graph-container svg .node-text {
  font-size: 11px;
  text-anchor: middle;
  dominant-baseline: central;
  pointer-events: none;
}
.graph-container svg .edge-path {
  fill: none;
  transition: opacity 0.2s;
}
.graph-container svg .dimmed { opacity: 0.15; }
.graph-loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 13px;
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
  <nav class="tab-nav">
    <button class="active" onclick="switchTab('research')">Research</button>
    <button onclick="switchTab('architecture')">Architecture</button>
  </nav>
</div>
<div class="main">
  <div id="tab-research" class="tab-panel active">
  <div class="input-area">
    <textarea id="prompt" placeholder="Enter your research question..."></textarea>
    <div class="controls">
      <select id="model">
        <option value="">Orchestrator: Opus (default)</option>
        <option value="sonnet">Orchestrator: Sonnet (fast)</option>
        <option value="haiku">Orchestrator: Haiku (fastest)</option>
      </select>
      <button class="btn btn-primary" id="runBtn" onclick="runQuery()">Run Research</button>
      <button class="btn btn-stop" id="stopBtn" onclick="stopQuery()" style="display:none">Stop</button>
      <div class="status" id="status" style="margin-left:auto">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">Ready</span>
      </div>
    </div>
  </div>

  <div class="progress-panel" id="progressPanel">
    <div class="progress-bar-wrap">
      <span class="phase-label" id="phaseLabel">Starting...</span>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" id="progressFill"></div>
      </div>
      <span class="progress-label" id="progressLabel">0%</span>
    </div>
    <div class="agents-list" id="agentsList"></div>
  </div>

  <div class="output-area" id="output"></div>
  </div><!-- /tab-research -->

  <div id="tab-architecture" class="tab-panel">
    <div class="graph-container" id="graphContainer">
      <div class="graph-loading" id="graphLoading">Loading architecture...</div>
    </div>
  </div><!-- /tab-architecture -->
</div>
<div class="footer">
  Stratagem &mdash; Market research agent powered by Claude
</div>
<script>
let eventSource = null;
const threadId = sessionStorage.getItem('threadId') || ('web_' + Date.now());
sessionStorage.setItem('threadId', threadId);

// Tab switching
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.querySelector('.tab-nav button[onclick*="' + name + '"]').classList.add('active');
  if (name === 'architecture' && !graphLoaded) loadGraph();
}

// Phase tracking
const PHASES = ['Plan', 'Execute', 'Validate', 'Report'];
let currentPhase = 0;
let activeAgents = {};   // name -> {action, active}
let completedAgents = {};

function setStatus(state, text) {
  document.getElementById('statusDot').className = 'dot ' + state;
  document.getElementById('statusText').textContent = text;
}

function showProgress(visible) {
  document.getElementById('progressPanel').classList.toggle('visible', visible);
}

function updateProgress(phase, pct) {
  document.getElementById('phaseLabel').textContent = phase;
  const fill = document.getElementById('progressFill');
  fill.style.width = pct + '%';
  fill.classList.toggle('done', pct >= 100);
  document.getElementById('progressLabel').textContent = Math.round(pct) + '%';
}

function addAgent(name, action, model) {
  if (activeAgents[name]) return;
  activeAgents[name] = { action, model: model || 'sonnet', active: true };
  renderAgents();
}

function completeAgent(name) {
  if (activeAgents[name]) {
    activeAgents[name].active = false;
    completedAgents[name] = true;
    renderAgents();
  }
}

function renderAgents() {
  const el = document.getElementById('agentsList');
  el.innerHTML = '';
  for (const [name, info] of Object.entries(activeAgents)) {
    const chip = document.createElement('div');
    chip.className = 'agent-chip' + (info.active ? '' : ' completed');
    const modelTag = '<span class="agent-model ' + info.model + '">' + info.model + '</span>';
    chip.innerHTML = '<span class="agent-dot"></span>'
      + '<span>' + escapeHtml(name) + '</span>'
      + modelTag
      + '<span class="agent-action">' + escapeHtml(info.action) + '</span>';
    el.appendChild(chip);
  }
}

function detectPhase(text) {
  const lower = text.toLowerCase();
  if (lower.includes('phase 1') || lower.includes('planning')) return { idx: 0, label: 'Phase 1: Planning' };
  if (lower.includes('phase 2') || lower.includes('gathering') || lower.includes('extracting')) return { idx: 1, label: 'Phase 2: Executing' };
  if (lower.includes('phase 3') || lower.includes('validat') || lower.includes('verif')) return { idx: 2, label: 'Phase 3: Validating' };
  if (lower.includes('phase 4') || lower.includes('report') || lower.includes('final')) return { idx: 3, label: 'Phase 4: Reporting' };
  return null;
}

function runQuery() {
  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) return;

  const model = document.getElementById('model').value;
  const output = document.getElementById('output');
  output.innerHTML = '';
  activeAgents = {};
  completedAgents = {};
  currentPhase = 0;

  document.getElementById('runBtn').disabled = true;
  document.getElementById('runBtn').style.display = 'none';
  document.getElementById('stopBtn').style.display = 'inline-block';
  setStatus('running', 'Running...');
  showProgress(true);
  updateProgress('Starting...', 2);
  renderAgents();

  const params = new URLSearchParams({ prompt, thread_id: threadId });
  if (model) params.set('model', model);
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
      addAgent(data.name, data.action, data.model);
      if (currentPhase === 0 && data.name !== 'research-planner') {
        currentPhase = 1;
        updateProgress('Phase 2: Executing', 30);
      }
    } else if (data.type === 'agent_end') {
      completeAgent(data.name);
    } else if (data.type === 'tool') {
      // Show non-agent tools subtly
      if (!data.is_agent) {
        output.innerHTML += '<span class="tool-use">[' + escapeHtml(data.name) + ']</span>\\n';
      }
    } else if (data.type === 'done') {
      updateProgress('Complete', 100);
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
    // Mark all remaining agents as complete
    for (const name of Object.keys(activeAgents)) completeAgent(name);
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

// ── Architecture Graph ──
let graphLoaded = false;

async function loadGraph() {
  const container = document.getElementById('graphContainer');
  const loading = document.getElementById('graphLoading');
  try {
    const res = await fetch('/api/graph');
    if (!res.ok) throw new Error('Failed to load graph');
    const data = await res.json();
    loading.style.display = 'none';
    renderGraph(data, container);
    graphLoaded = true;
  } catch (e) {
    loading.textContent = 'Failed to load architecture: ' + e.message;
  }
}

function renderGraph(data, container) {
  const nodes = data.nodes || [];
  const edges = data.edges || [];
  if (!nodes.length) { container.innerHTML = '<div class="graph-loading">No architecture data</div>'; return; }

  // Classify nodes into layers
  const layers = [[], [], []]; // 0=control, 1=agents, 2=tools
  const nodeMap = {};
  nodes.forEach(n => {
    nodeMap[n.id] = n;
    if (n.name === 'control-agent') { n._layer = 0; layers[0].push(n); }
    else if (n.type === 'agent') { n._layer = 1; layers[1].push(n); }
    else { n._layer = 2; layers[2].push(n); }
  });

  // Layout constants
  const PAD = 80, LAYER_Y = [60, 220, 380];
  const LAYER_LABELS = ['Orchestrator', 'Subagents', 'Tools'];
  const NODE_SIZES = { 0: [140, 44], 1: [110, 36], 2: [100, 32] };
  const NODE_COLORS = { 0: '#dc2626' };
  const AGENT_MODEL_COLORS = { opus: '#7c3aed', sonnet: '#0891b2' };

  // Position nodes horizontally within each layer
  const positions = {};
  layers.forEach((layer, li) => {
    const [w] = NODE_SIZES[li];
    const gap = li === 2 ? 12 : 20;
    const totalW = layer.length * w + (layer.length - 1) * gap;
    const startX = PAD + (li === 0 ? (Math.max(layers[1].length, layers[2].length) * (NODE_SIZES[1][0] + 20) - totalW) / 2 : 0);
    layer.forEach((n, i) => {
      positions[n.id] = { x: startX + i * (w + gap) + w / 2, y: LAYER_Y[li], w, h: NODE_SIZES[li][1] };
    });
  });

  // Calculate SVG dimensions
  let maxX = PAD;
  Object.values(positions).forEach(p => { if (p.x + p.w / 2 + PAD > maxX) maxX = p.x + p.w / 2 + PAD; });
  const svgW = Math.max(maxX, 800);
  const svgH = LAYER_Y[2] + 60;

  // Build edge connection map for hover
  const connMap = {}; // nodeId -> Set of connected nodeIds
  edges.forEach(e => {
    if (!connMap[e.source]) connMap[e.source] = new Set();
    if (!connMap[e.target]) connMap[e.target] = new Set();
    connMap[e.source].add(e.target);
    connMap[e.target].add(e.source);
  });

  // Get node border color
  function nodeColor(n) {
    if (n._layer === 0) return NODE_COLORS[0];
    if (n._layer === 1) {
      const tags = (n.tags || []).join(' ');
      if (tags.includes('opus')) return AGENT_MODEL_COLORS.opus;
      return AGENT_MODEL_COLORS.sonnet;
    }
    return '#059669';
  }

  // Edge style
  function edgeStyle(type) {
    if (type === 'service-call') {
      // Check if it's agent delegation or tool usage by looking at semantic
      return { dash: '', width: 1.5, color: 'var(--text-muted)' };
    }
    return { dash: '4 3', width: 1, color: 'var(--text-muted)' };
  }

  // Build SVG
  let svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + svgW + ' ' + svgH + '">';

  // Arrowhead marker
  svg += '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">';
  svg += '<path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-muted)" /></marker></defs>';

  // Layer labels
  LAYER_LABELS.forEach((label, i) => {
    svg += '<text x="12" y="' + (LAYER_Y[i] + 4) + '" class="layer-label">' + label + '</text>';
  });

  // Edges
  edges.forEach(e => {
    const src = positions[e.source], tgt = positions[e.target];
    if (!src || !tgt) return;
    const connType = e.type || 'service-call';
    const isFeedback = connType === 'service-call' && src.y > tgt.y;
    const style = isFeedback ? { dash: '6 3', width: 1.5, color: 'var(--text-muted)' } : edgeStyle(connType);
    const isToolConn = tgt.y > src.y && nodeMap[e.target] && nodeMap[e.target].type === 'service';
    if (isToolConn) { style.dash = '2 2'; style.width = 1; }

    // Quadratic bezier
    const midY = (src.y + tgt.y) / 2;
    const d = 'M ' + src.x + ' ' + (src.y + src.h / 2) + ' Q ' + src.x + ' ' + midY + ' ' + tgt.x + ' ' + (tgt.y - tgt.h / 2);
    svg += '<path class="edge-path" data-src="' + escapeAttr(e.source) + '" data-tgt="' + escapeAttr(e.target) + '" d="' + d + '" ';
    svg += 'stroke="' + style.color + '" stroke-width="' + style.width + '"';
    if (style.dash) svg += ' stroke-dasharray="' + style.dash + '"';
    svg += ' marker-end="url(#arrow)" />';
  });

  // Nodes
  nodes.forEach(n => {
    const p = positions[n.id];
    if (!p) return;
    const color = nodeColor(n);
    svg += '<g class="node-group" data-id="' + escapeAttr(n.id) + '">';
    svg += '<rect class="node-rect" x="' + (p.x - p.w / 2) + '" y="' + (p.y - p.h / 2) + '" width="' + p.w + '" height="' + p.h + '" stroke="' + color + '" />';
    // Truncate long names
    const label = n.name.length > 16 ? n.name.slice(0, 15) + '...' : n.name;
    svg += '<text class="node-text" x="' + p.x + '" y="' + p.y + '">' + escapeHtml(label) + '</text>';
    svg += '</g>';
  });

  svg += '</svg>';
  container.innerHTML = svg;

  // Hover interactivity
  container.querySelectorAll('.node-group').forEach(g => {
    g.addEventListener('mouseenter', () => {
      const id = g.dataset.id;
      const connected = connMap[id] || new Set();
      container.querySelectorAll('.node-group').forEach(ng => {
        ng.querySelector('.node-rect').classList.toggle('dimmed', ng.dataset.id !== id && !connected.has(ng.dataset.id));
      });
      container.querySelectorAll('.edge-path').forEach(ep => {
        ep.classList.toggle('dimmed', ep.dataset.src !== id && ep.dataset.tgt !== id);
      });
    });
    g.addEventListener('mouseleave', () => {
      container.querySelectorAll('.dimmed').forEach(el => el.classList.remove('dimmed'));
    });
  });
}
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

    def _handle_research(self, parsed):
        """Stream research results as Server-Sent Events."""
        params = parse_qs(parsed.query)
        prompt = params.get("prompt", [None])[0]

        if not prompt:
            self._json_response({"error": "No prompt provided"}, 400)
            return

        model = params.get("model", [None])[0]
        thread_id = params.get("thread_id", [None])[0]

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
            loop.run_until_complete(self._stream_research(prompt, model, thread_id, send_event))
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

    async def _stream_research(self, prompt: str, model: str | None, thread_id: str | None, send_event):
        """Run research and stream events with agent tracking."""
        from stratagem.agent import run_research, AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

        cwd = Path.cwd()
        stratagem_dir = cwd / ".stratagem"
        for subdir in ["cache", "filings", "extractions", "reports", "threads", "artifacts"]:
            (stratagem_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create thread if specified
        if thread_id:
            from stratagem.threads import create_thread
            create_thread(thread_id, cwd)

        active_agents = set()

        async for message in run_research(
            prompt=prompt,
            cwd=cwd,
            model=model,
            thread_id=thread_id,
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
                                model = _AGENT_MODELS.get(agent_name, "sonnet")
                                send_event({
                                    "type": "agent_start",
                                    "name": agent_name,
                                    "action": action,
                                    "model": model,
                                })
                                active_agents.add(agent_name)
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
    server = HTTPServer(("127.0.0.1", port), StratagemHandler)
    print(f"Stratagem UI running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
