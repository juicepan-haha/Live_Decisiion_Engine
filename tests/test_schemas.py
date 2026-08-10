import pytest
from pydantic import ValidationError

from live_decision_engine.schemas.cards import STAGES, DecisionCard
from live_decision_engine.schemas.inputs import ChatLine, Product, TranscriptLine
from live_decision_engine.schemas.stages import EVENT_TYPES, LiveEvent, Segment


def test_transcript_line_valid():
    line = TranscriptLine(ts_start=0.0, ts_end=2.44, text="大清早的")
    assert line.ts_start == 0.0
    assert line.text == "大清早的"


def test_transcript_line_rejects_missing_text():
    with pytest.raises(ValidationError):
        TranscriptLine(ts_start=0.0, ts_end=2.44)


def test_chat_line_and_product():
    chat = ChatLine(ts=123.5, user="user_3f2a", text="主播这件有L码吗")
    prod = Product(product_id="p001", name="法式碎花连衣裙", price=129, stock=200, category="连衣裙")
    assert chat.user == "user_3f2a"
    assert prod.price == 129


def test_event_types_enum():
    assert EVENT_TYPES == [
        "user_question", "product_intro", "selling_point", "promotion",
        "try_on", "interaction_prompt", "scarcity", "conversion_call", "price_mention",
    ]


def test_event_rejects_unknown_type():
    with pytest.raises(ValidationError):
        LiveEvent(event_id="e_001", ts=1.0, type="unknown_type", content="x", confidence=0.9, source="chat")


def test_segment_shape():
    seg = Segment(segment_id="s_001", ts_start=0.0, ts_end=187.16, text="内容", line_refs=[0, 1, 2])
    assert seg.line_refs == [0, 1, 2]


def test_stages_enum():
    assert STAGES == [
        "start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up",
    ]


def test_card_rejects_unknown_stage():
    with pytest.raises(ValidationError):
        DecisionCard(
            card_id="c_0001", timestamp=1234.5, stage="bogus",
            action={"name": "size_question", "category": "size", "goal": "g"},
            trigger={"event_id": "e_001", "segment_id": "s_012", "detail": "d", "rule_ref": "r"},
            reason="r", script="s", expected_goal="g",
            quality={"score": 87, "flags": []},
        )
