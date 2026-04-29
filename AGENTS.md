# AGENTS.md — a2a repository conventions

This file applies to all contributors and autonomous agents working in this repository.
It mirrors the rules in `.cursor/rules/` for agents that do not load Cursor rule files.

---

## Python style

- **Runtime:** Python 3.12+. Use `from __future__ import annotations` in every module.
- **Package manager:** `uv` exclusively. Never use pip, poetry, or requirements.txt.
- **Linting / formatting:** `ruff` only (replaces black, isort, flake8). Run `uv run ruff check . && uv run ruff format .` before committing.
- **Type checking:** `mypy --strict`. All public functions and methods must have full type annotations.
- **DTOs:** Pydantic v2 for every structured data object. No plain dicts crossing module boundaries.
- **Config / secrets:** pydantic-settings with `YamlConfigSettingsSource`. Settings come from `env.yaml` (tracked example at `env.yaml.example`) and `.env` (never committed). Precedence: `init > env vars > .env > env.yaml`.
- **Logging:** `structlog` with JSON output. No bare `print()` calls in src/ or scripts/.
- **LLM calls:** Every model call goes through `src/a2a/llm.py`. No direct provider SDK calls anywhere else. Every call records tokens, latency, cost, model, and a prompt hash.
- **Randomness:** Always inject a `random.Random` seeded from config. No `random.random()` or `random.seed()` at module level.
- **Tests:** `pytest` with `pytest-cov`. Coverage gate ≥80% on `src/a2a/runner/` and `src/a2a/llm.py`.

## Commits

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`, `perf:`.
- **Never** mention "Cursor", "Claude", "Codex", "Anthropic", "GPT", or any AI tool as co-author or in commit trailers. Commits are authored by the human developer.
- Keep commit messages in the imperative mood, present tense: "add catalog fetcher" not "added catalog fetcher".
- Reference an experiment slug or ticket when changing experiment config: `chore(experiments): update saas-subscription config for v0.2`.

## Security

- **Never** commit `.env`, `env.yaml`, `*.key`, `*.pem`, or any credential file.
- **Never** commit anything under `output/` (generated artefacts are in `experiments/<slug>/` and committed selectively).
- `.cursor/` is in `.gitignore` and must never be staged or committed.
- Run `gitleaks detect --no-git` before pushing to a shared branch.

## File and module layout

```
src/a2a/
  config.py        — AppConfig (pydantic-settings + yaml)
  llm.py           — LLM wrapper (litellm), LLMRecord dataclass
  catalog/         — product ingestion → CatalogEntry
  buyer/           — BuyingAgent, Mandate, archetypes
  seller/          — SellingAgent, Funnel, variants
  protocols/       — AP2, MCP, A2A, x402, UCP samples
  runner/          — Orchestrator, JSONL ledger, autonomy dial
  reporting/       — HTML report generator
```

## Experiment results

Committed under `experiments/<YYYY-MM-slug>/`:
- `config.yaml` — exact parameters used
- `results.jsonl` — one line per dyad (the ledger)
- `report.html` — self-contained HTML report
- `README.md` — run summary, key findings, how to reproduce

Do **not** commit raw LLM prompt/response dumps unless they are anonymised.

## Licensing

- Code (`src/`, `scripts/`, `tests/`) → Apache-2.0
- Content (`experiments/`, `site/`, `README.md`, `NOTICE`) → CC-BY-4.0
- See `NOTICE` for the preferred citation.
