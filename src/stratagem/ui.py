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
    <div class="controls">
      <select id="model" aria-label="Orchestrator model">
        <option value="">Orchestrator: Opus (default)</option>
        <option value="sonnet">Orchestrator: Sonnet (fast)</option>
        <option value="haiku">Orchestrator: Haiku (fastest)</option>
      </select>
      <button class="btn btn-primary" id="runBtn" onclick="runQuery()" aria-label="Run research query">Run Research</button>
      <button class="btn btn-stop" id="stopBtn" onclick="stopQuery()" style="display:none" aria-label="Stop running query">Stop</button>
      <div class="status" id="status" style="margin-left:auto">
        <span class="dot" id="statusDot"></span>
        <span id="statusText">Ready</span>
      </div>
    </div>
  </div>

  <div class="phase-diagram" id="graphContainer">
    <div class="phase-column">
      <div class="phase-header">Plan</div>
      <div class="phase-node model-sonnet" data-name="research-planner">
        <div class="node-label">Planner</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Execute</div>
      <div class="phase-node model-sonnet" data-name="data-extractor">
        <div class="node-label">Extractor</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-opus" data-name="financial-analyst">
        <div class="node-label">Financials</div>
        <div class="node-model">opus</div>
      </div>
      <div class="phase-node model-opus" data-name="research-synthesizer">
        <div class="node-label">Synthesizer</div>
        <div class="node-model">opus</div>
      </div>
      <div class="phase-node model-sonnet" data-name="executive-synthesizer">
        <div class="node-label">Exec Brief</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="flowchart-architect">
        <div class="node-label">Visuals</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="prompt-optimizer">
        <div class="node-label">Optimizer</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Quality</div>
      <div class="phase-node model-sonnet" data-name="plan-validator">
        <div class="node-label">Validator</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="source-verifier">
        <div class="node-label">Verifier</div>
        <div class="node-model">sonnet</div>
      </div>
    </div>
    <div class="phase-arrow" aria-hidden="true">&#x2192;</div>
    <div class="phase-column">
      <div class="phase-header">Deliver</div>
      <div class="phase-node model-sonnet" data-name="report-critic">
        <div class="node-label">Critic</div>
        <div class="node-model">sonnet</div>
      </div>
      <div class="phase-node model-sonnet" data-name="design-agent">
        <div class="node-label">Designer</div>
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
</div>
<div class="footer">
  Stratagem &mdash; Market research agent powered by Claude
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

function initDiagram() {
  nameToGroup = {};
  document.querySelectorAll('.phase-node[data-name]').forEach(function(el) {
    nameToGroup[el.dataset.name] = el;
  });

  // Hover: dim nodes outside hovered node's phase
  document.querySelectorAll('.phase-node').forEach(function(node) {
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
}

// Init on page load
initDiagram();
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
