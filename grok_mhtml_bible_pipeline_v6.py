#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grok_mhtml_bible_pipeline_v6.py

MHTML-only Grok 长篇小说 / 对话整理流水线（v6：新增正文抽取）：

  1) 从 Chrome 保存的 .mhtml / .mht 中抽取 Grok 对话消息
     - 识别 data-testid="user-message"
     - 识别 data-testid="assistant-message"
     - 生成 clean_corpus.md / clean_corpus.jsonl / raw_messages.jsonl
     - 同时输出 assistant_only.txt / user_only.txt / full_conversation.txt

  2) 正文抽取
     - story_canon.md           纯小说正文，尽量去除 AI 交互感
     - removed_meta.md          被剔除的解释、总结、建议、废案等
     - canon_index.jsonl        正文抽取分块索引

  3) 分块总结 + 合并
     - parts_raw/
     - part_summaries/
     - worldbook.md

  4) 压缩出新对话上下文
     - final_bible.md

相对 v4 的主要变化：
  - 移除 TXT 入口。
  - 不再按 Thought for 启发式切段。
  - 输入只接受 .mhtml / .mht。
  - 每条原始消息明确标记为【USER】或【GROK】。
  - 后续所有证据引用均基于稳定编号 [S0001]、[S0002]……

依赖：
  - requests
  - beautifulsoup4

默认连接：
  - LM Studio OpenAI-compatible API
  - http://127.0.0.1:1234/v1

推荐保存方式：
  Chrome 打开 Grok share 页面 → 等完整加载 → Ctrl+S → 网页，单个文件 / Webpage, Single File (.mhtml)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, asdict
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests"])
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "beautifulsoup4"])
    from bs4 import BeautifulSoup


# ============================ 默认配置 ============================

DEFAULT_INPUT = r"D:\story\Police Goddess Park Crawl Ritual _ Shared Grok Conversation.mhtml"
DEFAULT_OUTPUT = r"D:\story\output_bible_mhtml_v6"
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"

DEFAULT_PART_CHARS = 30000
DEFAULT_MERGE_INPUT_CHARS = 70000
DEFAULT_TIMEOUT_SECONDS = 7200
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 4

PART_MAX_TOKENS = 18000
WORLDBOOK_MAX_TOKENS = 22000
COMPACT_MAX_TOKENS = 10000
CANON_MAX_TOKENS = 16000

DEFAULT_CANON_PART_CHARS = 24000
DEFAULT_RECENT_STORY_CHARS = 8000

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

_BAD_CHARS_TABLE = {
    **{c: None for c in range(32) if c not in (0x09, 0x0A)},
    **{c: None for c in range(0xE000, 0xF8FF + 1)},
}

log = logging.getLogger("bible")


# ============================ 数据结构 ============================

@dataclass
class Unit:
    uid: str
    role: str
    text: str
    char_start: int
    char_end: int
    message_index: int


# ============================ 通用工具 ============================

def setup_logging(log_file: Optional[Path] = None) -> None:
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def decode_bytes_smart(data: bytes, charset: Optional[str] = None) -> str:
    encodings: List[str] = []
    if charset:
        encodings.append(charset)

    encodings += [
        "utf-8-sig",
        "utf-8",
        "gb18030",
        "utf-16",
        "utf-16le",
        "utf-16be",
        "latin1",
    ]

    for enc in encodings:
        try:
            return data.decode(enc, errors="ignore")
        except Exception:
            continue

    return data.decode("utf-8", errors="ignore")


def sanitize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.translate(_BAD_CHARS_TABLE)

    for ch in ("\u00a0", "\u200b", "\u200c", "\u200d", "\ufeff"):
        text = text.replace(ch, " ")

    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def clean_message_text(text: str) -> str:
    """
    清理单条 Grok 消息。
    只删除页面 UI 噪声与 Thought 提示，不改写正文。
    """
    if not text:
        return ""

    text = sanitize_text(text)

    # 删除 Grok 页面上的思考提示
    text = re.sub(r"(?im)^\s*Thought\s+for\s+\d+\s*s\s*$", "", text)
    text = re.sub(r"(?im)^\s*Thinking\s*(?:for\s+\d+\s*s)?\s*$", "", text)
    text = re.sub(r"(?im)^\s*思考了\s*\d+\s*s\s*$", "", text)

    noise_lines = {
        "Copy",
        "Copied",
        "Share",
        "Retry",
        "Regenerate",
        "Like",
        "Dislike",
        "Open in app",
        "Sign in",
        "Log in",
        "Grok",
    }

    lines: List[str] = []
    for line in text.split("\n"):
        line = line.strip()

        if not line:
            lines.append("")
            continue

        if line in noise_lines:
            continue

        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_model_output(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"^```(?:markdown|md|json)?\s*\n?", "", raw)
    raw = re.sub(r"\n?\s*```\s*$", "", raw)
    return raw.strip()


def extract_possible_final_from_reasoning(reasoning: str) -> str:
    if not reasoning:
        return ""

    patterns = [
        r"(?:Final Answer|最终答案|输出)[:：]\s*(.*)$",
        r"(?:Here is the output|下面是整理结果)[:：]?\s*(.*)$",
    ]

    for pat in patterns:
        m = re.search(pat, reasoning, flags=re.DOTALL | re.IGNORECASE)
        if m and len(m.group(1).strip()) > 200:
            return clean_model_output(m.group(1))

    if "##" in reasoning and len(reasoning) > 1000:
        idx = reasoning.find("#")
        return clean_model_output(reasoning[idx:])

    return ""


# ============================ MHTML 抽取 ============================

def assert_mhtml_input(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"输入文件不存在：{path}")

    if path.suffix.lower() not in {".mhtml", ".mht"}:
        raise ValueError(
            f"当前 v5 只接受 .mhtml / .mht 输入，不再支持 TXT/HTML：{path}\n"
            "请用 Chrome 保存：Ctrl+S → 网页，单个文件 / Webpage, Single File。"
        )


