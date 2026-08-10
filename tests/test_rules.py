from live_decision_engine.rules.loader import (
    load_action_stages,
    load_actions,
    load_patterns,
    load_rules,
)


def test_patterns_loaded():
    patterns = load_patterns()
    assert len(patterns) >= 8
    assert all({"id", "source", "regex", "event_type", "confidence"} <= set(p) for p in patterns)


def test_rules_and_fallback():
    rules, fallback, stage_map = load_rules()
    assert len(rules) >= 8
    assert fallback["conversion"] == ["scarcity", "no_conversion", "last_call", "coupon_push", "size_question"]
    assert stage_map["product_intro"] == "product_intro"


def test_actions_loaded():
    actions = load_actions()
    assert len(actions) == 14
    assert set(actions["size_question"].keys()) == {"category", "goal", "trigger", "template"}
    assert "{product}" in actions["scarcity"]["template"]


def test_action_stages():
    stages = load_action_stages()
    assert "size_question" in stages
    assert "conversion" in stages["scarcity"]
