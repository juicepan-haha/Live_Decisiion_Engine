from pathlib import Path

import pytest

from live_decision_engine.pipeline import run_pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "session_mini"


def test_full_pipeline_writes_stages(tmp_path):
    result = run_pipeline(FIXTURE, out_dir=tmp_path)
    stages = tmp_path / "stages"
    assert (stages / "01_cleaned.jsonl").exists()
    assert (stages / "02_segments.jsonl").exists()
    assert (stages / "03_events.jsonl").exists()
    assert (stages / "04_cards.jsonl").exists()
    assert (tmp_path / "summary.txt").exists()
    assert isinstance(result["cards"], list)
    assert len(result["cards"]) > 0  # 空列表会让下面的逐卡断言恒真
    for card in result["cards"]:
        assert card.quality.score >= 60


def test_from_stage_02(tmp_path):
    first = run_pipeline(FIXTURE, out_dir=tmp_path)
    again = run_pipeline(FIXTURE, from_stage="02", out_dir=tmp_path)
    # 02 之后确定性重跑，卡片应一致（幂等）
    assert [c.card_id for c in again["cards"]] == [c.card_id for c in first["cards"]]
    for name in ("02_segments.jsonl", "03_events.jsonl", "04_cards.jsonl"):
        assert (tmp_path / "stages" / name).exists()
    assert (tmp_path / "summary.txt").exists()


def test_from_stage_03(tmp_path):
    run_pipeline(FIXTURE, out_dir=tmp_path)
    first = run_pipeline(FIXTURE, out_dir=tmp_path)
    again = run_pipeline(FIXTURE, from_stage="03", out_dir=tmp_path)
    # 03 之后逻辑相同，两次跑出的卡应一致（幂等）
    assert [c.card_id for c in again["cards"]] == [c.card_id for c in first["cards"]]


def test_from_stage_04(tmp_path):
    first = run_pipeline(FIXTURE, out_dir=tmp_path)
    again = run_pipeline(FIXTURE, from_stage="04", out_dir=tmp_path)
    # 04 重跑 decision+scoring，卡片应一致（幂等）
    assert [c.card_id for c in again["cards"]] == [c.card_id for c in first["cards"]]
    assert (tmp_path / "stages" / "04_cards.jsonl").exists()
    assert (tmp_path / "summary.txt").exists()


def test_invalid_from_stage(tmp_path):
    with pytest.raises(ValueError):
        run_pipeline(FIXTURE, from_stage="99", out_dir=tmp_path)
