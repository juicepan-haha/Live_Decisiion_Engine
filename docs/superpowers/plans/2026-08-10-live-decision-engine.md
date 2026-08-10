# Live Decision Engine 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `Live_Decisiion_Engine` 空仓库中实现"一场直播 → 一组高质量 Decision Cards"的开源最小 Demo：分层流水线（ingestion → cleaning → segmentation → event → decision → validation），规则为主、LLM 可选，demo 数据为真实转录脱敏 + 合成弹幕。

**Architecture:** 每个环节是独立模块，产物按层落盘到 `demo/<session>/output/stages/`（01_cleaned → 02_segments → 03_events → 04_cards），层间严格走文件、只依赖前一层产物；CLI（typer）支持 `--from` 从任意层重跑。决策规则与动作库外部化为 YAML，LLM（OpenAI 兼容）仅在配置 key 后启用。

**Tech Stack:** Python 3.11+，pydantic v2（数据契约）、typer（CLI）、pyyaml（规则表）、pytest（测试）、openai（可选依赖）。

## Global Constraints

- 包名：`live-decision-engine`，源码根：`src/live_decision_engine/`，Python `>=3.11`
- 运行依赖仅：`pydantic>=2.0`、`typer>=0.12`、`pyyaml>=6.0`；可选依赖 `llm = ["openai>=1.0"]`、`dev = ["pytest>=8.0"]`
- 无数据库、无网络请求（LLM 除外）、无 UI；产物全部为 JSONL 文本文件
- 事件类型枚举（唯一）：`user_question / product_intro / selling_point / promotion / try_on / interaction_prompt / scarcity / conversion_call / price_mention`
- stage 枚举（唯一）：`start / attract / product_intro / try_on / trust / conversion / follow_up`
- 动作库：移植原项目 `stream-script-kb/agent/action_library.py` 的 14 个动作、4 类（`interaction / size / selling / conversion`），话术模板中 `{product} {price} {stock}` 占位符保留
- 打分：0–100，阈值 60，低于阈值不进最终输出；同 action 30 分钟窗口去重
- 输入四件套文件名定死：`transcript.jsonl / chat.jsonl / products.json / metadata.json`
- LLM 环境变量：`LDE_LLM_API_KEY` / `LDE_LLM_BASE_URL` / `LDE_LLM_MODEL`；未配置或无 key 时系统纯规则运行
- 每层函数签名必须预留 `llm=None` 参数（Task 11 填入 LLM 增强，禁止后续重构签名）
- 提交信息前缀：`feat: / test: / docs: / chore:`

---

### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `src/live_decision_engine/__init__.py`
- Create: `src/live_decision_engine/py.typed`
- Create: `.gitignore`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: 可 `pip install -e .` 的包骨架，pytest 可发现 `tests/`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "live-decision-engine"
version = "0.1.0"
description = "Turn one livestream session into a set of auditable decision cards."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = [
    "pydantic>=2.0",
    "typer>=0.12",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
llm = ["openai>=1.0"]
dev = ["pytest>=8.0"]

[project.scripts]
live-decision = "live_decision_engine.cli:app"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 写 LICENSE（MIT 全文）**

```text
MIT License

Copyright (c) 2026 wentworth

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: 写 .gitignore**

```text
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
*.egg-info/
dist/
build/
demo/*/output/
```

- [ ] **Step 4: 写包初始化文件**

`src/live_decision_engine/__init__.py`:
```python
__version__ = "0.1.0"
```

`src/live_decision_engine/py.typed`: 空文件。

`tests/__init__.py`: 空文件。

- [ ] **Step 5: 创建占位 README.md 并验证安装**

`README.md`（占位，Task 13 完善）:
```markdown
# Live Decision Engine
Turn one livestream session into a set of auditable decision cards.
```

运行验证：
```bash
cd /home/wentworth/Developer/ultimate/Live_Decisiion_Engine
python -m venv .venv && .venv/bin/pip install -e ".[dev]" -q
.venv/bin/python -c "import live_decision_engine; print(live_decision_engine.__version__)"
```
Expected: `0.1.0`

- [ ] **Step 6: 验证 pytest 可运行**

```bash
.venv/bin/pytest -q
```
Expected: `no tests ran`（退出码 5 可接受，说明收集正常）。

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml LICENSE .gitignore README.md src tests
git commit -m "chore: project scaffolding (pyproject, license, package skeleton)"
```

---

### Task 2: 数据契约（schemas）

**Files:**
- Create: `src/live_decision_engine/schemas/__init__.py`
- Create: `src/live_decision_engine/schemas/inputs.py`
- Create: `src/live_decision_engine/schemas/stages.py`
- Create: `src/live_decision_engine/schemas/cards.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Produces（后续所有层依赖的类型）：
  - `inputs.py`: `TranscriptLine(ts_start: float, ts_end: float, text: str)`、`ChatLine(ts: float, user: str, text: str)`、`Product(product_id: str, name: str, price: float, stock: int, category: str)`、`SessionMetadata(session_id: str, platform: str, category: str, recorded_at: str, source: str)`、`SessionData(transcript: list[TranscriptLine], chat: list[ChatLine], products: list[Product], metadata: SessionMetadata | None)`
  - `stages.py`: `CleanedLine(ts_start: float, ts_end: float, text: str, origin: str)`、`Segment(segment_id: str, ts_start: float, ts_end: float, text: str, line_refs: list[int])`、`EVENT_TYPES: list[str]`（9 种）、`LiveEvent(event_id: str, ts: float, type: EventType, content: str, confidence: float, source: Literal["segment","chat"], segment_ref: str | None = None)`
  - `cards.py`: `STAGES: list[str]`（7 种）、`ActionRef(name, category, goal)`、`Trigger(event_id, segment_id, detail, rule_ref)`、`Quality(score: int, flags: list[str])`、`DecisionCard(card_id, timestamp, stage: Stage, action, trigger, reason, script, expected_goal, quality)`
- 所有模型 pydantic v2 `BaseModel`；`LiveEvent.type` 与 `DecisionCard.stage` 用 `Literal` 约束

- [ ] **Step 1: 写失败的测试**

`tests/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError

from live_decision_engine.schemas.cards import STAGES, DecisionCard
from live_decision_engine.schemas.inputs import ChatLine, Product, TranscriptLine
from live_decision_engine.schemas.stages import EVENT_TYPES, LiveEvent, Segment


def test_transcript_line_valid():
    line = TranscriptLine(ts_start=0.0, ts_end=2.44, text="大清早的")
    assert line.ts_start == 0.0
    assert line.text == "大清早的"


def test_transcript_line_rejects_missing_text():
    with pytest.raises(ValidationError):
        TranscriptLine(ts_start=0.0, ts_end=2.44)


def test_chat_line_and_product():
    chat = ChatLine(ts=123.5, user="user_3f2a", text="主播这件有L码吗")
    prod = Product(product_id="p001", name="法式碎花连衣裙", price=129, stock=200, category="连衣裙")
    assert chat.user == "user_3f2a"
    assert prod.price == 129


def test_event_types_enum():
    assert EVENT_TYPES == [
        "user_question", "product_intro", "selling_point", "promotion",
        "try_on", "interaction_prompt", "scarcity", "conversion_call", "price_mention",
    ]


def test_event_rejects_unknown_type():
    with pytest.raises(ValidationError):
        LiveEvent(event_id="e_001", ts=1.0, type="unknown_type", content="x", confidence=0.9, source="chat")


def test_segment_shape():
    seg = Segment(segment_id="s_001", ts_start=0.0, ts_end=187.16, text="内容", line_refs=[0, 1, 2])
    assert seg.line_refs == [0, 1, 2]


def test_stages_enum():
    assert STAGES == [
        "start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up",
    ]


def test_card_rejects_unknown_stage():
    with pytest.raises(ValidationError):
        DecisionCard(
            card_id="c_0001", timestamp=1234.5, stage="bogus",
            action={"name": "size_question", "category": "size", "goal": "g"},
            trigger={"event_id": "e_001", "segment_id": "s_012", "detail": "d", "rule_ref": "r"},
            reason="r", script="s", expected_goal="g",
            quality={"score": 87, "flags": []},
        )
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_schemas.py -v`
Expected: FAIL（ModuleNotFoundError: live_decision_engine.schemas）

- [ ] **Step 3: 实现 schemas**

`src/live_decision_engine/schemas/__init__.py`:
```python
from live_decision_engine.schemas.cards import (
    STAGES,
    ActionRef,
    DecisionCard,
    Quality,
    Trigger,
)
from live_decision_engine.schemas.inputs import (
    ChatLine,
    Product,
    SessionData,
    SessionMetadata,
    TranscriptLine,
)
from live_decision_engine.schemas.stages import (
    EVENT_TYPES,
    CleanedLine,
    LiveEvent,
    Segment,
)

__all__ = [
    "STAGES", "EVENT_TYPES",
    "ActionRef", "ChatLine", "CleanedLine", "DecisionCard", "LiveEvent",
    "Product", "Quality", "Segment", "SessionData", "SessionMetadata",
    "TranscriptLine", "Trigger",
]
```

`src/live_decision_engine/schemas/inputs.py`:
```python
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
```

`src/live_decision_engine/schemas/stages.py`:
```python
from typing import Literal

from pydantic import BaseModel, Field

EVENT_TYPES = [
    "user_question", "product_intro", "selling_point", "promotion",
    "try_on", "interaction_prompt", "scarcity", "conversion_call", "price_mention",
]

EventType = Literal[
    "user_question", "product_intro", "selling_point", "promotion",
    "try_on", "interaction_prompt", "scarcity", "conversion_call", "price_mention",
]


class CleanedLine(BaseModel):
    ts_start: float = Field(ge=0)
    ts_end: float = Field(ge=0)
    text: str = Field(min_length=1)
    origin: str


class Segment(BaseModel):
    segment_id: str
    ts_start: float = Field(ge=0)
    ts_end: float = Field(ge=0)
    text: str = Field(min_length=1)
    line_refs: list[int] = []


class LiveEvent(BaseModel):
    event_id: str
    ts: float = Field(ge=0)
    type: EventType
    content: str
    confidence: float = Field(ge=0, le=1)
    source: Literal["segment", "chat"]
    segment_ref: str | None = None
```

`src/live_decision_engine/schemas/cards.py`:
```python
from typing import Literal

from pydantic import BaseModel, Field

STAGES = [
    "start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up",
]

Stage = Literal[
    "start", "attract", "product_intro", "try_on", "trust", "conversion", "follow_up",
]


class ActionRef(BaseModel):
    name: str
    category: str
    goal: str


class Trigger(BaseModel):
    event_id: str | None = None
    segment_id: str | None = None
    detail: str
    rule_ref: str


class Quality(BaseModel):
    score: int = Field(ge=0, le=100)
    flags: list[str] = []


class DecisionCard(BaseModel):
    card_id: str
    timestamp: float = Field(ge=0)
    stage: Stage
    action: ActionRef
    trigger: Trigger
    reason: str
    script: str
    expected_goal: str
    quality: Quality
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_schemas.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/schemas tests/test_schemas.py
git commit -m "feat: data contracts for inputs, stages and decision cards"
```

---

### Task 3: Ingestion（Data Adapter）

**Files:**
- Create: `src/live_decision_engine/ingestion/__init__.py`
- Create: `src/live_decision_engine/ingestion/adapter.py`
- Create: `tests/fixtures/session_mini/transcript.jsonl`
- Create: `tests/fixtures/session_mini/chat.jsonl`
- Create: `tests/fixtures/session_mini/products.json`
- Create: `tests/fixtures/session_mini/metadata.json`
- Test: `tests/test_ingestion.py`

**Interfaces:**
- Consumes: `schemas.inputs.*`（Task 2）
- Produces:
  - `load_session(session_dir: Path) -> SessionData`——读四件套并逐行校验；文件缺失/行损坏时抛 `IngestionError(message: str)`（自定义异常，message 含文件与行号）
  - `validate_session(session_dir: Path) -> list[str]`——返回错误列表，空列表表示通过（不抛异常）
  - `IngestionError(Exception)`

- [ ] **Step 1: 写 fixture 与失败测试**

`tests/fixtures/session_mini/metadata.json`:
```json
{"session_id": "session_mini", "platform": "taobao", "category": "女装", "recorded_at": "2026-07-13T08:00:00+08:00", "source": "synthetic"}
```

`tests/fixtures/session_mini/products.json`:
```json
[{"product_id": "p001", "name": "法式碎花连衣裙", "price": 129, "stock": 200, "category": "连衣裙"}]
```

`tests/fixtures/session_mini/chat.jsonl`:
```jsonl
{"ts": 10.0, "user": "user_01", "text": "主播这件有L码吗"}
{"ts": 20.0, "user": "user_02", "text": "多少钱啊"}
```

`tests/fixtures/session_mini/transcript.jsonl`:
```jsonl
{"ts_start": 0.0, "ts_end": 5.0, "text": "欢迎来到直播间"}
{"ts_start": 5.0, "ts_end": 10.0, "text": "今天给大家介绍这款连衣裙"}
```

`tests/test_ingestion.py`:
```python
from pathlib import Path

import pytest

from live_decision_engine.ingestion.adapter import (
    IngestionError,
    load_session,
    validate_session,
)

FIXTURE = Path(__file__).parent / "fixtures" / "session_mini"


def test_validate_ok():
    assert validate_session(FIXTURE) == []


def test_load_session_ok():
    data = load_session(FIXTURE)
    assert len(data.transcript) == 2
    assert len(data.chat) == 2
    assert data.products[0].name == "法式碎花连衣裙"
    assert data.metadata is not None
    assert data.metadata.session_id == "session_mini"


def test_validate_missing_file(tmp_path):
    errs = validate_session(tmp_path)
    assert any("transcript.jsonl" in e for e in errs)


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(IngestionError):
        load_session(tmp_path)


def test_validate_bad_line(tmp_path):
    (tmp_path / "products.json").write_text("[]", encoding="utf-8")
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "chat.jsonl").write_text("not json\n", encoding="utf-8")
    (tmp_path / "transcript.jsonl").write_text(
        '{"ts_start": 0.0, "ts_end": 1.0, "text": "ok"}\n', encoding="utf-8"
    )
    errs = validate_session(tmp_path)
    assert any("chat.jsonl:1" in e for e in errs)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_ingestion.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 adapter**

`src/live_decision_engine/ingestion/__init__.py`:
```python
from live_decision_engine.ingestion.adapter import IngestionError, load_session, validate_session

__all__ = ["IngestionError", "load_session", "validate_session"]
```

`src/live_decision_engine/ingestion/adapter.py`:
```python
import json
from pathlib import Path

from pydantic import ValidationError

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
    products = _read_lines(session_dir / "products.json", Product)
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
```

注意：`products.json` 与 `metadata.json` 是单对象/数组文件而非逐行 JSONL，但 `_read_lines`/`_read_metadata` 按单行解析即可正确工作（单行 JSON）。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_ingestion.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/ingestion tests/fixtures/session_mini tests/test_ingestion.py
git commit -m "feat: ingestion adapter with per-line validation"
```

---

### Task 4: Cleaning（转录清洗）

**Files:**
- Create: `src/live_decision_engine/cleaning/__init__.py`
- Create: `src/live_decision_engine/cleaning/cleaner.py`
- Test: `tests/test_cleaning.py`

**Interfaces:**
- Consumes: `TranscriptLine`（Task 2）
- Produces: `clean_transcript(lines: list[TranscriptLine], llm=None) -> list[CleanedLine]`——每行输出 `CleanedLine(text=清洗后, origin=原 text)`；时间戳断裂短句（与前一行间隔 ≤ 0.5 秒且新行 ≤ 8 字符）合并到前一行

**清洗规则**（保守，只删明确噪声）：
1. 删除纯语气词 token：`嗯 / 啊 / 呃 / 呀 / 哦 / 哈 / 嘛 / 吧`（前后是标点/空白或行首行尾时删除）
2. 连续重复字 ≥3 压缩为 2 个（如"哈哈哈哈"→"哈哈"）
3. 合并短句：`ts_start - prev.ts_end <= 0.5 and len(text) <= 8` → 追加到前一行（空格分隔），保留前一行起始时间戳
4. 清洗后空行丢弃

- [ ] **Step 1: 写失败测试**

`tests/test_cleaning.py`:
```python
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


def test_drops_empty_after_clean():
    out = clean_transcript([_line(0.0, 2.0, "嗯嗯嗯")])
    assert out == []
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_cleaning.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 cleaner**

`src/live_decision_engine/cleaning/__init__.py`:
```python
from live_decision_engine.cleaning.cleaner import clean_transcript

__all__ = ["clean_transcript"]
```

`src/live_decision_engine/cleaning/cleaner.py`:
```python
import re

from live_decision_engine.schemas.inputs import TranscriptLine
from live_decision_engine.schemas.stages import CleanedLine

_FILLERS = ["嗯", "啊", "呃", "呀", "哦", "哈", "嘛", "吧"]
_REPEAT_RE = re.compile(r"(.)\1{2,}")  # 同一字符连续 3 次及以上

_MERGE_GAP = 0.5   # 秒
_MERGE_MAX_LEN = 8  # 字符


def _strip_fillers(text: str) -> str:
    for filler in _FILLERS:
        text = re.sub(rf"(^|[\s，。！？、；：,.!?]){filler}(?=[\s，。！？、；：,.!?]|$)", r"\1", text)
    return text


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
            out[-1] = CleanedLine(
                ts_start=last.ts_start, ts_end=line.ts_end,
                text=f"{last.text} {text}", origin=last.origin,
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
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_cleaning.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/cleaning tests/test_cleaning.py
git commit -m "feat: conservative transcript cleaner (fillers, repeats, fragment merge)"
```

---

### Task 5: Segmentation（语义切块）

**Files:**
- Create: `src/live_decision_engine/segmentation/__init__.py`
- Create: `src/live_decision_engine/segmentation/segmenter.py`
- Test: `tests/test_segmentation.py`

**Interfaces:**
- Consumes: `CleanedLine`（Task 2）
- Produces: `segment_lines(lines: list[CleanedLine], min_chars: int = 500, max_chars: int = 1000, llm=None) -> list[Segment]`——语义块切分，逻辑移植自原项目 `stream-script-kb/batch_pipeline/step2_chunk.py`：
  1. 逐行累积文本；达到 `min_chars` 后优先在句末标点（`。！？.!?`）处断块
  2. 超 `max_chars` 未遇句末标点则硬切
  3. 结尾短尾合并进最后一块
  4. `segment_id` 格式 `s_{序号:03d}`，`ts_start/ts_end` 取块内首行/末行时间戳，`line_refs` 为原始 lines 列表下标

- [ ] **Step 1: 写失败测试**

`tests/test_segmentation.py`:
```python
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
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_segmentation.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 segmenter**

`src/live_decision_engine/segmentation/__init__.py`:
```python
from live_decision_engine.segmentation.segmenter import segment_lines

__all__ = ["segment_lines"]
```

`src/live_decision_engine/segmentation/segmenter.py`:
```python
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

        if buf_len >= min_chars:
            joined = "".join(buffer)
            cut = _cut_point(joined, min_chars, max_chars)
            if cut > 0:
                flush(joined[:cut], list(buf_refs), pending_start_ts, line.ts_end, len(segments) + 1)
                buffer, buf_refs, buf_len = [], [], []
            elif buf_len >= max_chars:
                flush(joined[:max_chars], list(buf_refs), pending_start_ts, line.ts_end, len(segments) + 1)
                buffer, buf_refs, buf_len = [], [], []

    if buffer:
        joined = "".join(buffer)
        if segments:
            last = segments[-1]
            segments[-1] = Segment(
                segment_id=last.segment_id,
                ts_start=last.ts_start,
                ts_end=lines[buf_refs[-1]].ts_end,
                text=last.text + joined,
                line_refs=last.line_refs + list(buf_refs),
            )
        else:
            flush(joined, list(buf_refs), pending_start_ts, lines[buf_refs[-1]].ts_end, 1)

    return segments
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_segmentation.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/segmentation tests/test_segmentation.py
git commit -m "feat: sentence-boundary segmenter with hard split and tail merge"
```

---

### Task 6: 规则表（YAML）与加载器

**Files:**
- Create: `src/live_decision_engine/rules/patterns.yaml`
- Create: `src/live_decision_engine/rules/decisions.yaml`
- Create: `src/live_decision_engine/rules/actions.yaml`
- Create: `src/live_decision_engine/rules/loader.py`
- Create: `src/live_decision_engine/rules/__init__.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Produces:
  - `load_patterns() -> list[dict]`——patterns.yaml 的 `patterns` 列表，每项 `{id, source, regex, event_type, confidence}`
  - `load_rules() -> tuple[list[dict], dict, dict]`——decisions.yaml 的 `rules` 列表（每项 `{id, when, action, priority, detail}`）+ `fallback` 字典（stage → action 名列表）+ `stage_map` 字典（event_type → stage）
  - `load_actions() -> dict[str, dict]`——actions.yaml 的 `actions` 字典，每项 `{category, goal, trigger, template}`
  - `load_action_stages() -> dict[str, list[str]]`——decisions.yaml 的 `action_stages` 字典
  - 路径解析相对于 `rules/` 目录本身（`Path(__file__).parent`），不依赖 CWD；全部 `@lru_cache`

- [ ] **Step 1: 写失败测试**

`tests/test_rules.py`:
```python
from live_decision_engine.rules.loader import (
    load_action_stages,
    load_actions,
    load_patterns,
    load_rules,
)


def test_patterns_loaded():
    patterns = load_patterns()
    assert len(patterns) >= 8
    assert all({"id", "source", "regex", "event_type", "confidence"} <= set(p) for p in patterns)


def test_rules_and_fallback():
    rules, fallback, stage_map = load_rules()
    assert len(rules) >= 8
    assert fallback["conversion"] == ["scarcity", "no_conversion", "last_call", "coupon_push", "size_question"]
    assert stage_map["product_intro"] == "product_intro"


def test_actions_loaded():
    actions = load_actions()
    assert len(actions) == 14
    assert set(actions["size_question"].keys()) == {"category", "goal", "trigger", "template"}
    assert "{product}" in actions["scarcity"]["template"]


def test_action_stages():
    stages = load_action_stages()
    assert "size_question" in stages
    assert "scarcity" in stages["conversion"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_rules.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 写 YAML 规则表**

`src/live_decision_engine/rules/patterns.yaml`:
```yaml
patterns:
  - id: p_question_size
    source: chat
    regex: "(尺码|多大码|什么码|有.{0,8}码|穿什么|能穿吗|合不合身)"
    event_type: user_question
    confidence: 0.9
  - id: p_question_price
    source: chat
    regex: "(多少钱|什么价格|贵不贵|便宜吗|怎么卖)"
    event_type: user_question
    confidence: 0.85
  - id: p_question_generic
    source: chat
    regex: "(怎么买|哪里拍|链接|发货|退换|七天无理由)"
    event_type: user_question
    confidence: 0.8
  - id: p_intro
    source: segment
    regex: "(今天.{0,12}(款|件|裙子|衣服|裤子|外套)|给大家介绍|这个(款|版型|颜色)|上链接|过款)"
    event_type: product_intro
    confidence: 0.85
  - id: p_selling_point
    source: segment
    regex: "(面料|材质|版型|做工|走线|防晒|显瘦|百搭|不透|舒服)"
    event_type: selling_point
    confidence: 0.8
  - id: p_promotion
    source: segment
    regex: "(优惠|折扣|立减|领券|满.{0,4}减|秒杀|买.{0,4}送|福利)"
    event_type: promotion
    confidence: 0.85
  - id: p_scarcity
    source: segment
    regex: "(最后.{0,6}(件|单|份)|限量|库存|卖完|抢|手速|拼单)"
    event_type: scarcity
    confidence: 0.85
  - id: p_try_on
    source: segment
    regex: "(试穿|上身|换.{0,4}(码|件)|穿给你们看|直接穿)"
    event_type: try_on
    confidence: 0.85
  - id: p_interaction
    source: segment
    regex: "(扣[0-9一二三]|公屏|评论区|打个.{0,4}(字|卡)|点关注|点点赞|有没有人)"
    event_type: interaction_prompt
    confidence: 0.8
  - id: p_conversion
    source: segment
    regex: "(下单|拍下|已拍|加购|购物车|上车|链接拍)"
    event_type: conversion_call
    confidence: 0.8
  - id: p_price_mention
    source: segment
    regex: "([0-9]+(\\.?[0-9]+)?(元|块)|到手.{0,4}[0-9]+)"
    event_type: price_mention
    confidence: 0.75
```

`src/live_decision_engine/rules/decisions.yaml`:
```yaml
rules:
  - id: rule_01
    when: {event_type: user_question, keyword: "尺码|码|合身"}
    action: size_question
    priority: 90
    detail: "用户询问尺码"
  - id: rule_02
    when: {event_type: user_question, keyword: "多少钱|价格|贵|便宜"}
    action: comparison
    priority: 85
    detail: "用户询问价格"
  - id: rule_03
    when: {event_type: user_question}
    action: question_prompt
    priority: 55
    detail: "用户提问，引导集中答疑"
  - id: rule_04
    when: {event_type: product_intro}
    action: try_on
    priority: 70
    detail: "主播开始介绍新品"
  - id: rule_05
    when: {event_type: selling_point}
    action: detail_show
    priority: 70
    detail: "主播陈述卖点"
  - id: rule_06
    when: {event_type: promotion}
    action: scarcity
    priority: 85
    detail: "促销信号"
  - id: rule_07
    when: {event_type: scarcity}
    action: scarcity
    priority: 80
    detail: "库存紧张"
  - id: rule_08
    when: {event_type: conversion_call}
    action: no_conversion
    priority: 70
    detail: "成交阶段，紧跟催单"
  - id: rule_09
    when: {event_type: interaction_prompt}
    action: question_prompt
    priority: 60
    detail: "主播引导互动，跟进提问收集关注点"
  - id: rule_10
    when: {event_type: price_mention}
    action: comparison
    priority: 75
    detail: "提及价格，强化价格优势"

fallback:
  start: [engagement_poll]
  attract: [engagement_poll]
  product_intro: [height_poll, size_question, question_prompt, try_on]
  try_on: [try_on, detail_show, fabric_demo, size_question]
  trust: [comparison, fabric_demo, detail_show]
  conversion: [scarcity, no_conversion, last_call, coupon_push, size_question]
  follow_up: [scarcity, no_conversion, engagement_poll]

stage_map:
  product_intro: product_intro
  selling_point: product_intro
  try_on: try_on
  promotion: conversion
  scarcity: conversion
  conversion_call: conversion
  interaction_prompt: attract
  user_question: product_intro

action_stages:
  engagement_poll: [start, attract]
  height_poll: [product_intro]
  question_prompt: [product_intro, try_on]
  size_question: [product_intro, try_on, conversion]
  size_promise: [product_intro, conversion]
  size_recommend: [product_intro, try_on]
  fabric_demo: [try_on, trust]
  detail_show: [try_on]
  comparison: [trust]
  try_on: [try_on]
  scarcity: [conversion]
  no_conversion: [conversion]
  coupon_push: [conversion]
  last_call: [conversion]
```

`src/live_decision_engine/rules/actions.yaml`（移植自原项目 action_library，14 动作）:
```yaml
actions:
  engagement_poll:
    category: interaction
    goal: "提高停留时长，活跃直播间"
    trigger: "开场 或 在线人数下降 或 长时间无互动"
    template: "刚进来的姐妹别划走！今天{product}这个价格，外面绝对买不到——想看的扣'看'"
  height_poll:
    category: interaction
    goal: "激活互动 + 筛选用户身材信息"
    trigger: "新品介绍时 或 需要了解用户身材分布"
    template: "160以下的姐妹扣1，160以上的扣2，我看看多少人合适这件{product}"
  question_prompt:
    category: interaction
    goal: "引导评论互动，收集用户关注点"
    trigger: "介绍产品中 或 需要了解用户疑虑"
    template: "姐妹们对{product}有什么问题直接打在公屏上，我一个一个回答！"
  size_question:
    category: size
    goal: "降低尺码顾虑，减少购买阻力"
    trigger: "用户询问尺码 或 进入成交阶段需打消最后顾虑"
    template: "不确定尺码的姐妹告诉我身高体重，我帮你选！{product}不挑人但尺码一定要选对"
  size_promise:
    category: size
    goal: "消除尺码风险，建立退换信心"
    trigger: "用户犹豫尺码 或 有人问'穿不上怎么办'"
    template: "尺码不合适直接退换！我们家支持7天无理由——{product}你大胆拍，回来试，不合适我出运费给你换"
  size_recommend:
    category: size
    goal: "主动推荐尺码，减少决策时间"
    trigger: "介绍了适用身材特征 或 多个尺码可选"
    template: "听我的——{product}这款，120斤以下拍M，120-140拍L，140以上拍XL。我已经卖了上千件，尺码从来没出过错"
  fabric_demo:
    category: selling
    goal: "展示面料质量，建立质感信任"
    trigger: "介绍了面料材质 或 用户质疑质量"
    template: "姐妹们感受一下{product}这个面料——拿到手一模就知道，跟商场几百块的一模一样。我们是源头工厂，同款面料供给品牌专柜"
  detail_show:
    category: selling
    goal: "展示产品细节，强化卖点认知"
    trigger: "开始展示产品 或 用户要求看细节"
    template: "来——镜头拉近！看{product}这个走线、这个版型、这个收边，你自己放大看。这个做工，专柜没有五六百下不来"
  comparison:
    category: selling
    goal: "竞品对比，建立价格优势认知"
    trigger: "需要建立价格信任 或 用户说'某家更便宜'"
    template: "外面同款{product}商场卖{price}，我们今天直播间直接一半都不到。因为我们是从工厂直接发，没有中间商赚差价"
  try_on:
    category: selling
    goal: "上身展示真实效果"
    trigger: "进入试穿展示阶段 或 用户想看上身效果"
    template: "光说没用！直接给姐妹上身看效果——来，{product}这个版型，我穿你们看！"
  scarcity:
    category: conversion
    goal: "制造稀缺感，加速下单决策"
    trigger: "库存紧张 或 需要加速成交节奏"
    template: "最后{stock}件了姐妹们！{product}这个价格出了直播间再也没有——拼手速！拍了直接打'已拍'"
  no_conversion:
    category: conversion
    goal: "打破僵局，刺激沉寂期成交"
    trigger: "一段时间无成交 或 观众犹豫不决"
    template: "库存还有最后20件！{product}卖完直接过款——还没拍的姐妹别等了，这个价格你拿回去绝对不亏"
  coupon_push:
    category: conversion
    goal: "优惠刺激，利用价格落差促单"
    trigger: "需要价格刺激 或 价格较高需要优惠驱动"
    template: "还没领券的姐妹，屏幕下方领券下单立减！到手只要{price}——这个券只剩最后几分钟了，领完即止"
  last_call:
    category: conversion
    goal: "最后催单，制造错过恐惧"
    trigger: "即将过款 或 倒计时阶段"
    template: "拼手速了姐妹们！{product}最后上车机会，一分钟后就过款——拍了直接打'已拍'，没拍的抓紧了"
```

`src/live_decision_engine/rules/loader.py`:
```python
from functools import lru_cache
from pathlib import Path

import yaml

_RULES_DIR = Path(__file__).parent


def _load_yaml(name: str) -> dict:
    with (_RULES_DIR / name).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def load_patterns() -> list[dict]:
    return _load_yaml("patterns.yaml")["patterns"]


@lru_cache(maxsize=None)
def load_rules() -> tuple[list[dict], dict, dict]:
    data = _load_yaml("decisions.yaml")
    return data["rules"], data["fallback"], data["stage_map"]


@lru_cache(maxsize=None)
def load_actions() -> dict[str, dict]:
    return _load_yaml("actions.yaml")["actions"]


@lru_cache(maxsize=None)
def load_action_stages() -> dict[str, list[str]]:
    return _load_yaml("decisions.yaml")["action_stages"]
```

`src/live_decision_engine/rules/__init__.py`:
```python
from live_decision_engine.rules.loader import (
    load_action_stages,
    load_actions,
    load_patterns,
    load_rules,
)

__all__ = ["load_action_stages", "load_actions", "load_patterns", "load_rules"]
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_rules.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/rules tests/test_rules.py
git commit -m "feat: externalized rule tables (patterns, decisions, actions) with cached loader"
```

---

### Task 7: Event Extraction（规则）

**Files:**
- Create: `src/live_decision_engine/event/__init__.py`
- Create: `src/live_decision_engine/event/extractor.py`
- Test: `tests/test_event_extractor.py`

**Interfaces:**
- Consumes: `Segment`、`ChatLine`、`LiveEvent`（Task 2）；`load_patterns()`（Task 6）
- Produces: `extract_events(segments: list[Segment], chat: list[ChatLine], llm=None) -> list[LiveEvent]`
  - segment 事件：对每个 segment 文本做正则匹配（patterns 中 `source: segment`），命中记 `event_id="e_{seq:04d}"`、`ts=segment.ts_start`、`segment_ref=segment.segment_id`、`source="segment"`
  - chat 事件：对每条 chat 匹配（`source: chat`），`ts=chat.ts`、`source="chat"`、`segment_ref=None`
  - 同一文本命中多个 pattern 时全部产出（决策层按优先级取舍）
  - 返回按 `ts` 升序

- [ ] **Step 1: 写失败测试**

`tests/test_event_extractor.py`:
```python
from live_decision_engine.event.extractor import extract_events
from live_decision_engine.schemas.inputs import ChatLine
from live_decision_engine.schemas.stages import Segment


def test_segment_events():
    segs = [
        Segment(segment_id="s_001", ts_start=10.0, ts_end=20.0, text="今天给大家介绍这款裙子，面料很好。", line_refs=[0]),
        Segment(segment_id="s_002", ts_start=30.0, ts_end=40.0, text="最后50件了，拼手速！", line_refs=[1]),
    ]
    events = extract_events(segs, [])
    types = {e.type for e in events}
    assert "product_intro" in types
    assert "selling_point" in types
    assert "scarcity" in types
    assert all(e.source == "segment" for e in events)
    assert events == sorted(events, key=lambda e: e.ts)


def test_chat_events():
    chats = [
        ChatLine(ts=5.0, user="u1", text="这件有L码吗"),
        ChatLine(ts=8.0, user="u2", text="多少钱"),
    ]
    events = extract_events([], chats)
    assert len(events) == 2
    assert all(e.source == "chat" for e in events)
    assert all(e.confidence >= 0.8 for e in events)


def test_no_match_no_events():
    segs = [Segment(segment_id="s_001", ts_start=0.0, ts_end=5.0, text="天气不错。", line_refs=[0])]
    assert extract_events(segs, []) == []


def test_llm_param_accepted():
    segs = [Segment(segment_id="s_001", ts_start=0.0, ts_end=5.0, text="天气不错。", line_refs=[0])]
    assert extract_events(segs, [], llm=object()) == []
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_event_extractor.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 extractor**

`src/live_decision_engine/event/__init__.py`:
```python
from live_decision_engine.event.extractor import extract_events

__all__ = ["extract_events"]
```

`src/live_decision_engine/event/extractor.py`:
```python
import re

from live_decision_engine.rules.loader import load_patterns
from live_decision_engine.schemas.inputs import ChatLine
from live_decision_engine.schemas.stages import LiveEvent, Segment


def extract_events(
    segments: list[Segment],
    chat: list[ChatLine],
    llm=None,
) -> list[LiveEvent]:
    events: list[LiveEvent] = []
    seq = 0

    for pattern in load_patterns():
        if pattern["source"] != "segment":
            continue
        rx = re.compile(pattern["regex"])
        for seg in segments:
            m = rx.search(seg.text)
            if not m:
                continue
            seq += 1
            events.append(
                LiveEvent(
                    event_id=f"e_{seq:04d}",
                    ts=seg.ts_start,
                    type=pattern["event_type"],
                    content=seg.text[max(0, m.start() - 15): m.end() + 15],
                    confidence=pattern["confidence"],
                    source="segment",
                    segment_ref=seg.segment_id,
                )
            )

    for pattern in load_patterns():
        if pattern["source"] != "chat":
            continue
        rx = re.compile(pattern["regex"])
        for line in chat:
            m = rx.search(line.text)
            if not m:
                continue
            seq += 1
            events.append(
                LiveEvent(
                    event_id=f"e_{seq:04d}",
                    ts=line.ts,
                    type=pattern["event_type"],
                    content=line.text,
                    confidence=pattern["confidence"],
                    source="chat",
                )
            )

    if llm is not None and getattr(llm, "available", False):
        from live_decision_engine.event.llm_extractor import enhance_events
        events = enhance_events(events, segments, llm)

    return sorted(events, key=lambda e: e.ts)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_event_extractor.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/event tests/test_event_extractor.py
git commit -m "feat: rule-based event extraction from segments and chat"
```

---

### Task 8: Decision Extraction（规则引擎 + 会话状态）

**Files:**
- Create: `src/live_decision_engine/decision/__init__.py`
- Create: `src/live_decision_engine/decision/state.py`
- Create: `src/live_decision_engine/decision/engine.py`
- Test: `tests/test_decision.py`

**Interfaces:**
- Consumes: `LiveEvent`、`Product`、`DecisionCard`（Task 2）；`load_rules()`、`load_actions()`、`load_action_stages()`（Task 6）
- Produces:
  - `class SessionState`：
    - `__init__(self, products: list[Product])`
    - 字段：`stage: str = "start"`、`current_product: Product | None`、`recent_events: list[LiveEvent]`（保留最近 20 条）、`last_card_ts: dict[str, float]`（action 名 → 上次卡时间戳）
    - `advance(self, event: LiveEvent, stage_map: dict) -> None`：按 `stage_map` 更新 stage（只前进不后退，顺序 `["start","attract","product_intro","try_on","trust","conversion","follow_up"]`）；`recent_events` 追加并裁剪
  - `decide(events: list[LiveEvent], products: list[Product], llm=None) -> list[DecisionCard]`：
    - 遍历事件（时间序）：每事件先 `state.advance`，再按 `rules`（优先级降序）匹配 `when.event_type` 与 `when.keyword`（正则，对事件 content 匹配），命中即选 action
    - 无规则命中 → 阶段兜底：按 `fallback[state.stage]` 顺序取动作（受 30 分钟去重窗口约束，一个事件最多出一张兜底卡）
    - 话术：`actions[action_name]["template"]` 用 `{product}/{price}/{stock}` 占位符填充（取 `state.current_product`）
    - 生成卡：`card_id=f"c_{seq:04d}"`、`timestamp=event.ts`、`stage=state.stage`、`trigger={event_id, segment_id, detail, rule_ref}`、`reason`、`expected_goal` 取自 actions.yaml 的 goal
    - 同 action 30 分钟（1800 秒）窗口内重复 → 跳过（不产出卡）
    - 兜底卡的 `rule_ref="decisions.yaml#fallback"`、`trigger.event_id=None`
    - LLM 可用时（`llm is not None and llm.available`）：`_rewrite_scripts(cards, llm)` 改写 script（保留字段语义）
  - `fill_template(template: str, product: Product | None) -> str`（模块函数）

- [ ] **Step 1: 写失败测试**

`tests/test_decision.py`:
```python
from live_decision_engine.decision.engine import decide
from live_decision_engine.decision.state import SessionState
from live_decision_engine.schemas.inputs import Product
from live_decision_engine.schemas.stages import LiveEvent


PRODUCTS = [
    Product(product_id="p001", name="法式碎花连衣裙", price=129, stock=200, category="连衣裙"),
]


def _evt(ts, etype, content, eid="e_x"):
    return LiveEvent(event_id=eid, ts=ts, type=etype, content=content, confidence=0.9, source="chat")


def test_user_question_size_produces_card():
    events = [_evt(100.0, "user_question", "这件有L码吗", "e_0001")]
    cards = decide(events, PRODUCTS)
    assert len(cards) == 1
    card = cards[0]
    assert card.action.name == "size_question"
    assert card.action.category == "size"
    assert card.trigger.rule_ref == "decisions.yaml#rule_01"
    assert "连衣裙" in card.script  # {product} 已填充
    assert card.trigger.event_id == "e_0001"
    assert card.timestamp == 100.0


def test_price_question_maps_to_comparison():
    events = [_evt(100.0, "user_question", "多少钱", "e_0001")]
    cards = decide(events, PRODUCTS)
    assert cards[0].action.name == "comparison"
    assert "129" in cards[0].script  # {price} 已填充


def test_dedup_window_skips_repeat():
    events = [
        _evt(100.0, "user_question", "这件有L码吗", "e_0001"),
        _evt(120.0, "user_question", "有M码吗", "e_0002"),
    ]
    cards = decide(events, PRODUCTS)
    assert len(cards) == 1  # 20 秒内同 action 去重


def test_dedup_expires_after_30min():
    events = [
        _evt(100.0, "user_question", "这件有L码吗", "e_0001"),
        _evt(2000.0, "user_question", "有M码吗", "e_0002"),
    ]
    cards = decide(events, PRODUCTS)
    assert len(cards) == 2


def test_stage_advance():
    state = SessionState(PRODUCTS)
    stage_map = {"product_intro": "product_intro"}
    state.advance(_evt(10.0, "product_intro", "介绍", "e_0001"), stage_map)
    assert state.stage == "product_intro"


def test_fallback_after_silence():
    # try_on 事件类型无任何规则命中 → 触发阶段兜底
    events = [_evt(100.0, "try_on", "主播试穿展示", "e_0001")]
    cards = decide(events, PRODUCTS)
    assert cards[0].trigger.rule_ref == "decisions.yaml#fallback"
    assert cards[0].action.name == "try_on"  # stage 推进到 try_on 后取 fallback[try_on] 首个候选
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_decision.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 state 与 engine**

`src/live_decision_engine/decision/state.py`:
```python
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
```

`src/live_decision_engine/decision/engine.py`:
```python
import re

from live_decision_engine.decision.state import SessionState
from live_decision_engine.rules.loader import load_actions, load_rules
from live_decision_engine.schemas.cards import ActionRef, DecisionCard, Trigger
from live_decision_engine.schemas.inputs import Product
from live_decision_engine.schemas.stages import LiveEvent

_DEDUP_WINDOW = 1800.0  # 30 分钟


def fill_template(template: str, product: Product | None) -> str:
    if product is None:
        return template
    price = str(int(product.price)) if product.price == int(product.price) else str(product.price)
    return (
        template
        .replace("{product}", product.name)
        .replace("{price}", price)
        .replace("{stock}", str(product.stock))
    )


def decide(
    events: list[LiveEvent],
    products: list[Product],
    llm=None,
) -> list[DecisionCard]:
    rules, fallback, stage_map = load_rules()
    actions = load_actions()
    state = SessionState(products)

    cards: list[DecisionCard] = []
    seq = 0

    for event in events:
        state.advance(event, stage_map)
        matched = _match_rule(rules, event)

        if matched is not None:
            action_name = matched["action"]
            if _within_dedup(state, action_name, event.ts):
                continue
            seq += 1
            cards.append(_build_card(seq, event, state, matched, actions))
        else:
            for action_name in fallback.get(state.stage, []):
                if _within_dedup(state, action_name, event.ts):
                    continue
                seq += 1
                cards.append(_build_fallback_card(seq, event, state, action_name, actions))
                break

    if llm is not None and getattr(llm, "available", False):
        cards = _rewrite_scripts(cards, llm)
    return cards


def _match_rule(rules: list[dict], event: LiveEvent) -> dict | None:
    for rule in sorted(rules, key=lambda r: -r["priority"]):
        when = rule["when"]
        if when["event_type"] != event.type:
            continue
        if "keyword" in when and not re.search(when["keyword"], event.content):
            continue
        return rule
    return None


def _within_dedup(state: SessionState, action_name: str, ts: float) -> bool:
    last = state.last_card_ts.get(action_name)
    return last is not None and ts - last < _DEDUP_WINDOW


def _build_card(seq, event, state, rule, actions) -> DecisionCard:
    action_name = rule["action"]
    action = actions[action_name]
    state.last_card_ts[action_name] = event.ts
    return DecisionCard(
        card_id=f"c_{seq:04d}",
        timestamp=event.ts,
        stage=state.stage,
        action=ActionRef(name=action_name, category=action["category"], goal=action["goal"]),
        trigger=Trigger(
            event_id=event.event_id,
            segment_id=event.segment_ref,
            detail=rule["detail"],
            rule_ref=f"decisions.yaml#{rule['id']}",
        ),
        reason=rule["detail"],
        script=fill_template(action["template"], state.current_product),
        expected_goal=action["goal"],
        quality={"score": 60, "flags": []},  # 占位，Task 9 评分
    )


def _build_fallback_card(seq, event, state, action_name, actions) -> DecisionCard:
    action = actions[action_name]
    state.last_card_ts[action_name] = event.ts
    return DecisionCard(
        card_id=f"c_{seq:04d}",
        timestamp=event.ts,
        stage=state.stage,
        action=ActionRef(name=action_name, category=action["category"], goal=action["goal"]),
        trigger=Trigger(
            event_id=None, segment_id=None,
            detail="阶段兜底", rule_ref="decisions.yaml#fallback",
        ),
        reason=f"阶段兜底（stage={state.stage}）",
        script=fill_template(action["template"], state.current_product),
        expected_goal=action["goal"],
        quality={"score": 60, "flags": []},
    )


def _rewrite_scripts(cards, llm) -> list[DecisionCard]:
    _system = "你是直播间运营。把话术改写得更自然口语，保留原有意图，只输出 JSON：{\"script\": \"...\"}。"
    out = []
    for card in cards:
        payload = llm.chat_json(_system, f"当前阶段: {card.stage}\n原话术: {card.script}")
        if payload and payload.get("script"):
            card = card.model_copy(update={"script": payload["script"]})
        out.append(card)
    return out
```

`src/live_decision_engine/decision/__init__.py`:
```python
from live_decision_engine.decision.engine import decide, fill_template
from live_decision_engine.decision.state import SessionState

__all__ = ["SessionState", "decide", "fill_template"]
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_decision.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/decision tests/test_decision.py
git commit -m "feat: rule-based decision engine with session state and dedup window"
```

---

### Task 9: Validation（Quality Scoring）

**Files:**
- Create: `src/live_decision_engine/validation/__init__.py`
- Create: `src/live_decision_engine/validation/scorer.py`
- Test: `tests/test_validation.py`

**Interfaces:**
- Consumes: `DecisionCard`（Task 2）、`load_action_stages()`（Task 6）
- Produces: `score_cards(cards: list[DecisionCard], llm=None) -> list[DecisionCard]`——每张卡重新计算 `quality`，返回**评分 ≥ 60 的卡**（顺序不变）；LLM 可用时用评委分与规则分取平均

**打分公式**（确定性）：
```
base = 60
if confidence >= 0.85: +15
elif confidence >= 0.7: +5
else: -10, flag "low_confidence"
if card.stage in action_stages[action.name]: +15
else: -20, flag "stage_mismatch"
if rule_ref 含 "fallback": flag "fallback"（不扣分——否则兜底卡 55 分会被阈值过滤，兜底机制失效）
score = clamp(0, 100)
```
- `_confidence_of(card)`：`trigger.event_id is None`（兜底卡）→ 0.5；否则 0.9（简化近似，见自审记录）
- `score < 60` 的卡从输出剔除

- [ ] **Step 1: 写失败测试**

`tests/test_validation.py`:
```python
from live_decision_engine.schemas.cards import ActionRef, DecisionCard, Quality, Trigger
from live_decision_engine.validation.scorer import score_cards


def _card(cid, stage, action_name, category, confidence=0.9, rule_ref="decisions.yaml#rule_01"):
    trigger = Trigger(
        event_id="e_0001" if confidence >= 0.7 else None,
        segment_id="s_001",
        detail="d",
        rule_ref=rule_ref,
    )
    return DecisionCard(
        card_id=cid,
        timestamp=100.0,
        stage=stage,
        action=ActionRef(name=action_name, category=category, goal="g"),
        trigger=trigger,
        reason="r",
        script="s",
        expected_goal="g",
        quality=Quality(score=60, flags=[]),
    )


def test_high_confidence_matching_stage_scores_high():
    card = _card("c_0001", "product_intro", "size_question", "size")  # 60+15+15=90
    out = score_cards([card])
    assert out[0].quality.score == 90
    assert out[0].quality.flags == []


def test_low_confidence_flagged():
    card = _card("c_0001", "product_intro", "size_question", "size", confidence=0.5)  # 60+(-10)+15=65
    out = score_cards([card])
    assert out[0].quality.score == 65
    assert "low_confidence" in out[0].quality.flags


def test_stage_mismatch_penalized():
    card = _card("c_0001", "start", "size_question", "size")  # size_question 不适配 start: 60+15-20=55 → 剔除
    out = score_cards([card])
    assert out == []


def test_fallback_flagged_not_discarded():
    # 真实兜底卡：event_id=None → confidence 0.5，rule_ref 含 fallback
    trigger = Trigger(event_id=None, segment_id=None, detail="阶段兜底", rule_ref="decisions.yaml#fallback")
    card = DecisionCard(
        card_id="c_0001", timestamp=100.0, stage="try_on",
        action=ActionRef(name="try_on", category="selling", goal="g"),
        trigger=trigger, reason="r", script="s", expected_goal="g",
        quality=Quality(score=60, flags=[]),
    )
    out = score_cards([card])
    # 60-10(low confidence)+15(stage 匹配 try_on∈[try_on])=65 → 保留，且带 fallback flag
    assert out[0].quality.score == 65
    assert "fallback" in out[0].quality.flags


def test_score_floor_60():
    card = _card("c_0001", "product_intro", "size_question", "size", confidence=0.5)  # 65 → 保留
    out = score_cards([card])
    assert len(out) == 1
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_validation.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 scorer**

`src/live_decision_engine/validation/__init__.py`:
```python
from live_decision_engine.validation.scorer import score_cards

__all__ = ["score_cards"]
```

`src/live_decision_engine/validation/scorer.py`:
```python
from live_decision_engine.rules.loader import load_action_stages
from live_decision_engine.schemas.cards import DecisionCard, Quality

THRESHOLD = 60


def _confidence_of(card: DecisionCard) -> float:
    return 0.5 if card.trigger.event_id is None else 0.9


def score_cards(cards: list[DecisionCard], llm=None) -> list[DecisionCard]:
    action_stages = load_action_stages()
    out: list[DecisionCard] = []

    for card in cards:
        score = 60
        flags: list[str] = []

        conf = _confidence_of(card)
        if conf >= 0.85:
            score += 15
        elif conf >= 0.7:
            score += 5
        else:
            score -= 10
            flags.append("low_confidence")

        if card.stage in action_stages.get(card.action.name, []):
            score += 15
        else:
            score -= 20
            flags.append("stage_mismatch")

        if "fallback" in card.trigger.rule_ref:
            # 只标记不扣分：兜底卡本身置信低（0.5），再扣分会全部低于阈值
            flags.append("fallback")

        score = max(0, min(100, score))
        if score < THRESHOLD:
            continue
        out.append(
            card.model_copy(
                update={"quality": Quality(score=score, flags=flags)}
            )
        )

    if llm is not None and getattr(llm, "available", False):
        out = _judge_adjust(out, llm)
    return out


def _judge_adjust(cards, llm) -> list[DecisionCard]:
    _system = "你是直播运营质量评委。给决策卡打 0-100 分，只输出 JSON：{\"score\": 0-100}。"
    adjusted = []
    for card in cards:
        payload = llm.chat_json(
            _system,
            f"阶段: {card.stage}\n动作: {card.action.name}\n理由: {card.reason}\n话术: {card.script}",
        )
        if payload and isinstance(payload.get("score"), (int, float)):
            llm_score = int(payload["score"])
            avg = round((card.quality.score + llm_score) / 2)
            card = card.model_copy(
                update={"quality": card.quality.model_copy(update={"score": avg})}
            )
        adjusted.append(card)
    return adjusted
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_validation.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/live_decision_engine/validation tests/test_validation.py
git commit -m "feat: quality scorer with threshold filter"
```

---

### Task 10: Pipeline 编排 + CLI + 集成测试

**Files:**
- Create: `src/live_decision_engine/pipeline.py`
- Create: `src/live_decision_engine/cli.py`
- Test: `tests/test_pipeline.py`（集成测试）

**Interfaces:**
- Consumes: 全部层（Task 3–9）
- Produces:
  - `run_pipeline(session_dir: Path, from_stage: str | None = None, llm: bool = False, out_dir: Path | None = None) -> dict`
    - `out_dir=None` 时默认 `session_dir/output`
    - 按需执行各层并写 `stages/01_cleaned.jsonl` → `02_segments.jsonl` → `03_events.jsonl` → `04_cards.jsonl`；写 `summary.txt`
    - `from_stage` 语义：`None`=全流程；`"01"`=从 cleaning 产物开始（读 01 文件）；`"02"`=从 segmentation 产物开始；`"03"`=从 event 产物开始；`"04"`=从 decision 层开始（读 03_events 重跑 decision+validation）；其他值抛 `ValueError`
    - 返回 `{"cards": list[DecisionCard], "counts": {"cards": int, "score_avg": float}, "summary": str}`
  - `write_jsonl(path: Path, items)` / `read_jsonl(path: Path, model) -> list`（模块函数）
  - `cli.py`: typer `app`；命令 `validate(session_dir)`、`run(session_dir, from_stage: str | None = typer.Option(None, "--from"), llm: bool = typer.Option(False, "--llm"))`

- [ ] **Step 1: 写失败测试**

`tests/test_pipeline.py`:
```python
from pathlib import Path

import pytest

from live_decision_engine.pipeline import run_pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "session_mini"


def test_full_pipeline_writes_stages(tmp_path):
    result = run_pipeline(FIXTURE, out_dir=tmp_path)
    stages = tmp_path / "stages"
    assert (stages / "01_cleaned.jsonl").exists()
    assert (stages / "02_segments.jsonl").exists()
    assert (stages / "03_events.jsonl").exists()
    assert (stages / "04_cards.jsonl").exists()
    assert (tmp_path / "summary.txt").exists()
    assert isinstance(result["cards"], list)
    for card in result["cards"]:
        assert card.quality.score >= 60


def test_from_stage_03(tmp_path):
    run_pipeline(FIXTURE, out_dir=tmp_path)
    first = run_pipeline(FIXTURE, out_dir=tmp_path)
    again = run_pipeline(FIXTURE, from_stage="03", out_dir=tmp_path)
    # 03 之后逻辑相同，两次跑出的卡应一致（幂等）
    assert [c.card_id for c in again["cards"]] == [c.card_id for c in first["cards"]]


def test_invalid_from_stage(tmp_path):
    with pytest.raises(ValueError):
        run_pipeline(FIXTURE, from_stage="99", out_dir=tmp_path)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_pipeline.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 pipeline 与 cli**

`src/live_decision_engine/pipeline.py`:
```python
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
```

`src/live_decision_engine/cli.py`:
```python
from pathlib import Path

import typer

from live_decision_engine.ingestion.adapter import validate_session
from live_decision_engine.pipeline import run_pipeline

app = typer.Typer(add_completion=False)


@app.command()
def validate(session_dir: Path):
    """校验 session 目录的四件套输入。"""
    errors = validate_session(session_dir)
    if errors:
        for e in errors:
            typer.echo(f"[FAIL] {e}", err=True)
        raise typer.Exit(1)
    typer.echo(f"[OK] {session_dir} 输入合法")


@app.command()
def run(
    session_dir: Path,
    from_stage: str | None = typer.Option(None, "--from", help="从某层开始重跑：01/02/03/04"),
    llm: bool = typer.Option(False, "--llm", help="启用 LLM 增强（需配置 LDE_LLM_* 环境变量）"),
):
    """跑完一场直播的完整决策管线。"""
    try:
        result = run_pipeline(session_dir, from_stage=from_stage, llm=llm)
    except Exception as e:
        typer.echo(f"[ERROR] {e}", err=True)
        raise typer.Exit(1)

    typer.echo(result["summary"])
    typer.echo(
        f"总计: {result['counts']['cards']} 张卡片, "
        f"平均分 {result['counts']['score_avg']}"
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/pytest tests/test_pipeline.py -v`
Expected: 3 passed

- [ ] **Step 5: 手动验证 CLI**

```bash
cd /home/wentworth/Developer/ultimate/Live_Decisiion_Engine
.venv/bin/live-decision validate tests/fixtures/session_mini
.venv/bin/live-decision run tests/fixtures/session_mini
```
Expected: validate 输出 `[OK]`；run 输出 summary 与统计，退出码 0

- [ ] **Step 6: Commit**

```bash
git add src/live_decision_engine/pipeline.py src/live_decision_engine/cli.py tests/test_pipeline.py
git commit -m "feat: pipeline orchestration, CLI and integration tests"
```

---

### Task 11: LLM 可选增强

**Files:**
- Create: `src/live_decision_engine/llm.py`
- Create: `src/live_decision_engine/event/llm_extractor.py`
- Modify: `src/live_decision_engine/event/extractor.py`（`extract_events` 内 `llm` 可用时调用增强）
- Modify: `src/live_decision_engine/decision/engine.py`（`decide` 内 LLM 改写 script——Task 8 已实现 `_rewrite_scripts` 与接入，本任务验证）
- Modify: `src/live_decision_engine/validation/scorer.py`（`score_cards` 内 LLM 评委——Task 9 已实现 `_judge_adjust` 与接入，本任务验证）
- Test: `tests/test_llm.py`（全部 mock，不发起真实请求）

**Interfaces:**
- Produces:
  - `class LLMClient`：
    - `__init__(api_key=None, base_url=None, model=None)`；默认读 `LDE_LLM_API_KEY` / `LDE_LLM_BASE_URL` / `LDE_LLM_MODEL`
    - `available: bool`（无 key 或 openai 未安装 → False）
    - `chat_json(system: str, user: str) -> dict | None`——请求 JSON 输出；解析失败/异常返回 None（绝不抛异常）
  - `enhance_events(events: list[LiveEvent], segments: list[Segment], llm) -> list[LiveEvent]`——segments 分批（每批 5 个）LLM 提取补充事件；与规则事件按 `(ts, type)` 去重（`abs(ts 差) < 1.0`）取置信度高者；返回按 `ts` 升序

- [ ] **Step 1: 写失败测试（全部 mock）**

`tests/test_llm.py`:
```python
import pytest

from live_decision_engine.event.extractor import extract_events
from live_decision_engine.llm import LLMClient
from live_decision_engine.schemas.stages import Segment


class FakeLLM:
    available = True

    def chat_json(self, system: str, user: str) -> dict | None:
        return {"events": [{"ts": 40.0, "type": "selling_point", "content": "面料是冰丝的", "confidence": 0.95}]}


class FailingLLM:
    available = True

    def chat_json(self, system: str, user: str) -> dict | None:
        return None


def test_llm_client_env_parsing(monkeypatch):
    monkeypatch.setenv("LDE_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LDE_LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LDE_LLM_MODEL", "deepseek-chat")
    client = LLMClient()
    assert client.api_key == "sk-test"
    assert client.base_url == "https://api.example.com/v1"
    assert client.model == "deepseek-chat"


def test_llm_client_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("LDE_LLM_API_KEY", raising=False)
    client = LLMClient()
    assert client.available is False


def test_enhance_events_merges_and_dedups():
    segs = [Segment(segment_id="s_001", ts_start=40.0, ts_end=50.0, text="这个面料是冰丝的。", line_refs=[0])]
    events = extract_events(segs, [], llm=FakeLLM())
    ev = next(e for e in events if e.type == "selling_point" and e.ts == 40.0)
    assert ev.confidence == 0.95  # LLM 0.95 > 规则 0.8，去重后保留 LLM


def test_llm_failure_falls_back_to_rules():
    segs = [Segment(segment_id="s_001", ts_start=40.0, ts_end=50.0, text="这个面料是冰丝的。", line_refs=[0])]
    events = extract_events(segs, [], llm=FailingLLM())
    assert any(e.type == "selling_point" for e in events)  # 规则结果仍在


def test_decision_llm_rewrites_script():
    from live_decision_engine.decision.engine import decide
    from live_decision_engine.schemas.inputs import Product
    from live_decision_engine.schemas.stages import LiveEvent

    class ScriptLLM:
        available = True

        def chat_json(self, system, user):
            return {"script": "姐妹们，这件连衣裙有 L 码，报身高体重我帮你选！"}

    products = [Product(product_id="p001", name="法式碎花连衣裙", price=129, stock=200, category="连衣裙")]
    events = [LiveEvent(event_id="e_0001", ts=100.0, type="user_question", content="这件有L码吗", confidence=0.9, source="chat")]
    cards = decide(events, products, llm=ScriptLLM())
    assert cards[0].script == "姐妹们，这件连衣裙有 L 码，报身高体重我帮你选！"


def test_validation_llm_judge_adjusts_score():
    from live_decision_engine.schemas.cards import ActionRef, DecisionCard, Quality, Trigger
    from live_decision_engine.validation.scorer import score_cards

    class JudgeLLM:
        available = True

        def chat_json(self, system, user):
            return {"score": 70}

    card = DecisionCard(
        card_id="c_0001", timestamp=100.0, stage="product_intro",
        action=ActionRef(name="size_question", category="size", goal="g"),
        trigger=Trigger(event_id="e_0001", segment_id="s_001", detail="d", rule_ref="decisions.yaml#rule_01"),
        reason="r", script="s", expected_goal="g", quality=Quality(score=60, flags=[]),
    )
    out = score_cards([card], llm=JudgeLLM())
    # 规则分 90（60+15+15），评委 70 → 平均 80
    assert out[0].quality.score == 80
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/pytest tests/test_llm.py -v`
Expected: FAIL（ModuleNotFoundError: live_decision_engine.llm）

- [ ] **Step 3: 实现 llm.py**

`src/live_decision_engine/llm.py`:
```python
import json
import os

DEFAULT_MODEL = "deepseek-chat"


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("LDE_LLM_API_KEY")
        self.base_url = base_url or os.getenv("LDE_LLM_BASE_URL")
        self.model = model or os.getenv("LDE_LLM_MODEL") or DEFAULT_MODEL
        self._client = None
        self.available = False
        if not self.api_key:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.available = True
        except ImportError:
            self.available = False

    def chat_json(self, system: str, user: str) -> dict | None:
        if not self.available or self._client is None:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception:
            return None
```

`src/live_decision_engine/event/llm_extractor.py`:
```python
from live_decision_engine.schemas.stages import LiveEvent, Segment

_SYSTEM = (
    "你是直播运营分析器。从直播转录文本中提取结构化事件，只输出 JSON："
    '{"events": [{"ts": 秒, "type": "类型", "content": "原文片段", "confidence": 0-1}]}。'
    "类型只能是: user_question, product_intro, selling_point, promotion, try_on, "
    "interaction_prompt, scarcity, conversion_call, price_mention。"
)

_BATCH = 5


def enhance_events(
    events: list[LiveEvent],
    segments: list[Segment],
    llm,
) -> list[LiveEvent]:
    if llm is None or not getattr(llm, "available", False):
        return events

    for i in range(0, len(segments), _BATCH):
        batch = segments[i:i + _BATCH]
        text = "\n".join(f"[{s.ts_start:.1f}s] {s.text}" for s in batch)
        payload = llm.chat_json(_SYSTEM, f"转录文本:\n{text}")
        if not payload or "events" not in payload:
            continue
        for raw in payload["events"]:
            try:
                cand = LiveEvent(
                    event_id=f"e_llm_{i}_{raw.get('ts', 0)}",
                    ts=float(raw["ts"]),
                    type=raw["type"],
                    content=str(raw["content"]),
                    confidence=float(raw["confidence"]),
                    source="segment",
                    segment_ref=batch[0].segment_id,
                )
            except Exception:
                continue
            # (ts, type) 去重，取置信度高者
            replaced = False
            for j, existing in enumerate(events):
                if abs(existing.ts - cand.ts) < 1.0 and existing.type == cand.type:
                    if cand.confidence > existing.confidence:
                        events[j] = cand
                    replaced = True
                    break
            if not replaced:
                events.append(cand)

    return sorted(events, key=lambda e: e.ts)
```

- [ ] **Step 4: 确认各层接入完整**

- `event/extractor.py`：Task 7 Step 3 已含 `if llm is not None and getattr(llm, "available", False):` 分支调用 `enhance_events`（无需改动）
- `decision/engine.py`：Task 8 已含 `_rewrite_scripts` 与 `decide` 尾部接入（无需改动）
- `validation/scorer.py`：Task 9 已含 `_judge_adjust` 与 `score_cards` 尾部接入（无需改动）

- [ ] **Step 5: 运行确认通过**

Run: `.venv/bin/pytest tests/test_llm.py -v`
Expected: 6 passed

Run: `.venv/bin/pytest -q`
Expected: 全量测试通过（回归）

- [ ] **Step 6: Commit**

```bash
git add src/live_decision_engine/llm.py src/live_decision_engine/event/llm_extractor.py tests/test_llm.py
git commit -m "feat: optional LLM enhancement for event/decision/validation"
```

---

### Task 12: demo 数据构建（真实脱敏 + 合成弹幕）

**Files:**
- Create: `scripts/build_demo_data.py`
- Create（生成产物，`demo/session_001/*` 四件套入 git；`demo/*/output/` 已被 .gitignore 排除）: `demo/session_001/transcript.jsonl`、`demo/session_001/chat.jsonl`、`demo/session_001/products.json`、`demo/session_001/metadata.json`

**Interfaces:**
- Produces: `demo/session_001/` 四件套，可通过 `validate_session` 校验

**构建规则**：
- 参数：`--source-vtt`（默认 `/home/wentworth/Developer/python_projects/stream-script-kb/data/transcripts/livestream_20260713.vtt`）、`--out`（默认 `demo/session_001`）、`--max-minutes`（默认 25.0）
- VTT 解析：跳过 `WEBVTT` 头与空行；时间戳行 `HH:MM:SS.mmm --> HH:MM:SS.mmm` 解析为秒；块内多行文本合并；只保留 `ts_start < max_minutes * 60` 的块
- 脱敏词表：`时尚任意门→夏日专场`、`三亚→海滨`、`上海→城市`、粉丝昵称（`小窝头/苏朵/棉花糖`）→`粉丝`
- products.json：内置 4 个脱敏女装商品（不解析 enriched.json，避免脆弱依赖）
- chat.jsonl：合成 40 条弹幕（模板池轮转），`ts` 均匀散布在窗口内，`user` 为 `user_{001..040}`
- metadata.json：`{"session_id": "session_001", "platform": "taobao", "category": "女装", "recorded_at": "2026-07-13T08:00:00+08:00", "source": "real_desensitized"}`
- 幂等：直接覆盖输出文件

- [ ] **Step 1: 写构建脚本**

`scripts/build_demo_data.py`:
```python
#!/usr/bin/env python
"""一次性构建 demo/session_001 四件套：真实 VTT 脱敏 + 合成弹幕。"""
import argparse
import json
import re
from pathlib import Path

VTT_BLOCK = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})\.(\d{3})"
)

