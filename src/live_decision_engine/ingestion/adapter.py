import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from live_decision_engine.schemas.inputs import (
    ChatLine,
    Product,
    SessionData,
    SessionMetadata,
    TranscriptLine,
)

INPUT_FILES = {
    "transcript.jsonl": "transcript",
    "chat.jsonl": "chat",
    "products.json": "products",
    "metadata.json": "metadata",
}


class IngestionError(Exception):
    pass


def _read_lines(path: Path, model) -> list:
    items = []
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                items.append(model.model_validate_json(line))
            except ValidationError as e:
                raise IngestionError(f"{path.name}:{lineno} 非法数据: {e.errors()[0]['msg']}")
    return items


_ProductArray = TypeAdapter(list[Product])


def _read_products(path: Path) -> list:
    # products.json 是单行 JSON 数组（如 [{"product_id": ...}, ...]），
    # 不能按逐行对象解析，需整体按数组校验（brief 原 `_read_lines` 无法处理数组）。
    try:
        return _ProductArray.validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as e:
        raise IngestionError(f"{path.name}:1 非法数据: {e.errors()[0]['msg']}")


def _read_metadata(path: Path) -> SessionMetadata | None:
    try:
        return SessionMetadata.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as e:
        raise IngestionError(f"metadata.json 非法: {e.errors()[0]['msg']}")


def load_session(session_dir: Path) -> SessionData:
    session_dir = Path(session_dir)
    for filename in INPUT_FILES:
        if not (session_dir / filename).exists():
            raise IngestionError(f"缺少输入文件: {filename}（session 目录: {session_dir}）")

    transcript = _read_lines(session_dir / "transcript.jsonl", TranscriptLine)
    chat = _read_lines(session_dir / "chat.jsonl", ChatLine)
    products = _read_products(session_dir / "products.json")
    metadata = _read_metadata(session_dir / "metadata.json")
    return SessionData(transcript=transcript, chat=chat, products=products, metadata=metadata)


def validate_session(session_dir: Path) -> list[str]:
    session_dir = Path(session_dir)
    errors: list[str] = []
    for filename in INPUT_FILES:
        if not (session_dir / filename).exists():
            errors.append(f"缺少输入文件: {filename}")
    if errors:
        return errors
    try:
        load_session(session_dir)
    except IngestionError as e:
        errors.append(str(e))
    return errors
