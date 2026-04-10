# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a single-service **Streamlit** Python web application ("Coreo-Flow / Arbeitszeitverwaltung") for German-language workforce time-tracking. It uses an **external Supabase** (hosted PostgreSQL) backend for all data persistence.

### Running the app

```bash
streamlit run app.py --server.port 8501 --server.headless true
```

The app requires three Supabase environment variables to connect to the database: `SUPABASE_URL`, `SUPABASE_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`. Without them, the app will crash on startup with `RuntimeError: Fehlende Umgebungsvariable`. For UI-only testing you can set dummy values in a `.env` file (already gitignored); for full end-to-end testing, real Supabase credentials are required.

The app loads `.env` via `python-dotenv` so environment variables can be placed in `/workspace/.env`.

### Running tests

```bash
python3 -m pytest tests/ -v
```

All 21 tests are mock-based and do **not** require a Supabase connection.

### Linting

```bash
ruff check .
```

There is no project-level linter config (`pyproject.toml`, `.flake8`, etc.) — ruff runs with defaults. The existing codebase has ~102 lint findings (unused imports, semicolons, f-string issues); these are pre-existing.

### Kiosk mode (optional)

An alternative entry point for a dedicated clock-in terminal:

```bash
streamlit run kiosk_stempeluhr.py
```

### Key caveats

- Python 3.12 is used in the Cloud VM (the README says 3.11+ which is satisfied).
- `pytest` and `ruff` are dev-only dependencies not listed in `requirements.txt`; the update script installs them.
- There is no build step — Streamlit apps run directly from source.
