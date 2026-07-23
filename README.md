# Waypoint# Waypoint

**A long-horizon repo-migration agent that stays cheap *and* coherent over
multi-hour runs — built on [Paritok](https://github.com/Paritok-official/paritok-4b-v1).**

[![Built with Paritok](https://img.shields.io/badge/Built%20with-Paritok-1f2d3d)](https://github.com/Paritok-official/paritok-4b-v1)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)

Most AI coding agents fall apart the longer they run: context balloons past
what's affordable, or the usual fix — summarizing old history — quietly loses
the plot. Long-horizon migration and refactor tasks are exactly where this
shows up, and it's why even strong agents struggle to finish large,
multi-file jobs reliably.

Waypoint is a repo-wide migration agent (this demo: migrating a codebase off
`requests` and onto `httpx`, file by file, with tests enforced at every step)
built to run for hours unattended. It stays affordable because every request
routes through Paritok's compression proxy — and unlike naive summarization,
Paritok's compression is non-destructive: compressed content is tagged and
recoverable on demand via its `expand_context` tool, so the agent doesn't
have to choose between cheap and reliable.

---

## What makes this different

A token-savings percentage is table stakes. Waypoint's dashboard tracks
**reliability over a long run**, not just cost:

- **Live token/cost savings**, pulled directly from Paritok's own `/stats`
  endpoint — not estimated.
- **`expand_context` recall counter** — every time the agent needed context
  that had been compressed away, it recovered the original instead of
  guessing. Each recall is proof nothing was silently lost.
- **Plan adherence**, visualized as a waypoint trail — one node per file,
  showing exactly which are pending, in progress, done, or failed.
- **Durable checkpoints** — every successfully migrated file is a real git
  commit, not a summary living only in the model's context.
- **Crash-safe resume** — kill the process mid-run, restart it, and it
  continues from the last verified checkpoint instead of starting over.

## Architecture

```
Frontend (React + Vite)  →  Backend (FastAPI agent loop)  →  Paritok proxy  →  Anthropic API
                                       ↓
                              target repo on disk
                              (read / edit / test / commit)
```

The agent loop plans a file list, then for each file: reads it, asks Claude
to migrate it, writes the result, runs its tests, and commits only if they
pass. All model traffic flows through Paritok (`ANTHROPIC_BASE_URL` points at
the local proxy), so compression happens transparently — the agent code
never has to manage context truncation itself.

## Getting started

### 1. Start Paritok

```bash
pip install "paritok[proxy]"
paritok up
```

Leave this running in its own terminal — it's a foreground proxy server.
Confirm it's up:

```bash
curl http://127.0.0.1:8080/health
```

> Using the hosted GPU server instead of self-hosting? Set `use_gpu_server:
> true` and your API key in `paritok.yaml` — see [Paritok's
> docs](https://github.com/Paritok-official/paritok-4b-v1#2-pick-a-backend--self-host-or-the-gpu-server).

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_BASE_URL=http://127.0.0.1:8080
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### 4. Run a migration

Click **Start** on the dashboard, or:

```bash
curl -X POST http://localhost:8000/run/start \
  -H "Content-Type: application/json" \
  -d '{"task": "migrate requests to httpx"}'
```

Watch the waypoint trail move through each file, tokens/cost update live
from Paritok's stats, and checkpoints land as real commits in `demo-repo/`.

To test crash-safe resume: kill the backend process mid-run, restart it, and
click **Resume** — it continues from the last completed file.

## Project structure

```
waypoint/
├── backend/            # FastAPI app + agent loop (plan / migrate / checkpoint / resume)
├── frontend/            # React + Vite dashboard
├── demo-repo/            # sample repo Waypoint migrates (requests → httpx), with tests
├── examples/sample-run/  # example stats + checkpoint log from a completed run
└── paritok.yaml           # Paritok proxy config
```

## Example output

See [`examples/sample-run/`](./examples/sample-run/) for a completed run's
`stats.json` and checkpoint log, so you can evaluate results without running
the agent yourself.

## Roadmap / not in this MVP

- Multi-repo and multi-agent orchestration
- Automatic PR creation against a remote (this demo commits locally)
- Support for migration targets beyond the demo task
- Multi-user / authenticated dashboard

## Built with Paritok

This project routes all agent-to-model traffic through
[Paritok](https://github.com/Paritok-official/paritok-4b-v1), an open-source
compression model trained specifically for coding-agent context. Every
number on the dashboard's savings chart comes from Paritok's own `/stats`
endpoint.

## License

Apache 2.0 — see [LICENSE](./LICENSE).