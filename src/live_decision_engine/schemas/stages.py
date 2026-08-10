from typing import Literal

from pydantic import BaseModel, Field

EVENT_TYPES = [
    "user_question", "product_intro", "selling_point", "promotion",
    "try_on", "interaction_prompt", "scarcity", "conversion_call", "price_mention",
]

EventType = Literal[
    "user_question", "product_intro", "selling_point", "promotion",
    "try_on", "interaction_prompt", "scarcity", "conversion_call", "price_mention",
]


class CleanedLine(BaseModel):
    ts_start: float = Field(ge=0)
    ts_end: float = Field(ge=0)
    text: str = Field(min_length=1)
    origin: str


class Segment(BaseModel):
    segment_id: str
    ts_start: float = Field(ge=0)
    ts_end: float = Field(ge=0)
    text: str = Field(min_length=1)
    line_refs: list[int] = []


class LiveEvent(BaseModel):
    event_id: str
    ts: float = Field(ge=0)
    type: EventType
    content: str
    confidence: float = Field(ge=0, le=1)
    source: Literal["segment", "chat"]
    segment_ref: str | None = None
