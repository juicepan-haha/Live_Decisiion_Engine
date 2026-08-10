from pathlib import Path

from live_decision_engine import pipeline
from live_decision_engine.pipeline import run_pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "session_mini"


class FakeClient:
    """available=True 的假 LLM 客户端：返回一个规则提取不到的事件。"""

    available = True

    def chat_json(self, system: str, user: str) -> dict | None:
        return {
            "events": [
                {"ts": 7.0, "type": "selling_point", "content": "面料很舒服", "confidence": 0.95}
            ]
        }


def _event_ids(out_dir: Path) -> list[str]:
    ids = []
    with (out_dir / "stages" / "03_events.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ids.append(line.split('"event_id":"')[1].split('"')[0])
    return ids


def test_run_pipeline_with_injected_client_uses_llm_path(tmp_path):
    result = run_pipeline(FIXTURE, llm=FakeClient(), out_dir=tmp_path)
    # LLM 路径生效：03_events 出现 e_llm_ 前缀事件
    assert any(eid.startswith("e_llm_") for eid in _event_ids(tmp_path))
    assert len(result["cards"]) > 0


def test_run_pipeline_llm_true_instantiates_client(monkeypatch, tmp_path):
    # llm=True 时应实例化 LLMClient 并把实例传给各层（而非把 bool 传下去）
    monkeypatch.setattr(pipeline, "LLMClient", lambda: FakeClient())
    run_pipeline(FIXTURE, llm=True, out_dir=tmp_path)
    assert any(eid.startswith("e_llm_") for eid in _event_ids(tmp_path))


def test_run_pipeline_llm_true_without_key_falls_back(monkeypatch, tmp_path, capsys):
    # 无 key 环境：不崩溃，stderr 警告，回退纯规则路径正常产出
    monkeypatch.delenv("LDE_LLM_API_KEY", raising=False)
    result = run_pipeline(FIXTURE, llm=True, out_dir=tmp_path)
    err = capsys.readouterr().err
    assert "LDE_LLM_API_KEY" in err or "openai" in err
    assert len(result["cards"]) > 0
    # 未走 LLM 路径
    assert not any(eid.startswith("e_llm_") for eid in _event_ids(tmp_path))
