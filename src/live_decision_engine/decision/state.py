from live_decision_engine.schemas.inputs import Product
from live_decision_engine.schemas.stages import LiveEvent

_RECENT_LIMIT = 20
_STAGE_ORDER = ["start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up"]


class SessionState:
    def __init__(self, products: list[Product]):
        self.stage = "start"
        self.products = products
        self.current_product = products[0] if products else None
        self.recent_events: list[LiveEvent] = []
        self.last_card_ts: dict[str, float] = {}

    def advance(self, event: LiveEvent, stage_map: dict) -> None:
        target = stage_map.get(event.type)
        if target and target != self.stage:
            if _STAGE_ORDER.index(target) > _STAGE_ORDER.index(self.stage):
                self.stage = target
        self.recent_events.append(event)
        self.recent_events = self.recent_events[-_RECENT_LIMIT:]
