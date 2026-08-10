# Architecture

Extracted from the design spec `docs/superpowers/specs/2026-08-10-live-decision-engine-design.md`.

## 总体架构

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

## 数据契约（Schema）

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

## 各层实现要点

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

## 错误处理

- 输入校验失败：报错精确到文件与行号，列出问题明细
- 单行转录损坏：跳过 + 警告，不中断整体
- 层执行失败：保留已完成 stages 产物，退出非零码
- 每层支持幂等重跑（覆盖同名产物）

## 测试策略

- 单元测试：每层独立（清洗规则、切块边界、事件正则、决策规则、打分逻辑）
- 集成测试：demo/session_001 全流程跑通，断言 04_cards.jsonl 非空且全部通过 schema 校验
- fixtures：小段合成数据（不入 demo 目录）
