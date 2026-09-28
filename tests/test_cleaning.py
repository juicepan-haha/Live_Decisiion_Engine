from live_decision_engine.cleaning.cleaner import clean_transcript
from live_decision_engine.schemas.inputs import TranscriptLine


def _line(ts_start, ts_end, text):
    return TranscriptLine(ts_start=ts_start, ts_end=ts_end, text=text)


def test_removes_filler_words():
    out = clean_transcript([_line(0.0, 2.0, "嗯嗯今天给大家介绍啊这个裙子")])
    assert out[0].text == "今天给大家介绍这个裙子"


def test_deduplicates_repeats():
    out = clean_transcript([_line(0.0, 2.0, "哈哈哈哈欢迎欢迎欢迎")])
    assert out[0].text == "哈哈欢迎欢迎"


def test_merges_fragments():
    out = clean_transcript([_line(0.0, 5.0, "大家好"), _line(5.2, 5.6, "欢迎来"), _line(5.6, 9.0, "到直播间")])
    assert out[0].text == "大家好 欢迎来到直播间"


def test_keeps_origin():
    out = clean_transcript([_line(0.0, 2.0, "嗯大家好")])
    assert out[0].origin == "嗯大家好"


def test_merged_line_keeps_all_origins():
    out = clean_transcript([_line(0.0, 5.0, "嗯嗯大家好"), _line(5.2, 5.6, "欢迎来")])
    assert out[0].text == "大家好 欢迎来"
    assert out[0].origin == "嗯嗯大家好 欢迎来"


def test_drops_empty_after_clean():
    out = clean_transcript([_line(0.0, 2.0, "嗯嗯嗯")])
    assert out == []
