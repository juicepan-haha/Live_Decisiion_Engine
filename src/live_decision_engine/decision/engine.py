import re

from live_decision_engine.decision.state import SessionState
from live_decision_engine.rules.loader import load_actions, load_rules
from live_decision_engine.schemas.cards import ActionRef, DecisionCard, Trigger
from live_decision_engine.schemas.inputs import Product
from live_decision_engine.schemas.stages import LiveEvent

_DEDUP_WINDOW = 1800.0  # 30 分钟


def fill_template(template: str, product: Product | None) -> str:
    if product is None:
        return template
    price = str(int(product.price)) if product.price == int(product.price) else str(product.price)
    return (
        template
        .replace("{product}", product.name)
        .replace("{price}", price)
        .replace("{stock}", str(product.stock))
    )


def decide(
    events: list[LiveEvent],
    products: list[Product],
    llm=None,
) -> list[DecisionCard]:
    if not products:
        raise ValueError("products.json 为空：决策卡话术依赖商品信息，需至少一个商品")
    rules, fallback, stage_map = load_rules()
    actions = load_actions()
    state = SessionState(products)

    cards: list[DecisionCard] = []
    seq = 0

    for event in events:
        state.advance(event, stage_map)
        matched = _match_rule(rules, event)

        if matched is not None:
            action_name = matched["action"]
            if _within_dedup(state, action_name, event.ts):
                continue
            seq += 1
            cards.append(_build_card(seq, event, state, matched, actions))
        else:
            for action_name in fallback.get(state.stage, []):
                if _within_dedup(state, action_name, event.ts):
                    continue
                seq += 1
                cards.append(_build_fallback_card(seq, event, state, action_name, actions))
                break

    if llm is not None and getattr(llm, "available", False):
        cards = _rewrite_scripts(cards, llm)
    return cards


def _match_rule(rules: list[dict], event: LiveEvent) -> dict | None:
    for rule in sorted(rules, key=lambda r: -r["priority"]):
        when = rule["when"]
        if when["event_type"] != event.type:
            continue
        if "keyword" in when and not re.search(when["keyword"], event.content):
            continue
        return rule
    return None


def _within_dedup(state: SessionState, action_name: str, ts: float) -> bool:
    last = state.last_card_ts.get(action_name)
    return last is not None and ts - last < _DEDUP_WINDOW


def _build_card(seq, event, state, rule, actions) -> DecisionCard:
    action_name = rule["action"]
    action = actions[action_name]
    state.last_card_ts[action_name] = event.ts
    return DecisionCard(
        card_id=f"c_{seq:04d}",
        timestamp=event.ts,
        stage=state.stage,
        action=ActionRef(name=action_name, category=action["category"], goal=action["goal"]),
        trigger=Trigger(
            event_id=event.event_id,
            segment_id=event.segment_ref,
            detail=rule["detail"],
            rule_ref=f"decisions.yaml#{rule['id']}",
        ),
        reason=rule["detail"],
        script=fill_template(action["template"], state.current_product),
        expected_goal=action["goal"],
        quality={"score": 60, "flags": []},  # 占位，Task 9 评分
    )


def _build_fallback_card(seq, event, state, action_name, actions) -> DecisionCard:
    action = actions[action_name]
    state.last_card_ts[action_name] = event.ts
    return DecisionCard(
        card_id=f"c_{seq:04d}",
        timestamp=event.ts,
        stage=state.stage,
        action=ActionRef(name=action_name, category=action["category"], goal=action["goal"]),
        trigger=Trigger(
            event_id=None, segment_id=None,
            detail="阶段兜底", rule_ref="decisions.yaml#fallback",
        ),
        reason=f"阶段兜底（stage={state.stage}）",
        script=fill_template(action["template"], state.current_product),
        expected_goal=action["goal"],
        quality={"score": 60, "flags": []},
    )


def _rewrite_scripts(cards, llm) -> list[DecisionCard]:
    _system = "你是直播间运营。把话术改写得更自然口语，保留原有意图，只输出 JSON：{\"script\": \"...\"}。"
    out = []
    for card in cards:
        payload = llm.chat_json(_system, f"当前阶段: {card.stage}\n原话术: {card.script}")
        if payload and payload.get("script"):
            card = card.model_copy(update={"script": payload["script"]})
        out.append(card)
    return out
