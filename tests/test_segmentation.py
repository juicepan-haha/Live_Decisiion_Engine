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


def test_intra_line_cut_no_duplicate_refs():
    # 行内切割 + 尾并：单行输入不得出现段内重复下标（回归：曾产出 [0, 0]）
    lines = [_line(0, 0.0, 1.0, "x" * 50 + "。" + "y" * 10)]
    segs = segment_lines(lines, min_chars=50, max_chars=100)
    for seg in segs:
        assert len(seg.line_refs) == len(set(seg.line_refs))
    assert segs[0].line_refs == [0]


def test_remainder_segment_ts_start_at_first_contributing_line():
    # 变体 A：硬切后 remainder 全部来自 line 2，末段 refs/ts_start 只应指向 line 2
    lines = [_line(i, float(i), float(i) + 1.0, "a" * 40) for i in range(3)]
    segs = segment_lines(lines, min_chars=90, max_chars=100)
    last = segs[-1]
    assert last.line_refs == [2]
    assert last.ts_start == lines[2].ts_start


def test_consumed_line_not_listed_in_later_segments():
    # 变体 B：line 0 文本全部落入第一段后，不得再出现在后续段的 refs 中
    lines = [
        _line(0, 0.0, 1.0, "x" * 30),
        _line(1, 1.0, 2.0, "y" * 25 + "。" + "z" * 30),
        _line(2, 2.0, 3.0, "w" * 75),
    ]
    segs = segment_lines(lines, min_chars=50, max_chars=100)
    assert segs[0].line_refs == [0, 1]
    assert segs[1].line_refs == [1, 2]
    assert segs[2].line_refs == [2]
