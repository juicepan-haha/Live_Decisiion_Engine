from pydantic import BaseModel, Field


class TranscriptLine(BaseModel):
    ts_start: float = Field(ge=0)
    ts_end: float = Field(ge=0)
    text: str = Field(min_length=1)


class ChatLine(BaseModel):
    ts: float = Field(ge=0)
    user: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Product(BaseModel):
    product_id: str
    name: str
    price: float = Field(ge=0)
    stock: int = Field(ge=0)
    category: str = ""


class SessionMetadata(BaseModel):
    session_id: str
    platform: str
    category: str = ""
    recorded_at: str
    source: str = ""


class SessionData(BaseModel):
    transcript: list[TranscriptLine] = []
    chat: list[ChatLine] = []
    products: list[Product] = []
    metadata: SessionMetadata | None = None
