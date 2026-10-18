# Repository Guidelines

## Project Structure & Module Organization

`upload.py` is the primary CLI entry point; `config-generator.py` creates local configuration. Core Python modules live in `src/`, with tracker-specific adapters in `src/trackers/` and torrent-client integrations in `src/torrent_clients/`. The Flask-based interface is under `web_ui/`, with templates and JavaScript in `web_ui/templates/` and `web_ui/static/`. Helper/download scripts belong in `bin/`, documentation in `docs/`, and default configuration, templates, and release metadata in `data/`.

## Build, Test, and Development Commands

- `python3 -m venv .venv && source .venv/bin/activate` creates an isolated environment.
- `python -m pip install -r requirements.txt` installs runtime dependencies. Install Ruff, Pyright, and Bandit separately for contributor checks.
- `python config-generator.py` creates or updates the local `data/config.py`.
- `python upload.py -h` verifies the CLI and lists supported options.
- `python upload.py "/path/to/media" --webui 127.0.0.1:5000` starts the local Web UI.
- `ruff check .`, `pyright`, and `bandit -c bandit.yaml -r .` run lint, strict type, and security checks.
- `docker compose up -d` runs the containerized Web UI after paths and environment values are configured.

## Coding Style & Naming Conventions

Target Python 3.9 or newer. Use four-space indentation, snake_case for modules/functions/variables, PascalCase for classes, and uppercase tracker acronyms for adapter files (for example, `src/trackers/BHD.py`). Ruff controls import ordering and lint rules; its configured line length is 176. Preserve type annotations and satisfy Pyright's strict mode. Keep tracker-specific behavior in its adapter and shared behavior in `COMMON.py` or another focused `src/` module.

## Testing Guidelines

No automated test suite or coverage threshold is currently checked in. Before submitting, run all three static checks plus `python upload.py -h`. Exercise changed flows with non-sensitive sample media and avoid real uploads unless explicitly intended. If adding tests, place focused files under `tests/` and name them `test_<feature>.py`.

## Commit & Pull Request Guidelines

Recent history favors concise, imperative subjects, often Conventional Commit style: `fix(tvdb): don't rely on slug` or `feat(trackers/bjs): ...`. Keep each commit scoped to one change. PRs should explain the problem and solution, identify affected trackers or clients, list verification performed, link relevant issues, and include screenshots for Web UI changes. This codebase is in development freeze; prioritize critical fixes and new-site groundwork over minor enhancements.

## Security & Configuration

Never commit API keys, cookies, passwords, media, generated torrents, or `data/config.py`. Use `data/example-config.py` and `docs/example-config.md` as references, and redact logs and screenshots before sharing them.
