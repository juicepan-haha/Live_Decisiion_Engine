# AGENTS.md

Turn one livestream session into auditable decision cards. Chinese livestream e-commerce domain: all session data, CLI output, and YAML rules are in Chinese — keep new data/rules/scripts in Chinese.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"   # setup
.venv/bin/pip install -e ".[llm]"                            # optional: openai for --llm
.venv/bin/pytest -q                                          # tests (testpaths=tests)
.venv/bin/live-decision validate <session_dir>               # input-only check
.venv/bin/live-decision run <session_dir> [--from 01|02|03|04] [--llm]
```

- The existing `.venv` in this repo is broken (pytest shebang points to a misspelled path, package not installed). Recreate it with the setup command above; do not try to reuse it.
- `scripts/build_demo_data.py --source-vtt <file> --out <session_dir> --max-minutes N` builds a new session dir from a VTT transcript.

## Pipeline architecture

`ingestion → cleaning → segmentation → event → decision → validation`, stages write to `<session>/output/stages/{01_cleaned,02_segments,03_events,04_cards}.jsonl` (pydantic models in `schemas/`).

- Layers communicate **only via files** — no shared state between stages. Each stage is idempotent and overwrites its own file.
- `--from <stage>` resumes at that stage but requires earlier stage files to already exist on disk.
- A session dir is exactly four input files: `transcript.jsonl`, `chat.jsonl`, `products.json`, `metadata.json`. Schema in `docs/architecture.md`.
- Final cards are filtered by `THRESHOLD = 60` in `validation/scorer.py` (cards below are dropped).

## Rules are externalized YAML

`src/live_decision_engine/rules/` — `patterns.yaml` (event patterns), `decisions.yaml` (rules/fallback/stage_map), `actions.yaml` (14 actions). Loaded via `rules/loader.py` with `lru_cache`: YAML edits are picked up immediately with an editable install, but rule loaders are cached per process (clear cache or use a fresh process when tests mutate rules). These YAML files are packaged as package data — keep them in `rules/`; `tests/test_rules.py::test_yaml_files_readable_as_package_data` guards against packaging regressions.

## LLM enhancement (optional)

Rules run by default with zero dependencies. `--llm` enables enhancement via OpenAI-compatible client (`llm.py`): env vars `LDE_LLM_API_KEY`, `LDE_LLM_BASE_URL`, `LDE_LLM_MODEL` (default `deepseek-chat`). Without key/openai it warns and silently falls back to pure rules.

The LLM client is duck-typed: `pipeline._resolve_llm` accepts any object with an `available` attribute and `chat_json()` method. Tests use fakes (`tests/test_llm.py`, `tests/test_pipeline_llm.py`) — no network needed; run the full suite offline.

## Notes

- `database.db*` at repo root are untracked stray files, referenced by no code — don't commit them.
- `demo/session_001/output/` is gitignored.
- Integration tests use `tests/fixtures/session_mini/` (synthetic data, not in demo/).