def extract_html_from_mhtml(path: Path) -> str:
    """
    从 Chrome 保存的 .mhtml / .mht 中抽取主 HTML。
    通常最长的 text/html part 就是完整页面主体。
    """
    raw = path.read_bytes()
    msg = BytesParser(policy=policy.default).parsebytes(raw)

    html_parts: List[str] = []

    for part in msg.walk():
        if part.is_multipart():
            continue

        if part.get_content_type() != "text/html":
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        charset = part.get_content_charset()
        html_text = decode_bytes_smart(payload, charset)
        html_text = html_text.strip()

        if html_text:
            html_parts.append(html_text)

    if not html_parts:
        raise RuntimeError(
            f"{path} 中没有找到 text/html 部分。\n"
            "请确认它是 Chrome 保存的 .mhtml，而不是普通 HTML 改后缀。"
        )

    return max(html_parts, key=len)


def extract_grok_messages_from_mhtml(path: Path) -> List[Dict[str, str]]:
    html_text = extract_html_from_mhtml(path)
    soup = BeautifulSoup(html_text, "html.parser")

    selectors = [
        '[data-testid="user-message"]',
        '[data-testid="assistant-message"]',

        # 兼容 Grok / 其他导出版本
        '[data-message-author-role="user"]',
        '[data-message-author-role="assistant"]',
        '[data-author-role="user"]',
        '[data-author-role="assistant"]',
        '[data-role="user"]',
        '[data-role="assistant"]',
    ]

    messages: List[Dict[str, str]] = []

    for el in soup.select(", ".join(selectors)):
        data_testid = el.get("data-testid") or ""
        role_attr = (
            el.get("data-message-author-role")
            or el.get("data-author-role")
            or el.get("data-role")
            or ""
        )

        marker = f"{data_testid} {role_attr}".lower()

        role: Optional[str] = None
        if "user-message" in marker or role_attr.lower() == "user":
            role = "user"
        elif "assistant-message" in marker or role_attr.lower() == "assistant":
            role = "assistant"

        if not role:
            continue

        content = clean_message_text(el.get_text("\n", strip=True))
        if not content:
            continue

        messages.append({
            "role": role,
            "content": content,
        })

    messages = dedupe_role_messages(messages)

    if not messages:
        raise RuntimeError(
            "没有从 .mhtml 中提取到 Grok 消息。\n"
            "请确认：\n"
            "1. Chrome 保存方式是“网页，单个文件 / Webpage, Single File”。\n"
            "2. 保存前 Grok 页面已经完整加载。\n"
            "3. 文件里能搜到 data-testid=\"user-message\" 或 data-testid=\"assistant-message\"。"
        )

    return messages


def dedupe_role_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    seen = set()

    for msg in messages:
        role = msg.get("role", "").strip().lower()
        content = clean_message_text(msg.get("content", ""))

        if role not in {"user", "assistant"}:
            continue

        if not content:
            continue

        key = (role, content)
        if key in seen:
            continue

        seen.add(key)
        result.append({
            "role": role,
            "content": content,
        })

    return result


def messages_to_units(messages: List[Dict[str, str]]) -> List[Unit]:
    units: List[Unit] = []
    cursor = 0

    for i, msg in enumerate(messages, 1):
        role = msg["role"]
        label = "USER" if role == "user" else "GROK"
        content = clean_message_text(msg["content"])

        block = f"【{label}】\n{content}"
        start = cursor
        end = cursor + len(block)

        units.append(Unit(
            uid=f"S{i:04d}",
            role=role,
            text=block,
            char_start=start,
            char_end=end,
            message_index=i,
        ))

        cursor = end + 2

    return units


# ============================ 输出清洗结果 ============================

def render_clean_corpus_md(units: List[Unit]) -> str:
    parts = [
        "# 清洗编号原文",
        "",
        "说明：本文来自 Grok `.mhtml` 导出。每条原始消息已按页面结构抽取，并分配稳定编号 `Sxxxx`。",
        "",
        "角色标记：",
        "- `【USER】`：用户写作要求、修正、提示、偏好。",
        "- `【GROK】`：Grok 生成正文或回复。",
        "",
        "后续总结引用来源时，请使用编号，例如 `[S0001]`。",
        "整理原则：用户的明确要求、修正、否定优先级高于 Grok 早期正文；若存在冲突，以用户较新的表述为准。",
        "",
    ]

    for u in units:
        role_name = "USER" if u.role == "user" else "GROK"
        parts.extend([
            f"## [{u.uid}] {role_name} 消息 #{u.message_index}",
            "",
            u.text,
            "",
        ])

    return "\n".join(parts)


def render_full_conversation_txt(messages: List[Dict[str, str]]) -> str:
    blocks: List[str] = []

    for i, msg in enumerate(messages, 1):
        role = "USER" if msg["role"] == "user" else "GROK"
        blocks.append(
            f"===== {i:04d} [{role}] =====\n\n{msg['content']}"
        )

    return "\n\n\n".join(blocks)


