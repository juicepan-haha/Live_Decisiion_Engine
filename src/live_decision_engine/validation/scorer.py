from live_decision_engine.rules.loader import load_action_stages
from live_decision_engine.schemas.cards import DecisionCard, Quality

THRESHOLD = 60


def _confidence_of(card: DecisionCard) -> float:
    return 0.5 if card.trigger.event_id is None else 0.9


def score_cards(cards: list[DecisionCard], llm=None) -> list[DecisionCard]:
    action_stages = load_action_stages()
    out: list[DecisionCard] = []

    for card in cards:
        score = 60
        flags: list[str] = []

        conf = _confidence_of(card)
        if conf >= 0.85:
            score += 15
        elif conf >= 0.7:
            score += 5
        else:
            score -= 10
            flags.append("low_confidence")

        if card.stage in action_stages.get(card.action.name, []):
            score += 15
        else:
            score -= 20
            flags.append("stage_mismatch")

        if "fallback" in card.trigger.rule_ref:
            # 只标记不扣分：兜底卡本身置信低（0.5），再扣分会全部低于阈值
            flags.append("fallback")

        score = max(0, min(100, score))
        if score < THRESHOLD:
            continue
        out.append(
            card.model_copy(
                update={"quality": Quality(score=score, flags=flags)}
            )
        )

    if llm is not None and getattr(llm, "available", False):
        out = _judge_adjust(out, llm)
    return out


def _judge_adjust(cards, llm) -> list[DecisionCard]:
    _system = "你是直播运营质量评委。给决策卡打 0-100 分，只输出 JSON：{\"score\": 0-100}。"
    adjusted = []
    for card in cards:
        payload = llm.chat_json(
            _system,
            f"阶段: {card.stage}\n动作: {card.action.name}\n理由: {card.reason}\n话术: {card.script}",
        )
        if payload and isinstance(payload.get("score"), (int, float)):
            llm_score = int(payload["score"])
            avg = round((card.quality.score + llm_score) / 2)
            card = card.model_copy(
                update={"quality": card.quality.model_copy(update={"score": avg})}
            )
        adjusted.append(card)
    return adjusted
