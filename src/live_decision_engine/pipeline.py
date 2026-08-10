from pathlib import Path

from live_decision_engine.cleaning.cleaner import clean_transcript
from live_decision_engine.decision.engine import decide
from live_decision_engine.event.extractor import extract_events
from live_decision_engine.ingestion.adapter import load_session
from live_decision_engine.segmentation.segmenter import segment_lines
from live_decision_engine.validation.scorer import score_cards

STAGE_FILES = {
    "01": "01_cleaned.jsonl",
    "02": "02_segments.jsonl",
    "03": "03_events.jsonl",
    "04": "04_cards.jsonl",
}


def write_jsonl(path: Path, items) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")


def read_jsonl(path: Path, model) -> list:
    if not path.exists():
        raise FileNotFoundError(f"缺少产物: {path}")
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(model.model_validate_json(line))
    return items


def run_pipeline(
    session_dir: Path,
    from_stage: str | None = None,
    llm: bool = False,
    out_dir: Path | None = None,
) -> dict:
    from live_decision_engine.schemas.cards import DecisionCard
    from live_decision_engine.schemas.stages import CleanedLine, LiveEvent, Segment

    session_dir = Path(session_dir)
    out_dir = Path(out_dir) if out_dir else session_dir / "output"
    stages = out_dir / "stages"
    stages.mkdir(parents=True, exist_ok=True)

    if from_stage in (None, "01"):
        data = load_session(session_dir)
        cleaned = clean_transcript(data.transcript, llm=llm)
        write_jsonl(stages / STAGE_FILES["01"], cleaned)

    if from_stage in (None, "01", "02"):
        cleaned = read_jsonl(stages / STAGE_FILES["01"], CleanedLine)
        segments = segment_lines(cleaned, llm=llm)
        write_jsonl(stages / STAGE_FILES["02"], segments)

    if from_stage in (None, "01", "02", "03"):
        segments = read_jsonl(stages / STAGE_FILES["02"], Segment)
        data = load_session(session_dir)
        events = extract_events(segments, data.chat, llm=llm)
        write_jsonl(stages / STAGE_FILES["03"], events)

    if from_stage in (None, "01", "02", "03", "04"):
        events = read_jsonl(stages / STAGE_FILES["03"], LiveEvent)
        data = load_session(session_dir)
        cards = decide(events, data.products, llm=llm)
        scored = score_cards(cards, llm=llm)
        write_jsonl(stages / STAGE_FILES["04"], scored)

    if from_stage not in (None, "01", "02", "03", "04"):
        raise ValueError(f"非法 from_stage: {from_stage}（可选 01/02/03/04）")

    cards = read_jsonl(stages / STAGE_FILES["04"], DecisionCard)
    summary = _build_summary(session_dir, cards)
    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")
    counts = {
        "cards": len(cards),
        "score_avg": round(sum(c.quality.score for c in cards) / len(cards), 1) if cards else 0,
    }
    return {"cards": cards, "counts": counts, "summary": summary}


def _build_summary(session_dir: Path, cards) -> str:
    lines = [f"session: {session_dir.name}", f"cards: {len(cards)}"]
    for card in cards:
        lines.append(
            f"[{card.timestamp:>9.1f}s] stage={card.stage:<14} "
            f"action={card.action.name:<18} score={card.quality.score}"
        )
        lines.append(f"  reason: {card.reason}")
        lines.append(f"  script: {card.script}")
    return "\n".join(lines) + "\n"
