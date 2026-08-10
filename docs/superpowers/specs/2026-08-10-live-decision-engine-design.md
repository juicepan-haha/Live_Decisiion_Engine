# Live Decision Engine 设计文档

日期：2026-08-10
状态：已批准（用户确认各节设计）

## 1. 背景与目标

stream-script-kb 是此前摸索期项目（约 5500 行），包含批处理管线、Agent 决策层、反馈闭环等模块，存在单文件混杂、硬编码路径、无统一契约等问题。本设计将其正式化，另起新项目 **Live_Decisiion_Engine**（包名 `live-decision-engine`），作为开源最小 Demo：

**核心目标**：把"一场直播"跑通为"一组高质量 Decision Cards"。

**成功标准**：
- `pip install` 后 clone 即可跑通 demo（无 API key 也能完整运行）
- 每层中间产物落盘，可审计、可追溯每张卡片的决策依据
- 规则为主、LLM 可选：配了 key 输出质量升级，不配也能跑

## 2. 范围

### 做
- 输入：session 数据包（四件套：transcript/chat/products/metadata）
- 管线：ingestion → cleaning → segmentation → event → decision → validation
- 输出：Decision Cards（JSONL）+ 终端摘要
- 规则引擎（YAML 规则表）+ 可选 LLM 增强
- demo 示例数据（真实数据脱敏 + 合成弹幕）

### 不做（YAGNI）
- 无数据库 / 无 RAG / 无搜索
- 无实时流（模块接口保留流式形状，但 demo 为离线批处理）
- 无 UI（输出为 JSONL + 终端摘要）
- 无采集 / ASR 层（输入即数据包；ingestion 是未来扩展适配器的位置）
- 无反馈闭环 / 回放（后续阶段再做）

## 3. 总体架构

```
直播数据包 (session 四件套)
   ↓
[ingestion]  Data Adapter：读取 + pydantic 校验
   ↓
[cleaning]   转录清洗（语气词/重复/碎片合并）
   ↓
[segmentation] 语义切块（500-1000 字符，句末标点）
   ↓
[event]      Event Extraction（规则模式库 + 可选 LLM）
   ↓
[decision]   Decision Extraction（YAML 规则表 + 轻量会话状态 + 动作库）
   ↓
[validation] Quality Scoring（打分 + flags + 阈值过滤）
   ↓
Decision Cards (output/stages/04_cards.jsonl + summary.txt)
```

每层独立，输出落盘到 `output/stages/`，`--from <stage>` 支持从任意层重跑。分层之间严格走文件，不共享内存状态（decision 层内部维护会话状态除外）。

## 4. 目录结构

```
Live_Decisiion_Engine/
├── README.md
├── LICENSE
├── pyproject.toml
├── src/live_decision_engine/
│   ├── __init__.py
│   ├── cli.py                # typer CLI 入口
│   ├── llm.py                # OpenAI 兼容客户端（可选）
│   ├── pipeline.py           # 分层编排器
│   ├── ingestion/
│   │   ├── adapter.py        # 读四件套 + 校验
│   ├── cleaning/
│   │   ├── cleaner.py        # 转录清洗
│   ├── segmentation/
│   │   ├── segmenter.py      # 语义切块
│   ├── event/
│   │   ├── extractor.py      # 事件提取（规则）
│   │   ├── llm_extractor.py  # 事件提取（LLM 可选）
│   ├── decision/
│   │   ├── engine.py         # 规则引擎 + 会话状态
│   │   ├── state.py          # 轻量会话状态
│   ├── validation/
│   │   ├── scorer.py         # 质量打分
│   ├── rules/
│   │   ├── patterns.yaml     # 事件模式库
│   │   ├── decisions.yaml    # 决策规则表
│   │   └── actions.yaml      # 动作库（移植原项目 14 动作 4 类）
│   └── schemas/
│       ├── inputs.py         # 四件套模型
│       ├── stages.py         # 中间产物模型
│       └── cards.py          # Decision Card 模型
├── demo/session_001/
│   ├── transcript.jsonl
│   ├── chat.jsonl
│   ├── products.json
│   ├── metadata.json
│   └── output/
│       ├── stages/
│       │   ├── 01_cleaned.jsonl
│       │   ├── 02_segments.jsonl
│       │   ├── 03_events.jsonl
│       │   └── 04_cards.jsonl
│       └── summary.txt
├── scripts/
│   └── build_demo_data.py   # 一次性：真实 VTT → 脱敏四件套
├── examples/                # 用法示例
├── tests/                   # 单元 + 集成测试
└── docs/
    └── architecture.md
```

## 5. 数据契约（Schema）

所有层间契约用 pydantic 模型定义在 `schemas/`。

### 输入四件套

**transcript.jsonl**（每行）：
```json
{"ts_start": 0.0, "ts_end": 2.44, "text": "大清早的"}
```
text 必填，时间戳为秒。

**chat.jsonl**（每行）：
```json
{"ts": 123.5, "user": "user_3f2a", "text": "主播这件有L码吗"}
```

**products.json**：
```json
[{"product_id": "p001", "name": "法式碎花连衣裙", "price": 129, "stock": 200, "category": "连衣裙"}]
```

**metadata.json**：
```json
{"session_id": "session_001", "platform": "taobao", "category": "女装", "recorded_at": "2026-07-13T08:00:00+08:00", "source": "real_desensitized"}
```

### 中间产物

