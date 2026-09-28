from live_decision_engine.schemas.stages import LiveEvent, Segment

_SYSTEM = (
    "你是直播运营分析器。从直播转录文本中提取结构化事件，只输出 JSON："
    '{"events": [{"ts": 秒, "type": "类型", "content": "原文片段", "confidence": 0-1}]}。'
    "类型只能是: user_question, product_intro, selling_point, promotion, try_on, "
    "interaction_prompt, scarcity, conversion_call, price_mention。"
)

_BATCH = 5


def _locate_segment(segments: list[Segment], ts: float) -> str | None:
    best: str | None = None
    best_gap = float("inf")
    for seg in segments:
        if seg.ts_start <= ts <= seg.ts_end:
            return seg.segment_id
        gap = min(abs(ts - seg.ts_start), abs(ts - seg.ts_end))
        if gap < best_gap:
            best, best_gap = seg.segment_id, gap
    return best


def enhance_events(
    events: list[LiveEvent],
    segments: list[Segment],
    llm,
) -> list[LiveEvent]:
    if llm is None or not getattr(llm, "available", False):
        return events

    for i in range(0, len(segments), _BATCH):
        batch = segments[i:i + _BATCH]
        text = "\n".join(f"[{s.ts_start:.1f}s] {s.text}" for s in batch)
        payload = llm.chat_json(_SYSTEM, f"转录文本:\n{text}")
        if not payload or "events" not in payload:
            continue
        for raw in payload["events"]:
            try:
                cand = LiveEvent(
                    event_id=f"e_llm_{i}_{raw.get('ts', 0)}",
                    ts=float(raw["ts"]),
                    type=raw["type"],
                    content=str(raw["content"]),
                    confidence=float(raw["confidence"]),
                    source="segment",
                    segment_ref=_locate_segment(segments, float(raw["ts"])),
                )
            except Exception:
                continue
            # (ts, type) 去重，取置信度高者
            replaced = False
            for j, existing in enumerate(events):
                if abs(existing.ts - cand.ts) < 1.0 and existing.type == cand.type:
                    if cand.confidence > existing.confidence:
                        events[j] = cand
                    replaced = True
                    break
            if not replaced:
                events.append(cand)

    return sorted(events, key=lambda e: e.ts)