def save_clean_outputs(units: List[Unit], messages: List[Dict[str, str]], out_dir: Path) -> None:
    write_text_atomic(out_dir / "clean_corpus.md", render_clean_corpus_md(units))
    write_text_atomic(out_dir / "full_conversation.txt", render_full_conversation_txt(messages))

    assistant_only = "\n\n===\n\n".join(
        msg["content"] for msg in messages if msg["role"] == "assistant"
    )
    user_only = "\n\n===\n\n".join(
        msg["content"] for msg in messages if msg["role"] == "user"
    )

    write_text_atomic(out_dir / "assistant_only.txt", assistant_only)
    write_text_atomic(out_dir / "user_only.txt", user_only)

    clean_jsonl = out_dir / "clean_corpus.jsonl"
    with clean_jsonl.open("w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(asdict(u), ensure_ascii=False) + "\n")

    raw_jsonl = out_dir / "raw_messages.jsonl"
    with raw_jsonl.open("w", encoding="utf-8") as f:
        for i, msg in enumerate(messages, 1):
            f.write(json.dumps({
                "index": i,
                "role": msg["role"],
                "content": msg["content"],
            }, ensure_ascii=False) + "\n")


def render_units_for_prompt(units: List[Unit]) -> str:
    blocks: List[str] = []
    for u in units:
        role_name = "USER" if u.role == "user" else "GROK"
        blocks.append(f"[{u.uid} | {role_name} 消息 #{u.message_index}]\n{u.text}")
    return "\n\n".join(blocks)


def pack_units_into_parts(units: List[Unit], part_chars: int) -> List[List[Unit]]:
    parts: List[List[Unit]] = []
    cur: List[Unit] = []
    cur_len = 0

    for u in units:
        add_len = len(u.text) + 64
        if cur and cur_len + add_len > part_chars:
            parts.append(cur)
            cur = [u]
            cur_len = add_len
        else:
            cur.append(u)
            cur_len += add_len

    if cur:
        parts.append(cur)

    return parts



# ============================ 正文抽取 / Canon ============================

def canon_extraction_prompt(idx: int, total: int, part_text: str) -> str:
    return f"""你将阅读一份从 Grok `.mhtml` 导出的长篇故事创作记录的第 {idx}/{total} 部分。

原文结构：
- 【USER】= 用户写作要求、剧情方向、关键台词、修正、否定、偏好。
- 【GROK】= Grok 回复，可能包含小说正文、解释、总结、建议、设定归纳、废案或多方案。
- 每条消息都有稳定编号 [S0001]、[S0002]……

你的任务：从本部分中抽取“可进入小说正文的纯正文”，形成 story_canon 片段。

极重要规则：
1. 不要改写、润色、扩写小说正文；只做提取、删交互废话、删标题说明、整理段落。
2. USER 消息通常不进入小说正文；但 USER 里如果写了明确要保留的原文句子/台词/段落，可作为候选，放入正文时要保持原句。
3. GROK 回复不一定全是正文。必须剔除：
   - “好的/我明白/下面是/我会……”等 AI 对话话术；
   - 总结、归纳、解释、写作建议、后续选项；
   - 设定卡、世界观列表、角色分析；
   - 被 USER 后文否定、重写、废弃的内容；
   - 多方案中未被后文承认的候选路线。
4. 如果某段像正文但不确定是否已被后文承认，可以放入正文，但在段落前加 HTML 注释：`<!-- uncertain canon: Sxxxx -->`。
5. 成人/亲密/身体内容：如果它本身是故事正文，可原样作为正文保留；不要新增细节，不要进行道德评价。
6. 输出必须严格使用下面三个二级标题。不要输出其他解释。

输出格式：

# Canon Extraction Part {idx}

## STORY_CANON
这里放纯小说正文。尽量不要带来源编号破坏阅读流，但可以用 HTML 注释标记不确定来源。
如果本部分没有可进入小说正文的内容，写：EMPTY

## REMOVED_META
这里记录被剔除的非正文内容，按来源编号简短说明，例如：
- [S0003] AI 解释/总结，不进入正文。
- [S0007] 用户写作要求，只作为设定证据，不进入正文。
如果没有，写：EMPTY

## CANON_NOTES
这里记录本部分正文抽取时的判断依据、疑似冲突、废案、待确认点。
如果没有，写：EMPTY

以下是第 {idx}/{total} 部分编号原文：
<<<PART_TEXT_START
{part_text}
PART_TEXT_END>>>"""


def parse_markdown_section(text: str, heading: str) -> str:
    pattern = rf"(?ims)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    m = re.search(pattern, text or "")
    if not m:
        return ""
    value = m.group(1).strip()
    if value.upper() == "EMPTY":
        return ""
    return value


def source_range_for_units(units: List[Unit]) -> str:
    if not units:
        return ""
    if len(units) == 1:
        return units[0].uid
    return f"{units[0].uid}-{units[-1].uid}"


def stage_story_canon(
    units: List[Unit],
    out_dir: Path,
    *,
    client: Optional[LMStudioClient],
    model: Optional[str],
    canon_part_chars: int,
    temperature: float,
    redo: bool,
    skip_canon: bool,
    no_think: bool,
) -> str:
    """
    从 USER/GROK 消息中抽取“无 AI 交互感”的小说正文。

    输出：
      - canon_raw_parts/canon_part_001_raw.md
      - story_canon_parts/canon_part_001_story.md
      - removed_meta_parts/canon_part_001_removed_meta.md
      - canon_notes_parts/canon_part_001_notes.md
      - story_canon.md
      - removed_meta.md
      - canon_notes.md
      - canon_index.jsonl
    """
    story_path = out_dir / "story_canon.md"
    removed_path = out_dir / "removed_meta.md"
    notes_path = out_dir / "canon_notes.md"
    index_path = out_dir / "canon_index.jsonl"

    if skip_canon:
        if story_path.exists():
            log.info("[story_canon] --skip-canon：使用已有 %s", story_path)
            return story_path.read_text(encoding="utf-8")
        log.info("[story_canon] --skip-canon：没有已有 story_canon.md，后续 final 只使用 worldbook")
        return ""

    parts = pack_units_into_parts(units, canon_part_chars)
    raw_dir = out_dir / "canon_raw_parts"
    story_dir = out_dir / "story_canon_parts"
    removed_dir = out_dir / "removed_meta_parts"
    notes_dir = out_dir / "canon_notes_parts"
    debug_dir = out_dir / "debug"

    for d in (raw_dir, story_dir, removed_dir, notes_dir):
        d.mkdir(parents=True, exist_ok=True)

    if client is None or model is None:
        raise RuntimeError("需要 LMStudioClient 才能生成 story_canon")

    index_rows: List[Dict[str, Any]] = []

    for i, part_units in enumerate(parts, 1):
        source_range = source_range_for_units(part_units)
        part_raw = render_units_for_prompt(part_units)

        raw_path = raw_dir / f"canon_part_{i:03d}_raw.md"
        extracted_path = story_dir / f"canon_part_{i:03d}_story.md"
        removed_part_path = removed_dir / f"canon_part_{i:03d}_removed_meta.md"
        notes_part_path = notes_dir / f"canon_part_{i:03d}_notes.md"

        write_text_atomic(raw_path, part_raw)

        if extracted_path.exists() and removed_part_path.exists() and notes_part_path.exists() and not redo:
            log.info("[story_canon %d/%d] 已存在，跳过", i, len(parts))
        else:
            log.info("[story_canon %d/%d] 抽取正文 %d 字符，来源 %s", i, len(parts), len(part_raw), source_range)
            result = client.complete(
                canon_extraction_prompt(i, len(parts), part_raw),
                model=model,
                max_tokens=CANON_MAX_TOKENS,
                temperature=temperature,
                debug_dir=debug_dir,
                tag=f"story_canon_{i:03d}",
                no_think=no_think,
            )

            story = parse_markdown_section(result, "STORY_CANON")
            removed = parse_markdown_section(result, "REMOVED_META")
            notes = parse_markdown_section(result, "CANON_NOTES")

            # 如果模型没有严格按标题输出，兜底把结果放入 notes，避免污染正文。
            if not story and not removed and not notes:
                notes = "模型未按指定标题输出，原始输出如下：\n\n" + result

            write_text_atomic(extracted_path, story.strip())
            write_text_atomic(removed_part_path, removed.strip())
            write_text_atomic(notes_part_path, notes.strip())

        index_rows.append({
            "part_index": i,
            "source_range": source_range,
            "source_uids": [u.uid for u in part_units],
            "raw_part": str(raw_path),
            "story_part": str(extracted_path),
            "removed_meta_part": str(removed_part_path),
            "notes_part": str(notes_part_path),
        })

    story_blocks: List[str] = []
    removed_blocks: List[str] = []
    notes_blocks: List[str] = []

    for row in index_rows:
        i = row["part_index"]
        source_range = row["source_range"]

        story = Path(row["story_part"]).read_text(encoding="utf-8").strip()
        removed = Path(row["removed_meta_part"]).read_text(encoding="utf-8").strip()
        notes = Path(row["notes_part"]).read_text(encoding="utf-8").strip()

        if story:
            story_blocks.append(f"<!-- canon_part_{i:03d}; source: {source_range} -->\n\n{story}")
        if removed:
            removed_blocks.append(f"## canon_part_{i:03d} / source: {source_range}\n\n{removed}")
        if notes:
            notes_blocks.append(f"## canon_part_{i:03d} / source: {source_range}\n\n{notes}")

    story_header = "# story_canon：纯小说正文\n\n说明：本文由 LLM 从 Grok 对话中抽取，目标是去除 AI 交互感；仍建议人工抽查。\n\n"
    removed_header = "# removed_meta：未进入正文的交互、总结、建议、废案\n\n"
    notes_header = "# canon_notes：正文抽取判断记录\n\n"

    write_text_atomic(story_path, story_header + "\n\n".join(story_blocks).strip() + "\n")
    write_text_atomic(removed_path, removed_header + "\n\n".join(removed_blocks).strip() + "\n")
    write_text_atomic(notes_path, notes_header + "\n\n".join(notes_blocks).strip() + "\n")

    with index_path.open("w", encoding="utf-8") as f:
        for row in index_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    log.info("[story_canon] 写入 %s", story_path)
    log.info("[story_canon] 写入 %s", removed_path)
    log.info("[story_canon] 写入 %s", index_path)

    return story_path.read_text(encoding="utf-8")


def tail_text(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[-max_chars:]

# ============================ LM Studio 调用 ============================

class LMStudioClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = (15, timeout_seconds)
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def list_models(self) -> List[str]:
        r = self.session.get(f"{self.base_url}/models", timeout=10)
        r.raise_for_status()
        return [m["id"] for m in (r.json().get("data") or [])]

    def auto_model(self) -> str:
        try:
            ids = self.list_models()
        except Exception as e:
            raise RuntimeError(f"无法访问 LM Studio {self.base_url}：{e}") from e

        if not ids:
            raise RuntimeError("LM Studio /v1/models 没有返回模型，请先在 LM Studio 中加载一个模型")

        return ids[0]

    def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        debug_dir: Path,
        tag: str,
        no_think: bool = True,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        prompt_to_send = ("/no_think\n" + prompt) if no_think else prompt

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_to_send}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        last_err: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                r = self.session.post(url, json=payload, timeout=self.timeout)

                if r.status_code in RETRYABLE_STATUS:
                    raise RuntimeError(f"HTTP {r.status_code}（可重试）：{r.text[:300]}")

                if r.status_code >= 400:
                    raise PermissionError(f"HTTP {r.status_code}：{r.text[:500]}")

                data = r.json()
                msg = (((data.get("choices") or [{}])[0]).get("message") or {})
                content = clean_model_output(msg.get("content") or "")

                if content:
                    return content

                reasoning = msg.get("reasoning_content") or ""
                fallback = extract_possible_final_from_reasoning(reasoning)
                if fallback:
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    write_text_atomic(
                        debug_dir / f"{tag}_reasoning_fallback_attempt{attempt}.txt",
                        reasoning,
                    )
                    return fallback

                debug_dir.mkdir(parents=True, exist_ok=True)
                write_text_atomic(
                    debug_dir / f"{tag}_empty_attempt{attempt}.json",
                    json.dumps(data, ensure_ascii=False, indent=2),
                )
                raise RuntimeError("模型返回空内容")

            except PermissionError:
                raise
            except (requests.ConnectionError, requests.Timeout) as e:
                last_err = e
                log.warning("[%s 重试 %d/%d] 网络错误：%s", tag, attempt, self.max_retries, e)
            except Exception as e:
                last_err = e
                log.warning("[%s 重试 %d/%d] %s", tag, attempt, self.max_retries, e)

            if attempt < self.max_retries:
                backoff = min(60, 2 ** attempt) + random.uniform(0, 2)
                time.sleep(backoff)

        raise last_err or RuntimeError("LM Studio 调用失败（未知原因）")


# ============================ Prompt 模板 ============================

def part_prompt(idx: int, total: int, part_text: str) -> str:
    return f"""你将阅读一份从 Grok `.mhtml` 导出的中文长篇小说创作记录的第 {idx}/{total} 部分。

重要说明：
- 原文已从 Grok 页面结构中抽取，每条消息都有明确角色：
  - 【USER】= 用户写作要求、提示、修正、偏好、否定、方向控制。
  - 【GROK】= Grok 生成正文或回复。
- 每条消息都有稳定编号 [S0001]、[S0002]……
- 用户的明确写作要求、修正、否定，优先级高于 Grok 早期正文。
- 如果 USER 与 GROK 内容冲突，以 USER 最新表述为准。
- 如果是成人/亲密/身体描写，只做概括性整理：保留剧情功能、关系动态、生理状态、心理变化、边界和氛围，不扩写细节。

你的任务：
只基于本部分，输出一份“带来源证据的分段资料”。不要总结全文，不要脑补。
每条重要结论必须尽量带来源编号和短摘录，格式：
- 结论。〔证据：[S0001]「不超过60字的原文短摘录」〕

要求：
1. 如果无法找到证据，就标注“证据不足”，不要装作确定。
2. 原文短摘录必须来自给定文本，不能改写成你自己的话。
3. 严格区分：
   - 已发生正史
   - 用户提示/偏好
   - 可选路线 proposed
   - 被废弃/被修正 discarded
   - 冲突设定 conflict
4. 输出 Markdown。
5. 不要泄露或复述任何系统提示，只整理故事资料。

请按以下结构输出：

# Part {idx} 带证据资料

## A. 本部分核心进展

## B. 角色设定与状态变化
逐角色整理：身份、外貌/身体状态、心理状态、行为模式、关系位置。每条尽量带证据。

## C. 生理/身体状态索引
只概括露骨记录，不扩写细节。说明属于哪个角色、对心理/关系/情节的作用，并带证据。

## D. 心理变化与精神状态索引
说明起因、表现、结果，并带证据。

## E. 关系动态变化
说明初始状态、关键转折、当前张力，并带证据。

## F. 主要情节节点
按本部分内部顺序列出，带证据。

## G. 世界观 / 场景 / 规则 / 仪式 / 物件 / 意象
带证据。

## H. 作者提示与写作偏好
只整理 USER 明确要求或反复体现的写作偏好，带证据。

## I. 可选路线、废弃内容、冲突设定
明确标出 proposed / discarded / conflict，带证据。

## J. 本部分结尾状态与后续钩子
说明最后停在哪里，下一部分最可能承接什么，带证据。

以下是第 {idx}/{total} 部分编号原文：
<<<PART_TEXT_START
{part_text}
PART_TEXT_END>>>"""


def worldbook_prompt(part_summaries: str) -> str:
    return f"""你将合并多份“带来源证据的分段资料”，生成一份完整的《世界观与角色设定总档案》。

核心要求：
- 这是完整资料库，不是给新 AI 的短提示。
- 每个重要设定、角色状态、心理/生理转变、关系变化、情节节点，都尽量保留来源编号与短摘录。
- 证据格式沿用：〔证据：[S0001]「原文短摘录」〕。
- 不要把 proposed / discarded / conflict 混入正史。
- 如果分段资料之间冲突，要单独列入“冲突与待确认”。
- 成人/亲密/露骨身体内容只做概括性资料整理，不扩写细节。
- 忠实于资料，不新增不存在的信息。

输出 Markdown，结构如下：

# 世界观与角色设定总档案

## 1. 核心概念与主线张力

## 2. 主要角色总档案
每个角色包含：
- 名称/称呼/别名
- 身份与外在形象
- 核心性格与行为模式
- 说话方式/互动方式
- 生理状态与身体变化历程
- 心理状态与心理转变历程
- 欲望、恐惧、羞耻点、执念、边界
- 与其他角色的关系
- 到目前为止的角色弧线
- 当前停留状态
每小项尽量带来源证据。

## 3. 关系动态总表

## 4. 已确定主要情节时间线

## 5. 生理变化与身体状态索引

## 6. 心理变化与精神状态索引

## 7. 世界观 / 场景 / 规则 / 仪式 / 物件 / 意象

## 8. 写作风格与作者偏好

## 9. 可选路线 proposed

## 10. 已废弃/被修正 discarded

## 11. 冲突与待确认

## 12. 当前停顿点与后续钩子

以下是所有分段资料：
<<<SUMMARIES_START
{part_summaries}
SUMMARIES_END>>>"""


def compact_prompt(worldbook: str, recent_story: str = "") -> str:
    recent_block = ""
    if recent_story.strip():
        recent_block = f"""

以下是从 story_canon.md 末尾截取的最近正文。它用于帮助新 AI 接住文气、场景、节奏和最后停顿点：
<<<RECENT_STORY_START
{recent_story}
RECENT_STORY_END>>>"""

    return f"""你将基于完整《世界观与角色设定总档案》和最近正文，生成一份适合复制给 Grok / 新 AI 开新对话继续写的精简版 final_bible。

要求：
- 目标不是越详细越好，而是让新 AI 快速接上。
- 控制在 5000-9000 中文字左右。
- 保留核心来源编号，但不要每句话都塞证据；关键设定、关键状态、当前钩子必须保留少量证据引用。
- 不要扩写新剧情，不要新增原资料没有的设定。
- proposed / discarded 必须分开写清楚，避免新 AI 误用。
- 成人/亲密/露骨/身体内容只做概括性上下文记录，不扩写细节。
- 必须强调：新 AI 续写时只输出小说正文，不要说“好的”、不要解释、不要总结、不要给选项。

输出 Markdown：

# final_bible：给 Grok 续写用的精简上下文

## 1. 可直接复制给新 AI 的压缩上下文
1200-2500 字，说明当前故事到哪里、角色是谁、关系张力、风格口味、当前钩子。

## 2. 主要角色速查

## 3. 关系动态速查

## 4. 已发生主要情节

## 5. 生理/心理变化重点

## 6. 场景、规则、仪式、意象

## 7. 写作风格与禁忌

## 8. 可选路线与不要带入内容

## 9. 当前停顿点与三种自然接法

## 10. 给新 AI 的开场提示
写一段可直接粘贴给 Grok 的提示。提示中必须包含：
- “只输出小说正文”
- “不要解释写作思路”
- “不要总结前情”
- “不要给我选项”
- “从最近正文之后自然续写”

以下是完整总档案：
<<<WORLDBOOK_START
{worldbook}
WORLDBOOK_END>>>{recent_block}"""


# ============================ 合并辅助 ============================

def split_text_for_merge(
    texts: List[Tuple[str, str]],
    max_chars: int,
) -> List[List[Tuple[str, str]]]:
    groups: List[List[Tuple[str, str]]] = []
    cur: List[Tuple[str, str]] = []
    cur_len = 0

    for name, text in texts:
        add_len = len(text) + len(name) + 64

        if cur and cur_len + add_len > max_chars:
            groups.append(cur)
            cur = [(name, text)]
            cur_len = add_len
        else:
            cur.append((name, text))
            cur_len += add_len

    if cur:
        groups.append(cur)

    return groups


def _format_group_payload(group: List[Tuple[str, str]]) -> str:
    return "\n\n".join(f"<!-- {name} -->\n{text}" for name, text in group)


def merge_part_summaries(
    summary_files: List[Path],
    *,
    client: LMStudioClient,
    model: str,
    out_dir: Path,
    merge_input_chars: int,
    temperature: float,
    no_think: bool,
) -> str:
    texts = [(p.name, p.read_text(encoding="utf-8")) for p in summary_files]
    groups = split_text_for_merge(texts, merge_input_chars)
    round_dir = out_dir / "merge_rounds"
    round_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = out_dir / "debug"

    if len(groups) == 1:
        payload = _format_group_payload(groups[0])
        log.info("[worldbook] 单轮合并 %d 字符", len(payload))
        return client.complete(
            worldbook_prompt(payload),
            model=model,
            max_tokens=WORLDBOOK_MAX_TOKENS,
            temperature=temperature,
            debug_dir=debug_dir,
            tag="worldbook",
            no_think=no_think,
        )

    shard_paths: List[Path] = []

    for i, group in enumerate(groups, 1):
        shard_path = round_dir / f"worldbook_shard_{i:03d}.md"

        if shard_path.exists():
            log.info("[merge shard %d/%d] 已存在，跳过", i, len(groups))
            shard_paths.append(shard_path)
            continue

        payload = _format_group_payload(group)
        log.info("[merge shard %d/%d] 合并 %d 字符资料", i, len(groups), len(payload))

        shard = client.complete(
            worldbook_prompt(payload),
            model=model,
            max_tokens=WORLDBOOK_MAX_TOKENS,
            temperature=temperature,
            debug_dir=debug_dir,
            tag=f"worldbook_shard_{i:03d}",
            no_think=no_think,
        )

        write_text_atomic(shard_path, shard)
        shard_paths.append(shard_path)

    shard_texts = [(p.name, p.read_text(encoding="utf-8")) for p in shard_paths]
    payload = _format_group_payload(shard_texts)
    log.info("[merge final worldbook] 合并 %d 个 shard", len(shard_paths))

    return client.complete(
        worldbook_prompt(payload),
        model=model,
        max_tokens=WORLDBOOK_MAX_TOKENS,
        temperature=temperature,
        debug_dir=debug_dir,
        tag="worldbook_final",
        no_think=no_think,
    )


# ============================ 阶段函数 ============================

def stage_clean(input_path: Path, out_dir: Path) -> List[Unit]:
    assert_mhtml_input(input_path)

    log.info("读取 MHTML：%s", input_path)
    messages = extract_grok_messages_from_mhtml(input_path)
    units = messages_to_units(messages)

    save_clean_outputs(units, messages, out_dir)

    user_count = sum(1 for m in messages if m["role"] == "user")
    assistant_count = sum(1 for m in messages if m["role"] == "assistant")

    log.info(
        "MHTML 清洗完成：%d 条消息（USER=%d, GROK=%d）；输出 %s",
        len(messages),
        user_count,
        assistant_count,
        out_dir / "clean_corpus.md",
    )

    return units


def stage_parts(
    units: List[Unit],
    out_dir: Path,
    *,
    client: Optional[LMStudioClient],
    model: Optional[str],
    part_chars: int,
    temperature: float,
    redo: bool,
    skip_parts: bool,
    no_think: bool,
) -> List[Path]:
    parts = pack_units_into_parts(units, part_chars)
    parts_dir = out_dir / "parts_raw"
    summaries_dir = out_dir / "part_summaries"

    parts_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)

    log.info("切成 %d 部分；目标每部分 %d 字符", len(parts), part_chars)

    debug_dir = out_dir / "debug"

    for i, part_units in enumerate(parts, 1):
        part_raw = render_units_for_prompt(part_units)
        raw_path = parts_dir / f"part_{i:03d}.md"
        summary_path = summaries_dir / f"part_{i:03d}_summary.md"

        write_text_atomic(raw_path, part_raw)

        if skip_parts:
            continue

        if summary_path.exists() and not redo:
            log.info("[part %d/%d] 已存在，跳过", i, len(parts))
            continue

        if client is None or model is None:
            raise RuntimeError("需要 LMStudioClient 才能生成 part summary")

        log.info("[part %d/%d] 总结 %d 字符", i, len(parts), len(part_raw))

        result = client.complete(
            part_prompt(i, len(parts), part_raw),
            model=model,
            max_tokens=PART_MAX_TOKENS,
            temperature=temperature,
            debug_dir=debug_dir,
            tag=f"part_{i:03d}",
            no_think=no_think,
        )

        write_text_atomic(summary_path, result)
        log.info("[part %d/%d] 写入 %s", i, len(parts), summary_path)

    return sorted(summaries_dir.glob("part_*_summary.md"))