REDACT = {
    "时尚任意门": "夏日专场",
    "三亚": "海滨",
    "上海": "城市",
    "小窝头": "粉丝",
    "苏朵": "粉丝",
    "棉花糖": "粉丝",
}

PRODUCTS = [
    {"product_id": "p001", "name": "法式碎花连衣裙", "price": 129, "stock": 200, "category": "连衣裙"},
    {"product_id": "p002", "name": "纯色防晒衬衫", "price": 89, "stock": 150, "category": "衬衫"},
    {"product_id": "p003", "name": "高腰阔腿裤", "price": 119, "stock": 100, "category": "裤装"},
    {"product_id": "p004", "name": "度假风针织开衫", "price": 159, "stock": 80, "category": "外套"},
]

CHAT_TEMPLATES = [
    "主播这件有L码吗",
    "多少钱啊",
    "这个面料怎么样",
    "刚进来，今天卖什么",
    "扣1支持",
    "这个颜色好看",
    "可以发顺丰吗",
    "已拍！",
    "主播多高啊",
    "这个会显瘦吗",
    "有白色吗",
    "链接在哪里",
]

METADATA = {
    "session_id": "session_001",
    "platform": "taobao",
    "category": "女装",
    "recorded_at": "2026-07-13T08:00:00+08:00",
    "source": "real_desensitized",
}


