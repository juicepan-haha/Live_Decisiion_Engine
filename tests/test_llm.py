import pytest

from live_decision_engine.event.extractor import extract_events
from live_decision_engine.llm import LLMClient
from live_decision_engine.schemas.stages import Segment


class FakeLLM:
    available = True

    def chat_json(self, system: str, user: str) -> dict | None:
        return {"events": [{"ts": 40.0, "type": "selling_point", "content": "面料是冰丝的", "confidence": 0.95}]}


class FailingLLM:
    available = True

    def chat_json(self, system: str, user: str) -> dict | None:
        return None


def test_llm_client_env_parsing(monkeypatch):
    monkeypatch.setenv("LDE_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LDE_LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LDE_LLM_MODEL", "deepseek-chat")
    client = LLMClient()
    assert client.api_key == "sk-test"
    assert client.base_url == "https://api.example.com/v1"
    assert client.model == "deepseek-chat"


def test_llm_client_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("LDE_LLM_API_KEY", raising=False)
    client = LLMClient()
    assert client.available is False


def test_enhance_events_merges_and_dedups():
    segs = [Segment(segment_id="s_001", ts_start=40.0, ts_end=50.0, text="这个面料是冰丝的。", line_refs=[0])]
    events = extract_events(segs, [], llm=FakeLLM())
    ev = next(e for e in events if e.type == "selling_point" and e.ts == 40.0)
    assert ev.confidence == 0.95  # LLM 0.95 > 规则 0.8，去重后保留 LLM


def test_llm_failure_falls_back_to_rules():
    segs = [Segment(segment_id="s_001", ts_start=40.0, ts_end=50.0, text="这个面料是冰丝的。", line_refs=[0])]
    events = extract_events(segs, [], llm=FailingLLM())
    assert any(e.type == "selling_point" for e in events)  # 规则结果仍在


def test_decision_llm_rewrites_script():
    from live_decision_engine.decision.engine import decide
    from live_decision_engine.schemas.inputs import Product
    from live_decision_engine.schemas.stages import LiveEvent

    class ScriptLLM:
        available = True

        def chat_json(self, system, user):
            return {"script": "姐妹们，这件连衣裙有 L 码，报身高体重我帮你选！"}

    products = [Product(product_id="p001", name="法式碎花连衣裙", price=129, stock=200, category="连衣裙")]
    events = [LiveEvent(event_id="e_0001", ts=100.0, type="user_question", content="这件有L码吗", confidence=0.9, source="chat")]
    cards = decide(events, products, llm=ScriptLLM())
    assert cards[0].script == "姐妹们，这件连衣裙有 L 码，报身高体重我帮你选！"


def test_validation_llm_judge_adjusts_score():
    from live_decision_engine.schemas.cards import ActionRef, DecisionCard, Quality, Trigger
    from live_decision_engine.validation.scorer import score_cards

    class JudgeLLM:
        available = True

        def chat_json(self, system, user):
            return {"score": 70}

    card = DecisionCard(
        card_id="c_0001", timestamp=100.0, stage="product_intro",
        action=ActionRef(name="size_question", category="size", goal="g"),
        trigger=Trigger(event_id="e_0001", segment_id="s_001", detail="d", rule_ref="decisions.yaml#rule_01"),
        reason="r", script="s", expected_goal="g", quality=Quality(score=60, flags=[]),
    )
    out = score_cards([card], llm=JudgeLLM())
    # 规则分 90（60+15+15），评委 70 → 平均 80
    assert out[0].quality.score == 80
