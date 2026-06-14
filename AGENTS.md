# AGENTS.md — datagate-mcp

> Repo-specific Codex guidance. Global behavioral directives (outcome-driven, anti-exploration,
> batch-reads) live in ~/.codex/AGENTS.md and apply on top of this.

## What this is
MCP server + Click CLI for the DataGate (dgportal.net) billing platform — customers, invoices,
products, agreements, sites, payments. MCP tools are read-only; CLI does full CRUD.

## Stack
Python ≥3.10 · hatchling build · httpx · Click (CLI) · FastMCP (`mcp[cli]`) · rich. Distributed on
PyPI (`pip install datagate-mcp` / `uvx datagate-mcp`).

## Verify — run after every change (mandatory)
```bash
# no automated checks configured in this repo (no test suite, no ruff/mypy config)
# smoke-check imports compile after editing:
python -c "import datagate_mcp.client, datagate_mcp.server, datagate_mcp.cli"
```

## Conventions
- All CLI write ops require `--confirm`. Payments are IRREVERSIBLE (void only via the DataGate portal).
- Client auto-paces to the API limits (60/min, 5000/day) — don't bypass the pacing.
- Config via env: `DATAGATE_API_KEY`, `DATAGATE_CLIENT_ID` (optional `DATAGATE_BASE_URL`). Never hardcode.

## Where things live
- `src/datagate_mcp/`: `client.py` (HTTP + rate-limit pacing), `server.py` (MCP tools), `cli.py` (Click CRUD).
- `pyproject.toml`: build config + `datagate` / `datagate-mcp` entry points.
