import re

from live_decision_engine.rules.loader import load_patterns
from live_decision_engine.schemas.inputs import ChatLine
from live_decision_engine.schemas.stages import LiveEvent, Segment


def extract_events(
    segments: list[Segment],
    chat: list[ChatLine],
    llm=None,
) -> list[LiveEvent]:
    events: list[LiveEvent] = []
    seq = 0

    for pattern in load_patterns():
        if pattern["source"] != "segment":
            continue
        rx = re.compile(pattern["regex"])
        for seg in segments:
            m = rx.search(seg.text)
            if not m:
                continue
            seq += 1
            events.append(
                LiveEvent(
                    event_id=f"e_{seq:04d}",
                    ts=seg.ts_start,
                    type=pattern["event_type"],
                    content=seg.text[max(0, m.start() - 15): m.end() + 15],
                    confidence=pattern["confidence"],
                    source="segment",
                    segment_ref=seg.segment_id,
                )
            )

    for pattern in load_patterns():
        if pattern["source"] != "chat":
            continue
        rx = re.compile(pattern["regex"])
        for line in chat:
            m = rx.search(line.text)
            if not m:
                continue
            seq += 1
            events.append(
                LiveEvent(
                    event_id=f"e_{seq:04d}",
                    ts=line.ts,
                    type=pattern["event_type"],
                    content=line.text,
                    confidence=pattern["confidence"],
                    source="chat",
                )
            )

    if llm is not None and getattr(llm, "available", False):
        from live_decision_engine.event.llm_extractor import enhance_events
        events = enhance_events(events, segments, llm)

    return sorted(events, key=lambda e: e.ts)
