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
