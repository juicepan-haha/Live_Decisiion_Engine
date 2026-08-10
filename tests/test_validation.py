from live_decision_engine.schemas.cards import ActionRef, DecisionCard, Quality, Trigger
from live_decision_engine.validation.scorer import score_cards


def _card(cid, stage, action_name, category, confidence=0.9, rule_ref="decisions.yaml#rule_01"):
    trigger = Trigger(
        event_id="e_0001" if confidence >= 0.7 else None,
        segment_id="s_001",
        detail="d",
        rule_ref=rule_ref,
    )
    return DecisionCard(
        card_id=cid,
        timestamp=100.0,
        stage=stage,
        action=ActionRef(name=action_name, category=category, goal="g"),
        trigger=trigger,
        reason="r",
        script="s",
        expected_goal="g",
        quality=Quality(score=60, flags=[]),
    )


def test_high_confidence_matching_stage_scores_high():
    card = _card("c_0001", "product_intro", "size_question", "size")  # 60+15+15=90
    out = score_cards([card])
    assert out[0].quality.score == 90
    assert out[0].quality.flags == []


def test_low_confidence_flagged():
    card = _card("c_0001", "product_intro", "size_question", "size", confidence=0.5)  # 60+(-10)+15=65
    out = score_cards([card])
    assert out[0].quality.score == 65
    assert "low_confidence" in out[0].quality.flags


def test_stage_mismatch_penalized():
    card = _card("c_0001", "start", "size_question", "size")  # size_question 不适配 start: 60+15-20=55 → 剔除
    out = score_cards([card])
    assert out == []


def test_fallback_flagged_not_discarded():
    # 真实兜底卡：event_id=None → confidence 0.5，rule_ref 含 fallback
    trigger = Trigger(event_id=None, segment_id=None, detail="阶段兜底", rule_ref="decisions.yaml#fallback")
    card = DecisionCard(
        card_id="c_0001", timestamp=100.0, stage="try_on",
        action=ActionRef(name="try_on", category="selling", goal="g"),
        trigger=trigger, reason="r", script="s", expected_goal="g",
        quality=Quality(score=60, flags=[]),
    )
    out = score_cards([card])
    # 60-10(low confidence)+15(stage 匹配 try_on∈[try_on])=65 → 保留，且带 fallback flag
    assert out[0].quality.score == 65
    assert "fallback" in out[0].quality.flags


def test_score_floor_60():
    card = _card("c_0001", "product_intro", "size_question", "size", confidence=0.5)  # 65 → 保留
    out = score_cards([card])
    assert len(out) == 1
