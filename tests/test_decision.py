from live_decision_engine.decision.engine import decide
from live_decision_engine.decision.state import SessionState
from live_decision_engine.schemas.inputs import Product
from live_decision_engine.schemas.stages import LiveEvent

import pytest


PRODUCTS = [
    Product(product_id="p001", name="法式碎花连衣裙", price=129, stock=200, category="连衣裙"),
]


def _evt(ts, etype, content, eid="e_x"):
    return LiveEvent(event_id=eid, ts=ts, type=etype, content=content, confidence=0.9, source="chat")


def test_user_question_size_produces_card():
    events = [_evt(100.0, "user_question", "这件有L码吗", "e_0001")]
    cards = decide(events, PRODUCTS)
    assert len(cards) == 1
    card = cards[0]
    assert card.action.name == "size_question"
    assert card.action.category == "size"
    assert card.trigger.rule_ref == "decisions.yaml#rule_01"
    assert "连衣裙" in card.script  # {product} 已填充
    assert card.trigger.event_id == "e_0001"
    assert card.timestamp == 100.0


def test_price_question_maps_to_comparison():
    events = [_evt(100.0, "user_question", "多少钱", "e_0001")]
    cards = decide(events, PRODUCTS)
    assert cards[0].action.name == "comparison"
    assert "129" in cards[0].script  # {price} 已填充


def test_dedup_window_skips_repeat():
    events = [
        _evt(100.0, "user_question", "这件有L码吗", "e_0001"),
        _evt(120.0, "user_question", "有M码吗", "e_0002"),
    ]
    cards = decide(events, PRODUCTS)
    assert len(cards) == 1  # 20 秒内同 action 去重


def test_dedup_expires_after_30min():
    events = [
        _evt(100.0, "user_question", "这件有L码吗", "e_0001"),
        _evt(2000.0, "user_question", "有M码吗", "e_0002"),
    ]
    cards = decide(events, PRODUCTS)
    assert len(cards) == 2


def test_stage_advance():
    state = SessionState(PRODUCTS)
    stage_map = {"product_intro": "product_intro"}
    state.advance(_evt(10.0, "product_intro", "介绍", "e_0001"), stage_map)
    assert state.stage == "product_intro"


def test_fallback_after_silence():
    # try_on 事件类型无任何规则命中 → 触发阶段兜底
    events = [_evt(100.0, "try_on", "主播试穿展示", "e_0001")]
    cards = decide(events, PRODUCTS)
    assert cards[0].trigger.rule_ref == "decisions.yaml#fallback"
    assert cards[0].action.name == "try_on"  # stage 推进到 try_on 后取 fallback[try_on] 首个候选


def test_empty_products_raises():
    events = [_evt(100.0, "user_question", "多少钱", "e_0001")]
    with pytest.raises(ValueError, match="products.json 为空"):
        decide(events, [])


def test_price_question_card_survives_scoring():
    # 回归：comparison 的 action_stages 必须覆盖 product_intro，否则价格询问卡被阈值静默过滤
    from live_decision_engine.validation.scorer import score_cards

    events = [_evt(100.0, "user_question", "多少钱", "e_0001")]
    cards = decide(events, PRODUCTS)
    scored = score_cards(cards)
    assert len(scored) == 1
    assert scored[0].action.name == "comparison"
    assert scored[0].quality.score == 90  # 60+15(conf)+15(阶段匹配)


def test_interaction_prompt_card_survives_scoring():
    from live_decision_engine.validation.scorer import score_cards

    events = [_evt(100.0, "interaction_prompt", "扣1支持", "e_0001")]
    cards = decide(events, PRODUCTS)
    scored = score_cards(cards)
    assert len(scored) == 1
    assert scored[0].action.name == "question_prompt"