def stage_worldbook(
    summary_files: List[Path],
    out_dir: Path,
    *,
    client: LMStudioClient,
    model: str,
    merge_input_chars: int,
    temperature: float,
    redo: bool,
    skip_worldbook: bool,
    no_think: bool,
) -> str:
    worldbook_path = out_dir / "worldbook.md"

    if skip_worldbook:
        if not worldbook_path.exists():
            raise RuntimeError("--skip-worldbook 但 worldbook.md 不存在")
        return worldbook_path.read_text(encoding="utf-8")

    if worldbook_path.exists() and not redo:
        log.info("worldbook.md 已存在，跳过合并")
        return worldbook_path.read_text(encoding="utf-8")

    log.info("[worldbook] 合并 %d 个 part summary", len(summary_files))

    worldbook = merge_part_summaries(
        summary_files,
        client=client,
        model=model,
        out_dir=out_dir,
        merge_input_chars=merge_input_chars,
        temperature=temperature,
        no_think=no_think,
    )

    write_text_atomic(worldbook_path, worldbook)
    log.info("[worldbook] 写入 %s", worldbook_path)

    return worldbook


def stage_final(
    worldbook: str,
    story_canon: str,
    out_dir: Path,
    *,
    client: LMStudioClient,
    model: str,
    temperature: float,
    redo: bool,
    no_think: bool,
    recent_story_chars: int,
) -> Path:
    final_path = out_dir / "final_bible.md"
    recent_story_path = out_dir / "recent_story_for_prompt.md"

    recent_story = tail_text(story_canon, recent_story_chars)
    if recent_story:
        write_text_atomic(recent_story_path, recent_story)

    if final_path.exists() and not redo:
        log.info("final_bible.md 已存在，跳过")
        return final_path

    log.info("[final_bible] 生成给 Grok / 新 AI 的精简版")

    final = client.complete(
        compact_prompt(worldbook, recent_story),
        model=model,
        max_tokens=COMPACT_MAX_TOKENS,
        temperature=temperature,
        debug_dir=out_dir / "debug",
        tag="final_bible",
        no_think=no_think,
    )

    write_text_atomic(final_path, final)
    log.info("[final_bible] 写入 %s", final_path)

    return final_path


