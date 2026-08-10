# Live Decision Engine

Turn one livestream session into a set of auditable decision cards.

Pipeline: `ingestion → cleaning → segmentation → event extraction → decision extraction → quality scoring`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

```bash
live-decision validate demo/session_001
live-decision run demo/session_001
# resume from a specific stage (01 cleaned / 02 segments / 03 events / 04 cards)
live-decision run demo/session_001 --from 03
```

Output: `demo/session_001/output/stages/*.jsonl` (per-stage artifacts) and `output/summary.txt`.

## Optional LLM enhancement

Rules run by default with zero external dependencies. Set these env vars to
upgrade event extraction, script rewriting and quality judging:

```bash
export LDE_LLM_API_KEY=sk-...
export LDE_LLM_BASE_URL=https://api.deepseek.com/v1
export LDE_LLM_MODEL=deepseek-chat
live-decision run demo/session_001 --llm
```

## Session data format

A session directory contains four files: `transcript.jsonl` (host speech),
`chat.jsonl` (audience messages), `products.json` (products on show) and
`metadata.json` (session meta). See `docs/architecture.md` for the schema.

## Tests

```bash
pytest -q
```

## License

MIT
