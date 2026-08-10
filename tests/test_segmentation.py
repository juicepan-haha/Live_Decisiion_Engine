from live_decision_engine.schemas.stages import CleanedLine
from live_decision_engine.segmentation.segmenter import segment_lines


def _line(i, ts_start, ts_end, text):
    return CleanedLine(ts_start=ts_start, ts_end=ts_end, text=text, origin=text)


def test_single_segment_small_input():
    lines = [_line(0, 0.0, 5.0, "欢迎来到直播间，今天介绍新款。")]
    segs = segment_lines(lines)
    assert len(segs) == 1
    assert segs[0].segment_id == "s_001"
    assert segs[0].line_refs == [0]


def test_splits_at_sentence_boundary():
    lines = [_line(i, i * 10.0, i * 10.0 + 5.0, "欢迎来到直播间。") for i in range(120)]
    segs = segment_lines(lines, min_chars=10, max_chars=50)
    assert len(segs) >= 2
    assert all(s.ts_end >= s.ts_start for s in segs)


def test_hard_split_oversize_line():
    long_text = "今天给大家介绍这款连衣裙面料很好" * 60  # 480 字无标点
    lines = [_line(0, 0.0, 100.0, long_text)]
    segs = segment_lines(lines, min_chars=50, max_chars=100)
    assert len(segs) > 1
    assert all(len(s.text) <= 100 for s in segs)


def test_tail_merged_into_last():
    lines = [_line(i, i * 10.0, i * 10.0 + 5.0, "介绍商品。") for i in range(60)]
    segs = segment_lines(lines, min_chars=100, max_chars=500)
    last = segs[-1]
    assert last.text.endswith("介绍商品。")
    assert len(last.line_refs) == len(lines) - sum(len(s.line_refs) for s in segs[:-1])