def show_status(out_dir: Path) -> None:
    parts_dir = out_dir / "parts_raw"
    summaries_dir = out_dir / "part_summaries"

    parts_count = len(list(parts_dir.glob("part_*.md"))) if parts_dir.exists() else 0
    summary_count = len(list(summaries_dir.glob("part_*_summary.md"))) if summaries_dir.exists() else 0

    print(f"输出目录：{out_dir}")
    print(f"  clean_corpus.md      : {'✓' if (out_dir / 'clean_corpus.md').exists() else '✗'}")
    print(f"  raw_messages.jsonl   : {'✓' if (out_dir / 'raw_messages.jsonl').exists() else '✗'}")
    print(f"  full_conversation.txt: {'✓' if (out_dir / 'full_conversation.txt').exists() else '✗'}")
    print(f"  assistant_only.txt   : {'✓' if (out_dir / 'assistant_only.txt').exists() else '✗'}")
    print(f"  user_only.txt        : {'✓' if (out_dir / 'user_only.txt').exists() else '✗'}")
    print(f"  story_canon.md      : {'✓' if (out_dir / 'story_canon.md').exists() else '✗'}")
    print(f"  removed_meta.md     : {'✓' if (out_dir / 'removed_meta.md').exists() else '✗'}")
    print(f"  canon_index.jsonl   : {'✓' if (out_dir / 'canon_index.jsonl').exists() else '✗'}")
    print(f"  parts_raw            : {parts_count} 份")
    print(f"  part_summaries       : {summary_count} 份")
    print(f"  worldbook.md         : {'✓' if (out_dir / 'worldbook.md').exists() else '✗'}")
    print(f"  final_bible.md       : {'✓' if (out_dir / 'final_bible.md').exists() else '✗'}")


