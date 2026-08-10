from typing import Literal

from pydantic import BaseModel, Field

STAGES = [
    "start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up",
]

Stage = Literal[
    "start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up",
]


class ActionRef(BaseModel):
    name: str
    category: str
    goal: str


class Trigger(BaseModel):
    event_id: str | None = None
    segment_id: str | None = None
    detail: str
    rule_ref: str


class Quality(BaseModel):
    score: int = Field(ge=0, le=100)
    flags: list[str] = []


class DecisionCard(BaseModel):
    card_id: str
    timestamp: float = Field(ge=0)
    stage: Stage
    action: ActionRef
    trigger: Trigger
    reason: str
    script: str
    expected_goal: str
    quality: Quality
