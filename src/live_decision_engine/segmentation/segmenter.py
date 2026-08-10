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
    buf_ref_lens: list[int] = []  # 与 buf_refs 平行：每个下标当前贡献的字符数
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
        buf_ref_lens.append(len(line.text))
        buf_len += len(line.text)

        while buf_len >= min_chars:
            joined = "".join(buffer)
            cut = _cut_point(joined, min_chars, max_chars)
            if cut <= 0:
                if buf_len < max_chars:
                    break
                cut = max_chars
            # 按切点划分下标：前缀段只保留对 joined[:cut] 有贡献的行，
            # remainder 只保留与 remainder 文本重叠的行及其剩余字符数
            cut_refs: list[int] = []
            rem_refs: list[int] = []
            rem_lens: list[int] = []
            pos = 0
            for ref, ln in zip(buf_refs, buf_ref_lens):
                end = pos + ln
                if ln and pos < cut:
                    cut_refs.append(ref)
                if ln and end > cut:
                    rem_refs.append(ref)
                    rem_lens.append(end - max(cut, pos))
                pos = end
            remainder = joined[cut:]
            flush(joined[:cut], cut_refs, pending_start_ts, line.ts_end, len(segments) + 1)
            buffer = [remainder] if remainder else []
            buf_refs = rem_refs
            buf_ref_lens = rem_lens
            buf_len = len(remainder)
            if buf_refs:
                pending_start_ts = lines[buf_refs[0]].ts_start

    if buffer:
        joined = "".join(buffer)
        if segments and len(segments[-1].text) + len(joined) <= max_chars:
            last = segments[-1]
            seen = set(last.line_refs)
            segments[-1] = Segment(
                segment_id=last.segment_id,
                ts_start=last.ts_start,
                ts_end=lines[buf_refs[-1]].ts_end,
                text=last.text + joined,
                line_refs=list(last.line_refs) + [r for r in buf_refs if r not in seen],
            )
        else:
            flush(joined, list(buf_refs), pending_start_ts, lines[buf_refs[-1]].ts_end, len(segments) + 1)

    return segments
