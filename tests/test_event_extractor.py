from live_decision_engine.event.extractor import extract_events
from live_decision_engine.schemas.inputs import ChatLine
from live_decision_engine.schemas.stages import Segment


def test_segment_events():
    segs = [
        Segment(segment_id="s_001", ts_start=10.0, ts_end=20.0, text="今天给大家介绍这款裙子，面料很好。", line_refs=[0]),
        Segment(segment_id="s_002", ts_start=30.0, ts_end=40.0, text="最后50件了，拼手速！", line_refs=[1]),
    ]
    events = extract_events(segs, [])
    types = {e.type for e in events}
    assert "product_intro" in types
    assert "selling_point" in types
    assert "scarcity" in types
    assert all(e.source == "segment" for e in events)
    assert events == sorted(events, key=lambda e: e.ts)


def test_chat_events():
    chats = [
        ChatLine(ts=5.0, user="u1", text="这件有L码吗"),
        ChatLine(ts=8.0, user="u2", text="多少钱"),
    ]
    events = extract_events([], chats)
    assert len(events) == 2
    assert all(e.source == "chat" for e in events)
    assert all(e.confidence >= 0.8 for e in events)


def test_no_match_no_events():
    segs = [Segment(segment_id="s_001", ts_start=0.0, ts_end=5.0, text="天气不错。", line_refs=[0])]
    assert extract_events(segs, []) == []


def test_llm_param_accepted():
    segs = [Segment(segment_id="s_001", ts_start=0.0, ts_end=5.0, text="天气不错。", line_refs=[0])]
    assert extract_events(segs, [], llm=object()) == []
