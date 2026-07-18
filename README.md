# Swarm

A **local-first visual workflow automation engine** — build automations on an n8n-style drag-and-drop canvas, run them on your own machine, and extend the node library by dropping a single Python file.

**v2 is a complete rewrite**: FastAPI backend with a branch-aware async execution engine, and a React + React Flow editor with live run status. No CDNs, no cloud — everything runs and stays local.

---

## What it does

- **Visual editor** — drag nodes from the palette, wire them up, configure them in a side panel. Zoom, pan, minimap, import/export JSON.
- **Real data flow** — reference upstream data anywhere with templates:
  `{{ input.name }}`, `{{ http_request_1.body.items[0].title }}`, `{{ env.OPENAI_API_KEY }}`
- **Real branching** — the **If** node routes down its `true`/`false` handle; the untaken branch (and everything after it) is skipped, not executed.
- **Concurrent execution** — independent branches run in parallel; runs execute in the background with **live per-node status** streamed to the canvas over WebSocket.
- **Run history** — every execution is persisted with statuses, outputs, and logs.
- **Multi-user** — login/register with session auth (PBKDF2 hashing).

## Node library (v2)

| Node | What it does |
|---|---|
| Manual Trigger | Starts the run, with an optional JSON payload |
| HTTP Request | Call any API (headers, params, JSON/text body, basic error policy) |
| If | Route to true/false branches (simple comparison or sandboxed expression) |
| Set Variables | Set/merge fields onto the flowing data |
| Transform | Pick/omit fields, build objects from templates, parse/stringify JSON |
| LLM | OpenAI, DeepSeek, or any OpenAI-compatible endpoint (local Ollama works) |
| Gmail: Send / Read | Send mail (text/html, cc/bcc); search and read your inbox |
| Sheets: Append / Read | Append rows to and read rows from Google Sheets |
| Calendar: Create / List | Create events (timed or all-day, attendees) and list upcoming ones |
| Drive: Upload | Create files in Google Drive from workflow data |
| Docs: Create | Create a Google Doc with initial content |
| Read / Write File | File I/O, sandboxed to the `data/` directory |
| Delay | Non-blocking wait |

## Connecting Google (one-time, ~5 minutes)

Google nodes authenticate through an OAuth credential you own - nothing goes
through third-party servers:

1. In the [Google Cloud Console](https://console.cloud.google.com/apis/credentials),
   create a project (or reuse one) and an **OAuth client ID** of type
   **Web application**.
2. Add this authorized redirect URI: `http://localhost:8000/api/oauth/google/callback`
3. Enable the APIs you plan to use (Gmail API, Google Sheets API, Google
   Calendar API, Google Drive API, Google Docs API) under "Enabled APIs".
4. In Swarm, open **Credentials** in the toolbar, add a Google credential with
   your client ID/secret, pick the services, and finish the Google consent
   screen that opens.

Tokens are stored encrypted on your machine and refreshed automatically.
Google nodes then offer the credential in a dropdown.

## Quickstart

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js 18+.

```bash
# 1. Backend deps + tests
cd backend
uv sync
uv run pytest          # 15 engine tests

# 2. Frontend build (one-time, or after UI changes)
cd ../frontend
npm install
npm run build

# 3. Run — backend serves the built UI at http://localhost:8000
cd ../backend
uv run uvicorn app.main:app --port 8000
```

Open http://localhost:8000, register an account, and build.

### Dev mode (hot reload)

```bash
# terminal 1
cd backend && uv run uvicorn app.main:app --port 8000 --reload
# terminal 2
cd frontend && npm run dev    # http://localhost:5173, proxies /api
```

## Writing your own node

Drop a `.py` file into the `nodes/` folder at the project root — that's the whole integration. No restart needed: hit **Reload nodes** in the palette (or `POST /api/nodes/reload`) and it appears. Files that fail to load show up with their exact error instead of disappearing silently.

```python
from app.engine.types import NodeContext

NODE_TYPE = "shout"
NODE_NAME = "Shout"
NODE_DESCRIPTION = "Uppercase a message"
NODE_CATEGORY = "Data"
NODE_COLOR = "#f43f5e"
NODE_ICON = "box"
NODE_INPUTS = ["in"]
NODE_OUTPUTS = ["out"]
CONFIG_FIELDS = [
    {"key": "message", "label": "Message", "type": "string", "required": True,
     "placeholder": "{{ input.text }}"},
]

async def run(ctx: NodeContext):
    return {"shouted": str(ctx.config["message"]).upper()}
```

Config values arrive with `{{ }}` templates already resolved. Return a dict (output data), or `NodeOutput(data, handle="true")` to route between multiple output handles. Plain `def run` also works (it runs in a worker thread). A drop-in node with the same `NODE_TYPE` as a built-in overrides it. Built-in nodes live in `backend/app/nodes/` and follow the identical contract.

## Configuration (env vars)

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` | Default LLM keys (or set per-node) |
| `SWARM_FILES_DIR` | File-node sandbox directory (default `./data`) |
| `SWARM_NODES_DIR` | Drop-in node directory (default `./nodes`) |
| `SWARM_ALLOW_ANY_PATH=1` | Disable the file sandbox |
| `SWARM_SECRET` | Session signing key (auto-generated otherwise) |
| `SWARM_DATABASE_URL` | Defaults to SQLite in `backend/instance/` |

## Architecture

```
frontend/            React + TypeScript + React Flow (Vite)
backend/
  app/main.py        FastAPI app, serves API + built frontend
  app/engine/
    executor.py      branch-aware concurrent DAG executor
    templating.py    {{ }} resolver + sandboxed expressions
    registry.py      auto-discovers node modules
    runs.py          background runs, WS event streams, history
  app/nodes/         one .py file per node type
  tests/             engine test suite
```

Design notes: no `eval()` anywhere (expressions go through `simpleeval`), file nodes are path-sandboxed, `{{ env.* }}` only exposes allow-listed variable names, runs are capped by per-node timeouts, and workflow definitions are validated (unknown types, cycles, missing triggers) before execution.
