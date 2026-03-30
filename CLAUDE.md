# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also: `backend/CLAUDE.md` (detailed backend architecture) and `frontend/CLAUDE.md` (frontend patterns).

## What is DeerFlow

DeerFlow is a full-stack AI "super agent harness" — a LangGraph-based agent system with sandbox execution, persistent memory, subagent delegation, MCP integration, and IM channel bridges (Feishu, Slack, Telegram).

## Commands

**From project root:**
```bash
make check           # Verify system prerequisites
make install         # Install all deps (backend uv sync + frontend pnpm install)
make config          # First-time config generation (aborts if config.yaml exists)
make config-upgrade  # Merge new fields from config.example.yaml
make dev             # Start all services (LangGraph:2024 + Gateway:8001 + Frontend:3000 + Nginx:2026)
make stop            # Stop all services
```

**Backend (from `backend/`):**
```bash
make lint            # ruff check + format
make test            # pytest (CI-equivalent: ~277 tests)
make dev             # LangGraph server only
make gateway         # Gateway API only
```

Run a single test:
```bash
PYTHONPATH=. uv run pytest tests/test_<feature>.py -v
```

**Frontend (from `frontend/`):**
```bash
pnpm lint            # ESLint
pnpm typecheck       # tsc --noEmit
BETTER_AUTH_SECRET=local-dev-secret pnpm build   # Production build (requires this env var)
pnpm dev             # Dev server with Turbopack
```

Note: `pnpm check` is broken (invalid directory resolution). Use `pnpm lint && pnpm typecheck` instead.

## Pre-Checkin Validation

Always run before PRs (this is what CI enforces):
```bash
cd backend && make lint && make test
cd frontend && pnpm lint && pnpm typecheck
```

## Architecture

```
Browser → Nginx (:2026) ─┬─ /api/langgraph/* → LangGraph Server (:2024)
                          ├─ /api/*           → Gateway API (:8001)
                          └─ /*               → Frontend (:3000)
```

### Backend Two-Layer Split

- **Harness** (`backend/packages/harness/deerflow/`): Publishable agent framework. Import as `deerflow.*`.
- **App** (`backend/app/`): Gateway API + IM channels. Import as `app.*`.
- **Rule**: App may import deerflow; deerflow must never import app. Enforced by `test_harness_boundary.py` in CI.

### Agent Pipeline

Entry point: `deerflow.agents:make_lead_agent` (registered in `langgraph.json`).

The lead agent runs through a 12-middleware chain in strict order:
ThreadData → Uploads → Sandbox → DanglingToolCall → Guardrail → Summarization → TodoList → Title → Memory → ViewImage → SubagentLimit → Clarification

### Key Subsystems

- **Sandbox**: Virtual path system (`/mnt/user-data/`, `/mnt/skills/` → physical paths). Local or Docker providers.
- **Subagents**: Dual thread pool, max 3 concurrent, 15min timeout. Built-ins: `general-purpose`, `bash`.
- **Memory**: LLM-based fact extraction, debounced queue, stored in `backend/.deer-flow/memory.json`.
- **MCP**: Multi-server with lazy loading, mtime-based cache invalidation, OAuth support.
- **Skills**: `SKILL.md` files in `skills/{public,custom}/`, managed via `extensions_config.json`.
- **Config**: `config.yaml` (main app config) + `extensions_config.json` (MCP + skills). Both support hot-reload via mtime detection. `$VAR` syntax resolves environment variables.

### Frontend

Next.js 16 + React 19 + TypeScript 5.8 + Tailwind 4 + pnpm.

Core data flow: User input → thread hooks → LangGraph SDK streaming → TanStack Query state → component rendering.

`src/components/ui/` and `src/components/ai-elements/` are auto-generated from registries — do not manually edit.

## Toolchain Requirements

- Python >= 3.12, `uv` package manager
- Node.js >= 22, pnpm 10.26.2+
- nginx (for unified `make dev` endpoint)

## Configuration

- Copy `config.example.yaml` → `config.yaml` in project root
- Copy `extensions_config.example.json` → `extensions_config.json` in project root
- Copy `.env.example` → `.env` for API keys
- Config search order: explicit path → env var → `backend/` dir → parent (root) dir

## Code Style

- **Python**: ruff, 240-char line length, Python 3.12+ type hints, double quotes
- **TypeScript**: ESLint with enforced import ordering, `@/*` path alias to `src/*`, inline type imports (`import { type Foo }`)

## Documentation Update Policy

Update `README.md` and the relevant `CLAUDE.md` after code changes that affect architecture, commands, or developer workflows.