# ============================ 主流程 ============================

def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Grok MHTML 长篇小说对话整理 pipeline (v6, MHTML-only + story_canon)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("--input", default=DEFAULT_INPUT, help="Grok .mhtml / .mht 路径")
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help="输出目录")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help="LM Studio OpenAI-compatible base url")
    ap.add_argument("--model", default=None, help="模型 ID；不填则自动读取 /v1/models 第一个")
    ap.add_argument("--part-chars", type=int, default=DEFAULT_PART_CHARS)
    ap.add_argument("--canon-part-chars", type=int, default=DEFAULT_CANON_PART_CHARS, help="正文抽取阶段每块字符数")
    ap.add_argument("--recent-story-chars", type=int, default=DEFAULT_RECENT_STORY_CHARS, help="生成 final_bible 时附带的 story_canon 末尾字符数")
    ap.add_argument("--merge-input-chars", type=int, default=DEFAULT_MERGE_INPUT_CHARS)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="单次请求 read timeout 秒数")
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    ap.add_argument("--redo", action="store_true", help="重做已有 part/worldbook/final")
    ap.add_argument("--skip-parts", action="store_true", help="跳过 part 总结")
    ap.add_argument("--skip-worldbook", action="store_true", help="跳过 worldbook，直接用已有的生成 final")
    ap.add_argument("--skip-canon", action="store_true", help="跳过 story_canon 正文抽取；如果已有 story_canon.md 则复用")

    think = ap.add_mutually_exclusive_group()
    think.add_argument("--think", action="store_true", help="启用模型 thinking（不加 /no_think）")
    think.add_argument("--allow-think", dest="think", action="store_true", help=argparse.SUPPRESS)

    ap.add_argument("--log-file", default=None, help="可选：把日志同时写到文件")
    ap.add_argument("--dry-run", action="store_true", help="只清洗 + 切分，不调用 LLM；用于检查切分质量")
    ap.add_argument("--only-canon", action="store_true", help="只运行到 story_canon 正文抽取，生成后退出")
    ap.add_argument("--list-models", action="store_true", help="列出 LM Studio 当前可用模型并退出")
    ap.add_argument("--status", action="store_true", help="打印输出目录进度状态并退出")

    return ap