**01_cleaned.jsonl**：`{"ts_start", "ts_end", "text", "origin"}`（origin 保留原文，可追溯）

**02_segments.jsonl**：
```json
{"segment_id": "s_001", "ts_start": 0.0, "ts_end": 187.16, "text": "...", "line_refs": [0, 1, 2]}
```

**03_events.jsonl**：
```json
{"event_id": "e_001", "ts": 123.5, "type": "user_question", "content": "主播这件有L码吗", "confidence": 0.9, "source": "chat", "segment_ref": "s_012"}
```
事件类型枚举：`user_question / product_intro / selling_point / promotion / try_on / interaction_prompt / scarcity / conversion_call / price_mention`

### Decision Card（04_cards.jsonl）

```json
{
  "card_id": "c_0001",
  "timestamp": 1234.5,
  "stage": "product_intro",
  "action": {"name": "size_question", "category": "size", "goal": "降低尺码顾虑"},
  "trigger": {"event_id": "e_001", "segment_id": "s_012", "detail": "连续3条弹幕询问尺码", "rule_ref": "decisions.yaml#rule_03"},
  "reason": "用户连续询问尺码，介绍期应主动化解尺码顾虑",
  "script": "不确定尺码的姐妹告诉我身高体重，我帮你选！",
  "expected_goal": "降低尺码顾虑，推动下单",
  "quality": {"score": 87, "flags": []}
}
```

stage 枚举（沿用原项目状态机）：`start / attract / product_intro / try_on / trust / conversion / follow_up`

quality.score 0–100，quality.flags 标记问题（低置信/冗余/阶段错配），低于阈值（默认 60）的卡不进最终输出。

## 6. 各层实现要点

| 层 | 做什么 | 规则实现 | LLM 可选 |
|---|---|---|---|
| ingestion | 读四件套 + pydantic 校验 | 报错精确到问题行 | 无 |
| cleaning | 去语气词/重复词（保守清洗，保留 origin）、合并时间戳断裂短句 | 词表+正则 | 无 |
| segmentation | 500–1000 字符、句末标点切块，超长硬切、短尾合并 | 纯算法（借鉴原项目 step2_chunk） | 无 |
| event | 从 segment + chat 提取事件 | 关键词/正则模式库，固定置信度 | LLM 输出结构化事件，与规则结果按 (时间, 类型) 去重后取置信度高者 |
| decision | 事件+轻量会话状态 → 动作+话术 | YAML 规则表（事件规则优先 + 阶段兜底，借鉴原项目 planner） | LLM 改写话术填充占位符 |
| validation | 打分 + flags + 阈值过滤 | 触发充分性/阶段匹配/同动作去重（30 分钟窗口） | LLM 评委（可选） |

### 关键设计决策

1. **规则表外部化**：`rules/` 下 YAML——`patterns.yaml`（事件模式）、`decisions.yaml`（规则表）、`actions.yaml`（动作库，移植原项目 action_library 的 14 个动作、4 类：interaction/size/selling/conversion）。规则引擎统一：条件→动作→优先级，命中规则记录 `rule_ref` 保证可审计。
2. **会话状态内嵌**：decision 层内部维护轻量状态（当前 stage、当前商品、最近事件窗口），不单独成层；保留未来实时化的接口形状。
3. **LLM 接口**：`llm.py` 统一 OpenAI 兼容客户端（DeepSeek base_url）。环境变量 `LDE_LLM_API_KEY` / `LDE_LLM_BASE_URL` / `LDE_LLM_MODEL`。无 key 纯规则跑；CLI `--llm` 显式启用。
4. **CLI**：typer，Python 3.11+，依赖仅 pydantic / typer / pyyaml / openai（可选）。
   - `live-decision run <session_dir> [--from 01|02|03|04] [--llm]`
   - `live-decision validate <session_dir>`（只校验输入）

## 7. 错误处理

- 输入校验失败：报错精确到文件与行号，列出问题明细
- 单行转录损坏：跳过 + 警告，不中断整体
- 层执行失败：保留已完成 stages 产物，退出非零码
- 每层支持幂等重跑（覆盖同名产物）

## 8. 测试策略

- 单元测试：每层独立（清洗规则、切块边界、事件正则、决策规则、打分逻辑）
- 集成测试：demo/session_001 全流程跑通，断言 04_cards.jsonl 非空且全部通过 schema 校验
- fixtures：小段合成数据（不入 demo 目录）

## 9. demo 数据构建

`scripts/build_demo_data.py`（一次性脚本，依赖原项目数据路径）：
- 从原项目 `data/transcripts/*.vtt` 生成 transcript.jsonl（VTT → JSONL）
- 商品名/价格脱敏（模糊价格、替换品牌名），产品信息取自原项目 enriched.json
- 弹幕无真实数据：按时间线合成 30–50 条合理弹幕（含尺码提问、互动回应、价格询问）
- metadata.json 手写

## 10. 借鉴自 stream-script-kb 的部分

- segmentation：step2_chunk 的切块算法（500–1000 字符、句末标点、超长硬切、短尾合并）
- event：agent/event_extractor 的事件类型划分
- decision：agent/planner 的事件规则 + 阶段兜底结构；agent/action_library 的 14 个动作模板
- stage 状态机：PROJECT_VISION.md 的 7 阶段

## 11. 后续阶段（不在本 Demo 范围）

- 反馈闭环（feedback/：决策回放、评估、数据集构建）
- RAG 知识层（services/rag）
- 实时流式接入（接口预留）
- UI 可视化
