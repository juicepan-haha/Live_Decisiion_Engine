import re

from live_decision_engine.schemas.stages import CleanedLine, Segment

_SENTENCE_END = re.compile(r"[。！？.!?]")
_DEFAULT_MIN = 500
_DEFAULT_MAX = 1000


def _cut_point(text: str, floor: int, ceiling: int) -> int:
    """在 [floor, ceiling] 区间内找最后一个句末标点位置；找不到返回 -1。"""
    best = -1
    for m in _SENTENCE_END.finditer(text):
        if floor <= m.start() <= ceiling:
            best = m.start()
        elif m.start() > ceiling:
            break
    return best + 1 if best >= 0 else -1


def segment_lines(
    lines: list[CleanedLine],
    min_chars: int = _DEFAULT_MIN,
    max_chars: int = _DEFAULT_MAX,
    llm=None,
) -> list[Segment]:
    segments: list[Segment] = []
    buffer: list[str] = []
    buf_refs: list[int] = []
    buf_len = 0
    pending_start_ts = 0.0

    def flush(seg_text: str, refs: list[int], start_ts: float, end_ts: float, sid: int):
        segments.append(
            Segment(
                segment_id=f"s_{sid:03d}",
                ts_start=start_ts,
                ts_end=end_ts,
                text=seg_text,
                line_refs=refs,
            )
        )

    for idx, line in enumerate(lines):
        if not buffer:
            pending_start_ts = line.ts_start
        buffer.append(line.text)
        buf_refs.append(idx)
        buf_len += len(line.text)

        while buf_len >= min_chars:
            joined = "".join(buffer)
            cut = _cut_point(joined, min_chars, max_chars)
            if cut > 0:
                flush(joined[:cut], list(buf_refs), pending_start_ts, line.ts_end, len(segments) + 1)
                remainder = joined[cut:]
            elif buf_len >= max_chars:
                flush(joined[:max_chars], list(buf_refs), pending_start_ts, line.ts_end, len(segments) + 1)
                remainder = joined[max_chars:]
            else:
                break
            buffer = [remainder] if remainder else []
            buf_refs = list(buf_refs) if remainder else []
            buf_len = len(remainder)

    if buffer:
        joined = "".join(buffer)
        if segments and len(segments[-1].text) + len(joined) <= max_chars:
            last = segments[-1]
            segments[-1] = Segment(
                segment_id=last.segment_id,
                ts_start=last.ts_start,
                ts_end=lines[buf_refs[-1]].ts_end,
                text=last.text + joined,
                line_refs=last.line_refs + list(buf_refs),
            )
        else:
            flush(joined, list(buf_refs), pending_start_ts, lines[buf_refs[-1]].ts_end, len(segments) + 1)

    return segments
