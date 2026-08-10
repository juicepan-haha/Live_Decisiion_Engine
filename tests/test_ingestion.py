from pathlib import Path

import pytest

from live_decision_engine.ingestion.adapter import (
    IngestionError,
    load_session,
    validate_session,
)

FIXTURE = Path(__file__).parent / "fixtures" / "session_mini"


def test_validate_ok():
    assert validate_session(FIXTURE) == []


def test_load_session_ok():
    data = load_session(FIXTURE)
    assert len(data.transcript) == 2
    assert len(data.chat) == 2
    assert data.products[0].name == "法式碎花连衣裙"
    assert data.metadata is not None
    assert data.metadata.session_id == "session_mini"


def test_validate_missing_file(tmp_path):
    errs = validate_session(tmp_path)
    assert any("transcript.jsonl" in e for e in errs)


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(IngestionError):
        load_session(tmp_path)


def test_validate_bad_line(tmp_path):
    (tmp_path / "products.json").write_text("[]", encoding="utf-8")
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "chat.jsonl").write_text("not json\n", encoding="utf-8")
    (tmp_path / "transcript.jsonl").write_text(
        '{"ts_start": 0.0, "ts_end": 1.0, "text": "ok"}\n', encoding="utf-8"
    )
    errs = validate_session(tmp_path)
    assert any("chat.jsonl:1" in e for e in errs)