def parse_vtt(path: Path, max_seconds: float) -> list[dict]:
    lines_out = []
    with path.open(encoding="utf-8") as f:
        text_parts = []
        ts_start = ts_end = None
        for raw in f:
            line = raw.strip()
            m = VTT_BLOCK.match(line)
            if m:
                if text_parts and ts_start is not None:
                    lines_out.append({
                        "ts_start": ts_start,
                        "ts_end": ts_end,
                        "text": "".join(text_parts),
                    })
                g = m.groups()
                ts_start = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
                ts_end = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
                text_parts = []
            elif line and line != "WEBVTT" and ts_start is not None:
                text_parts.append(line)
        if text_parts and ts_start is not None:
            lines_out.append({"ts_start": ts_start, "ts_end": ts_end, "text": "".join(text_parts)})
    return [l for l in lines_out if l["ts_start"] < max_seconds]


def redact(text: str) -> str:
    for src, dst in REDACT.items():
        text = text.replace(src, dst)
    return text


def build_chat(max_seconds: float) -> list[dict]:
    n = 40
    out = []
    for i in range(n):
        ts = round((i + 0.5) * max_seconds / n, 1)
        out.append({"ts": ts, "user": f"user_{i + 1:03d}", "text": CHAT_TEMPLATES[i % len(CHAT_TEMPLATES)]})
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-vtt",
        default="/home/wentworth/Developer/python_projects/stream-script-kb/data/transcripts/livestream_20260713.vtt",
    )
    parser.add_argument("--out", default="demo/session_001")
    parser.add_argument("--max-minutes", type=float, default=25.0)
    args = parser.parse_args()

    max_seconds = args.max_minutes * 60
    vtt_lines = parse_vtt(Path(args.source_vtt), max_seconds)
    transcript = [
        {"ts_start": l["ts_start"], "ts_end": l["ts_end"], "text": redact(l["text"])}
        for l in vtt_lines
    ]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "transcript.jsonl").open("w", encoding="utf-8") as f:
        for l in transcript:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")

    with (out_dir / "chat.jsonl").open("w", encoding="utf-8") as f:
        for l in build_chat(max_seconds):
            f.write(json.dumps(l, ensure_ascii=False) + "\n")

    (out_dir / "products.json").write_text(
        json.dumps(PRODUCTS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "metadata.json").write_text(
        json.dumps(METADATA, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"transcript: {len(transcript)} 行（前 {args.max_minutes} 分钟，脱敏后）")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本生成 demo 数据**

```bash
cd /home/wentworth/Developer/ultimate/Live_Decisiion_Engine
python scripts/build_demo_data.py
head -3 demo/session_001/transcript.jsonl
grep -c "时尚任意门" demo/session_001/transcript.jsonl || true
```
Expected: 输出 transcript 行数；head 显示合法 JSON；grep 输出 0（脱敏生效）

- [ ] **Step 3: 校验并跑通 demo**

```bash
.venv/bin/live-decision validate demo/session_001
.venv/bin/live-decision run demo/session_001
```
Expected: validate 输出 `[OK]`；run 输出卡片摘要与统计，退出码 0；`demo/session_001/output/stages/04_cards.jsonl` 非空且每行合法 JSON

- [ ] **Step 4: Commit 四件套（不含 output）**

```bash
git add scripts/build_demo_data.py demo/session_001/transcript.jsonl demo/session_001/chat.jsonl demo/session_001/products.json demo/session_001/metadata.json
git commit -m "feat: demo session_001 with desensitized real transcript and synthetic chat"
```

---

### Task 13: 文档与最终验证

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `examples/README.md`

**Interfaces:**
- Produces: 可对外发布的文档（README 英文为主，architecture.md 含管线图与 schema）

- [ ] **Step 1: 写 README**

`README.md`:
```markdown
# Live Decision Engine

Turn one livestream session into a set of auditable decision cards.

Pipeline: `ingestion → cleaning → segmentation → event extraction → decision extraction → quality scoring`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

```bash
live-decision validate demo/session_001
live-decision run demo/session_001
# resume from a specific stage (01 cleaned / 02 segments / 03 events / 04 cards)
live-decision run demo/session_001 --from 03
```

Output: `demo/session_001/output/stages/*.jsonl` (per-stage artifacts) and `output/summary.txt`.

## Optional LLM enhancement

Rules run by default with zero external dependencies. Set these env vars to
upgrade event extraction, script rewriting and quality judging:

```bash
export LDE_LLM_API_KEY=sk-...
export LDE_LLM_BASE_URL=https://api.deepseek.com/v1
export LDE_LLM_MODEL=deepseek-chat
live-decision run demo/session_001 --llm
```

## Session data format

A session directory contains four files: `transcript.jsonl` (host speech),
`chat.jsonl` (audience messages), `products.json` (products on show) and
`metadata.json` (session meta). See `docs/architecture.md` for the schema.

## Tests

```bash
pytest -q
```

## License

MIT
```

- [ ] **Step 2: 写 architecture.md**

`docs/architecture.md`——从规格 `docs/superpowers/specs/2026-08-10-live-decision-engine-design.md` 第 3、5、6 节提取：管线图、四件套 schema、中间产物 schema、Decision Card schema、stage/event 枚举、打分公式、错误处理、测试策略。内容照抄规格对应节（无需改写），保留全部 JSON 示例与枚举。

- [ ] **Step 3: 写 examples/README.md**

`examples/README.md`:
```markdown
# Examples

## Run the demo session

```bash
live-decision run ../demo/session_001
```

## Build a new session from a VTT transcript

```bash
python ../scripts/build_demo_data.py --source-vtt /path/to/live.vtt --out ../demo/session_002 --max-minutes 30
```

## Validate input before running

```bash
live-decision validate ../demo/session_001
```
```

- [ ] **Step 4: 全量验证**

```bash
cd /home/wentworth/Developer/ultimate/Live_Decisiion_Engine
.venv/bin/pytest -q
.venv/bin/live-decision run demo/session_001 --from 01
.venv/bin/live-decision run demo/session_001 --from 03
```
Expected: 全部测试通过；两次 run 均退出码 0 且结果一致（幂等重跑）

- [ ] **Step 5: Commit**

```bash
git add README.md docs/architecture.md examples/README.md
git commit -m "docs: README, architecture doc and examples"
```

---

## 自审记录（写入计划前已核对）

- **规格覆盖**：四件套契约（T2/T3）、七层管线（T3–T9）、中间产物落盘与 `--from` 重跑（T10）、Decision Card schema（T2/T8/T9）、规则外部化 YAML（T6）、LLM 可选（T11）、demo 真实脱敏 + 合成弹幕（T12）、文档（T13）、测试（各任务 TDD + T10 集成）。规格"无 DB/无 RAG/无 UI/无采集"约束在 Global Constraints 与任务中均未引入。
- **类型一致性**：`extract_events(segments, chat, llm=None)`（T7 定义，T11 复用）；`decide(events, products, llm=None)`（T8 定义，T11 复用）；`score_cards(cards, llm=None)`（T9 定义，T11 复用）；`run_pipeline(session_dir, from_stage, llm, out_dir)`（T10 定义，CLI 与测试复用）。pydantic 模型名全项目唯一。
- **已知简化**：T9 `_confidence_of` 以 event_id 有无近似置信度（卡体未携带原始置信度），T11 的 LLM 评委机制可弥补；如需精确置信度，后续可在卡 schema 增加 `confidence` 字段（属规格外扩展，不在本计划内）。
- **自审修正（均已内联修复）**：
  1. 兜底卡打分：原公式"fallback 扣 10 分"使兜底卡（置信 0.5）恒得 55 分被阈值过滤，兜底机制失效 → 改为只打 `fallback` flag 不扣分
  2. 兜底触发条件："最近 3 事件无命中"不可达（9 种事件类型中 8 种有规则，仅 try_on 无规则）→ 改为"当前事件无规则命中即触发阶段兜底"
  3. `test_from_stage_03` 原断言 `>= 0` 恒真 → 改为与全流程结果对比 card_id 列表一致（幂等验证）
  4. actions.yaml 三处模板被压缩改写 → 恢复原项目原文（忠实移植）
