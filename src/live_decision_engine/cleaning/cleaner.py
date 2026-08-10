import re

from live_decision_engine.schemas.inputs import TranscriptLine
from live_decision_engine.schemas.stages import CleanedLine

_FILLER_RUN_RE = re.compile(r"([嗯啊呃呀哦哈嘛吧])\1*")
_REPEAT_RE = re.compile(r"(.+?)\1{2,}")  # 同一片段连续 3 次及以上

_MERGE_GAP = 0.5   # 秒
_MERGE_MAX_LEN = 8  # 字符


def _strip_fillers(text: str) -> str:
    def _repl(m: re.Match) -> str:
        # 语气词连续出现 4 次及以上视为情绪表达（如"哈哈哈哈"），压缩为 2 个保留；
        # 其余（含 1~3 连）视为噪声直接删除。
        return m.group(1) * 2 if len(m.group(0)) >= 4 else ""

    return _FILLER_RUN_RE.sub(_repl, text)


def _dedup_repeats(text: str) -> str:
    return _REPEAT_RE.sub(lambda m: m.group(1) * 2, text)


def _clean_text(text: str) -> str:
    text = _strip_fillers(text)
    text = _dedup_repeats(text)
    return text.strip()


def clean_transcript(lines: list[TranscriptLine], llm=None) -> list[CleanedLine]:
    out: list[CleanedLine] = []
    prev_end = 0.0
    for line in lines:
        text = _clean_text(line.text)
        if not text:
            continue
        if (
            out
            and line.ts_start - prev_end <= _MERGE_GAP
            and len(text) <= _MERGE_MAX_LEN
        ):
            last = out[-1]
            # 间隔为 0 视为同一句被时间戳切断，直接拼接；有小间隔则空格分隔
            sep = "" if line.ts_start - prev_end <= 0 else " "
            out[-1] = CleanedLine(
                ts_start=last.ts_start, ts_end=line.ts_end,
                text=f"{last.text}{sep}{text}", origin=last.origin,
            )
        else:
            out.append(
                CleanedLine(
                    ts_start=line.ts_start, ts_end=line.ts_end,
                    text=text, origin=line.text,
                )
            )
        prev_end = line.ts_end
    return out