def main() -> None:
    args = build_argparser().parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(Path(args.log_file) if args.log_file else None)

    if args.status:
        show_status(out_dir)
        return

    if args.list_models:
        client = LMStudioClient(
            args.base_url,
            timeout_seconds=args.timeout,
            max_retries=args.max_retries,
        )
        try:
            ids = client.list_models()
        except Exception as e:
            print(f"无法访问 LM Studio：{e}", file=sys.stderr)
            sys.exit(2)

        if not ids:
            print("（LM Studio 没有加载任何模型）")
        else:
            for i, mid in enumerate(ids):
                print(f"{i}: {mid}")
        return

    no_think = not args.think

    input_path = Path(args.input)

    try:
        assert_mhtml_input(input_path)
    except Exception as e:
        log.error("%s", e)
        sys.exit(1)

    log.info("输入文件：%s", input_path)
    log.info("输出目录：%s", out_dir)

    # 阶段 1：MHTML 清洗 + 编号
    units = stage_clean(input_path, out_dir)

    if args.dry_run:
        log.info("[dry-run] 跳过 LLM 调用")

        parts = pack_units_into_parts(units, args.part_chars)
        parts_dir = out_dir / "parts_raw"
        parts_dir.mkdir(parents=True, exist_ok=True)

        for i, part_units in enumerate(parts, 1):
            write_text_atomic(
                parts_dir / f"part_{i:03d}.md",
                render_units_for_prompt(part_units),
            )

        canon_parts = pack_units_into_parts(units, args.canon_part_chars)
        canon_raw_dir = out_dir / "canon_raw_parts"
        canon_raw_dir.mkdir(parents=True, exist_ok=True)

        for i, part_units in enumerate(canon_parts, 1):
            write_text_atomic(
                canon_raw_dir / f"canon_part_{i:03d}_raw.md",
                render_units_for_prompt(part_units),
            )

        log.info("[dry-run] worldbook 原文切成 %d 部分，已写入 %s", len(parts), parts_dir)
        log.info("[dry-run] story_canon 原文切成 %d 部分，已写入 %s", len(canon_parts), canon_raw_dir)
        return

    # LM Studio 客户端
    client = LMStudioClient(
        args.base_url,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
    )

    model = args.model or client.auto_model()
    log.info("使用模型：%s", model)

    # 阶段 2：story_canon 正文抽取
    story_canon = stage_story_canon(
        units,
        out_dir,
        client=client,
        model=model,
        canon_part_chars=args.canon_part_chars,
        temperature=args.temperature,
        redo=args.redo,
        skip_canon=args.skip_canon,
        no_think=no_think,
    )

    if args.only_canon:
        log.info("[only-canon] 已生成 story_canon，停止在正文抽取阶段")
        log.info("  纯小说正文         : %s", out_dir / "story_canon.md")
        log.info("  剔除交互记录       : %s", out_dir / "removed_meta.md")
        log.info("  正文抽取索引       : %s", out_dir / "canon_index.jsonl")
        return

    # 阶段 3：part summaries
    summary_files = stage_parts(
        units,
        out_dir,
        client=client,
        model=model,
        part_chars=args.part_chars,
        temperature=args.temperature,
        redo=args.redo,
        skip_parts=args.skip_parts,
        no_think=no_think,
    )

    if not summary_files:
        raise RuntimeError("没有找到 part_summaries，无法合并")

    # 阶段 3：worldbook
    worldbook = stage_worldbook(
        summary_files,
        out_dir,
        client=client,
        model=model,
        merge_input_chars=args.merge_input_chars,
        temperature=args.temperature,
        redo=args.redo,
        skip_worldbook=args.skip_worldbook,
        no_think=no_think,
    )

    # 阶段 4：final_bible
    final_path = stage_final(
        worldbook,
        story_canon,
        out_dir,
        client=client,
        model=model,
        temperature=args.temperature,
        redo=args.redo,
        no_think=no_think,
        recent_story_chars=args.recent_story_chars,
    )

    log.info("完成。主要输出：")
    log.info("  1. 清洗编号原文       : %s", out_dir / "clean_corpus.md")
    log.info("  2. 原始结构化消息     : %s", out_dir / "raw_messages.jsonl")
    log.info("  3. 完整对话 TXT       : %s", out_dir / "full_conversation.txt")
    log.info("  4. 纯小说正文         : %s", out_dir / "story_canon.md")
    log.info("  5. 剔除交互记录       : %s", out_dir / "removed_meta.md")
    log.info("  6. 完整世界观档案     : %s", out_dir / "worldbook.md")
    log.info("  7. Grok 精简续写版    : %s", final_path)


if __name__ == "__main__":
    main()
