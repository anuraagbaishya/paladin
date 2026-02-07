# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paladin is a security vulnerability scanning platform that fetches GitHub Security Advisories (GHSAs), runs Semgrep static analysis on repositories, and provides a web UI for reviewing findings. It optionally integrates Google Gemini for AI-powered code review of findings.

## Build & Run Commands

Requires `toml-cli` (`pip install toml-cli`) for Makefile config parsing.

```bash
# Setup
cp config.toml.sample config.toml  # then edit with your paths/tokens

# Docker (primary workflow)
make build       # Build Docker image
make up          # Start containers (set NO_MONGO=1 to skip MongoDB container)
make down        # Stop all containers
make rebuild     # Rebuild without cache and restart
make logs        # Tail paladin logs
make shell       # Shell into paladin container

# Frontend development
cd frontend && npm run dev      # Vite dev server
cd frontend && npm run build    # Build to ../static/js/
cd frontend && npm run lint     # ESLint

# Python linting (pre-commit hooks)
ruff check --fix .   # Linter
black .              # Formatter
```

## Architecture

**Backend (Python 3.13+ / Flask):** `app.py` is the entry point. Scan and refresh operations run in daemon threads; the frontend polls `/api/job_status/<job_id>` until completion.

**Frontend (React 19 / Vite):** SPA with two routes — `/` (IndexPage: GHSA reports list) and `/scan/:owner/:repo/:id` (SarifPage: findings viewer). Built assets go to `static/js/`.

**Data flow:**
1. **Refresher** (`refresher/`) fetches GHSAs via GitHub REST+GraphQL APIs → stores `vuln_reports` in MongoDB
2. **Scanner** (`scanner/scan.py`) clones repo → runs Semgrep → processes SARIF output (`scanner/sarif_utils.py`) → stores `scan_results` in MongoDB
3. **AI Review** (`scanner/gemini_ops.py`) sends finding + source context to Gemini → stores structured verdict back in MongoDB

**Key modules:**
- `models/` — Pydantic models (`data_models.py`), API response dataclasses (`response_models.py`), enums (`enums.py`)
- `utils/config.py` — TOML config loader with strict validation; app exits on invalid config
- `utils/mongo_utils.py` — All MongoDB operations (collections: `vuln_reports`, `scan_results`, `scan_jobs`, `scan_metadata`)

## Configuration

`config.toml` sections:
- `[paths]` — `semgrep_rules_dir`, `clone_base_dir` (required)
- `[deployment]` — `host`, `port`, `workers` (required)
- `[tokens]` — `github_token`, `gemini_api_key` (optional; needed for refresh/AI review)
- `[settings]` — Language exclusions, rule suppressions, Gemini model
- `[mongo]` — Database host/port (defaults: localhost:27017)

## Code Conventions

- **Python formatting:** Black + Ruff (configured in `.pre-commit-config.yaml`)
- **Python patterns:** Pydantic BaseModel for DB documents, dataclasses with `to_dict()` for API responses, type hints throughout
- **Frontend patterns:** Functional components with hooks, native fetch API (no axios), CSS in global `styles.css`
- **SARIF fingerprinting:** SHA256 of rule_id + code snippet; used for suppression tracking across re-scans
- **Path safety:** File viewer validates paths within `clone_base_dir` using `os.path.commonpath`
