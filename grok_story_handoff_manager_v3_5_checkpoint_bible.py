#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grok_story_handoff_manager_v3_5_checkpoint_bible.py

非硬合并版：每个 Grok 窗口独立归档，再把“新窗口内容”增量吸收到 master 正史里，
最后只生成 2~3 个给下个 Grok 新窗口用的文件。

你的默认配置：
  当前要吸收的故事 MHTML：
    D:\story\Police Goddess Park Crawl Ritual _ Shared Grok Conversation.mhtml

  单窗口整理脚本 v6：
    D:\story\grok_mhtml_bible_pipeline_v6.py

  项目总目录：
    D:\story\Police_Goddess_Project_v3

核心逻辑：
  1. 每个 .mhtml 都复制进 mhtml_archive，不覆盖旧窗口。
  2. 每个窗口都用 v6 跑进独立 runs/xxx 目录。
  3. v3 不再硬拼接所有 story_canon。
     它会读取：
       - 旧 master 正文
       - 旧 master 设定
       - 新窗口 story_canon
       - 新窗口 user_only / canon_notes
     让本地 LM Studio 判断：
       - 新窗口是否只是续写
       - 是否需要替换旧正文尾巴
       - 是否有废案/覆盖设定
       - 新的当前设定状态是什么
  4. 输出新的 handoff：
       - 01_当前设定状态_喂给Grok.md
       - 02_最近正文_喂给Grok.md
       - 03_下个窗口直接复制这个.md

依赖：
  - requests
  - beautifulsoup4 由 v6 自己处理
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests"])
    import requests


# =========================
# 默认配置
# =========================

DEFAULT_MHTML = r"D:\story\Police Goddess Park Crawl Ritual _ Shared Grok Conversation.mhtml"
DEFAULT_V6_SCRIPT = r"D:\story\grok_mhtml_bible_pipeline_v6.py"
DEFAULT_PROJECT_DIR = r"D:\story\Police_Goddess_Project_v3"

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_PART_CHARS = 30000
DEFAULT_CANON_PART_CHARS = 24000
DEFAULT_RECENT_CHARS = 9000

# 给“吸收判断模型”的旧正文尾巴长度
DEFAULT_OLD_RECENT_CHARS = 8000

# 给吸收判断模型看的新窗口头尾长度；新正文全文不让模型重写，只让它判断怎么吸收
DEFAULT_NEW_HEAD_CHARS = 8000
DEFAULT_NEW_TAIL_CHARS = 10000

DEFAULT_TIMEOUT_SECONDS = 7200
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 4

MHTML_SUFFIXES = {".mhtml", ".mht", ".mhtm"}
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


# =========================
# 基础工具
# =========================

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def stamp_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_name(name: str, max_len: int = 90) -> str:
    name = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(" .")
    return (name or "untitled")[:max_len]


def pause() -> None:
    input("\n按 Enter 继续……")


def ask(prompt: str, default: str = "") -> str:
    if default:
        s = input(f"{prompt} [{default}]: ").strip()
        return s or default
    return input(f"{prompt}: ").strip()


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    s = input(f"{prompt} [{suffix}]: ").strip().lower()
    if not s:
        return default
    return s in {"y", "yes", "是", "1", "run", "r"}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, obj: Any) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def tail_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    tail = text[-max_chars:]
    idx = tail.find("\n\n")
    if 0 <= idx <= 1200:
        tail = tail[idx:].strip()
    return tail.strip()


def head_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    head = text[:max_chars]
    idx = head.rfind("\n\n")
    if idx >= max_chars - 1200:
        head = head[:idx].strip()
    return head.strip()


def middle_notice(full: str, head: str, tail: str) -> str:
    omitted = max(0, len(full) - len(head) - len(tail))
    if omitted <= 0:
        return ""
    return f"\n\n【中间省略约 {omitted} 字，脚本不会丢弃，只是不全部喂给吸收判断模型。】\n\n"


def strip_top_title(text: str) -> str:
    lines = text.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("# "):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines).strip()


def is_mhtml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MHTML_SUFFIXES


def count_raw_messages(path: Path) -> Tuple[int, int, int]:
    rows = read_jsonl(path)
    user = sum(1 for r in rows if r.get("role") == "user")
    grok = sum(1 for r in rows if r.get("role") in {"assistant", "grok"})
    return len(rows), user, grok


# =========================
# 项目目录
# =========================

def project_paths(project_dir: Path) -> Dict[str, Path]:
    paths = {
        "archive": project_dir / "mhtml_archive",
        "runs": project_dir / "runs",
        "master": project_dir / "master",
        "handoff": project_dir / "handoff",
        "debug": project_dir / "debug",
        "snapshots": project_dir / "master" / "snapshots",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def archive_mhtml(mhtml_path: Path, archive_dir: Path) -> Path:
    if not mhtml_path.exists():
        raise FileNotFoundError(f"找不到 MHTML：{mhtml_path}")
    if not is_mhtml(mhtml_path):
        raise ValueError(f"不是 .mhtml/.mht/.mhtm：{mhtml_path}")

    size = mhtml_path.stat().st_size
    src_mtime = mhtml_path.stat().st_mtime
    stamp = datetime.fromtimestamp(src_mtime).strftime("%Y%m%d_%H%M%S")
    dst = archive_dir / f"{stamp}_{safe_name(mhtml_path.stem)}{mhtml_path.suffix}"

    # 同名同大小直接复用
    if dst.exists() and dst.stat().st_size == size:
        return dst

    if dst.exists() and dst.stat().st_size != size:
        dst = archive_dir / f"{stamp_now()}_{safe_name(mhtml_path.stem)}{mhtml_path.suffix}"

    if not dst.exists():
        shutil.copy2(mhtml_path, dst)

    return dst


def run_dir_for_archived_mhtml(archived_mhtml: Path, runs_dir: Path) -> Path:
    return runs_dir / safe_name(archived_mhtml.stem, max_len=140)


def save_run_manifest(run_dir: Path, archived_mhtml: Path, original_mhtml: Path) -> None:
    write_json(run_dir / "session_manifest.json", {
        "updated_at": now_str(),
        "run_dir": str(run_dir),
        "archived_mhtml": str(archived_mhtml),
        "original_mhtml": str(original_mhtml),
        "archived_mhtml_size": archived_mhtml.stat().st_size if archived_mhtml.exists() else None,
        "archived_mhtml_mtime": archived_mhtml.stat().st_mtime if archived_mhtml.exists() else None,
    })


def load_run_manifest(run_dir: Path) -> Dict[str, Any]:
    return read_json(run_dir / "session_manifest.json")


def discover_run_dirs(project_dir: Path) -> List[Path]:
    paths = project_paths(project_dir)
    runs_dir = paths["runs"]
    dirs: List[Path] = []
    for d in runs_dir.iterdir():
        if not d.is_dir():
            continue
        if (d / "story_canon.md").exists() or (d / "raw_messages.jsonl").exists():
            dirs.append(d)

    def sort_key(d: Path):
        m = load_run_manifest(d)
        t = m.get("archived_mhtml_mtime")
        if t is None:
            t = d.stat().st_mtime
        return (float(t), d.name.lower())

    dirs.sort(key=sort_key)
    return dirs


def session_title(run_dir: Path, index: int = 0) -> str:
    m = load_run_manifest(run_dir)
    archived = m.get("archived_mhtml")
    if archived:
        return Path(archived).stem
    return run_dir.name


# =========================
# LM Studio 客户端
# =========================

class LMStudioClient:
    def __init__(self, base_url: str, *, timeout_seconds: int, max_retries: int) -> None:
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
        ids = self.list_models()
        if not ids:
            raise RuntimeError("LM Studio 没有加载模型，请先加载一个模型")
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
        prompt_to_send = ("/no_think\n" + prompt + "\n\n/no_think\n直接输出最终答案，不要推理过程，不要 <think>。") if no_think else prompt

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
                    raise RuntimeError(f"HTTP {r.status_code} 可重试：{r.text[:300]}")
                if r.status_code >= 400:
                    raise RuntimeError(f"HTTP {r.status_code}：{r.text[:800]}")

                data = r.json()
                choice0 = (data.get("choices") or [{}])[0] or {}
                msg = choice0.get("message") or {}
                finish_reason = str(choice0.get("finish_reason") or "").strip().lower()
                content = clean_model_output(msg.get("content") or "")

                # completion 因长度截断时，content 常是半截 JSON，会在后续解析阶段报错。
                # 在这里优先识别并重试/报错，便于定位和调参。
                if finish_reason == "length":
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    write_text(debug_dir / f"{tag}_truncated_attempt{attempt}.json", json.dumps(data, ensure_ascii=False, indent=2))
                    usage = data.get("usage") or {}
                    raise RuntimeError(
                        "模型输出被长度截断（finish_reason=length）。"
                        f"建议提高 --max-tokens 或缩短输入；usage={usage}"
                    )

                if content:
                    return content

                # 有些 thinking 模型会把所有输出都塞进 reasoning_content，content 为空。
                # 这里不直接当成功返回，以免把思考过程写进 bible；但保存完整响应便于排查。
                reasoning_content = clean_model_output(msg.get("reasoning_content") or "")
                if reasoning_content:
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    write_text(debug_dir / f"{tag}_reasoning_only_attempt{attempt}.md", reasoning_content)

                debug_dir.mkdir(parents=True, exist_ok=True)
                write_text(debug_dir / f"{tag}_empty_attempt{attempt}.json", json.dumps(data, ensure_ascii=False, indent=2))
                raise RuntimeError("模型返回空内容")

            except Exception as e:
                last_err = e
                print(f"[{tag} 重试 {attempt}/{self.max_retries}] {e}")
                if attempt < self.max_retries:
                    time.sleep(min(60, 2 ** attempt) + random.uniform(0, 2))

        raise last_err or RuntimeError("LM Studio 调用失败")


def clean_model_output(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"^```(?:json|markdown|md)?\s*\n?", "", raw.strip())
    raw = re.sub(r"\n?\s*```\s*$", "", raw.strip())
    return raw.strip()


def _iter_brace_json_candidates(text: str) -> List[str]:
    candidates: List[str] = []
    start = -1
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(text[start:i + 1])

    return candidates


def extract_json_object(text: str) -> Dict[str, Any]:
    text = clean_model_output(text)
    if not text:
        raise ValueError("模型返回为空")

    # 直接 parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # 优先解析代码块中的 JSON
    for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE):
        block = block.strip()
        if not block:
            continue
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    # 扫描所有平衡的大括号片段，取第一个可解析对象
    for candidate in _iter_brace_json_candidates(text):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    # 回退：常见中文模型会输出全角标点，尽量修复一次
    normalized = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("：", ":")
        .replace("，", ",")
    )
    for candidate in _iter_brace_json_candidates(normalized):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    preview = text[:300].replace("\n", " ")
    raise ValueError(f"模型没有返回可解析 JSON（前300字预览：{preview}）")


# =========================
# 调用 v6
# =========================

def run_v6(
    *,
    mhtml_path: Path,
    v6_script: Path,
    run_dir: Path,
    part_chars: int,
    canon_part_chars: int,
    full_v6: bool,
    redo: bool,
) -> None:
    if not v6_script.exists():
        raise FileNotFoundError(f"找不到 v6 脚本：{v6_script}")

    cmd = [
        sys.executable,
        str(v6_script),
        "--input", str(mhtml_path),
        "--output", str(run_dir),
        "--part-chars", str(part_chars),
        "--canon-part-chars", str(canon_part_chars),
    ]

    if not full_v6:
        cmd.append("--only-canon")
    if redo:
        cmd.append("--redo")

    print("\n即将运行 v6：")
    print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
    print()

    subprocess.check_call(cmd)


def process_one_mhtml(
    *,
    mhtml_path: Path,
    v6_script: Path,
    project_dir: Path,
    part_chars: int,
    canon_part_chars: int,
    full_v6: bool,
    redo: bool,
) -> Path:
    paths = project_paths(project_dir)
    archived = archive_mhtml(mhtml_path, paths["archive"])
    run_dir = run_dir_for_archived_mhtml(archived, paths["runs"])
    run_dir.mkdir(parents=True, exist_ok=True)

    already_story = (run_dir / "story_canon.md").exists()
    already_full = (run_dir / "final_bible.md").exists()

    if not redo:
        if full_v6 and already_full:
            print(f"[SKIP] 这个窗口已经完整跑过：{run_dir}")
            save_run_manifest(run_dir, archived, mhtml_path)
            return run_dir
        if not full_v6 and already_story:
            print(f"[SKIP] 这个窗口已经跑过正文抽取：{run_dir}")
            save_run_manifest(run_dir, archived, mhtml_path)
            return run_dir

    run_v6(
        mhtml_path=archived,
        v6_script=v6_script,
        run_dir=run_dir,
        part_chars=part_chars,
        canon_part_chars=canon_part_chars,
        full_v6=full_v6,
        redo=redo,
    )

    save_run_manifest(run_dir, archived, mhtml_path)
    return run_dir


# =========================
# master 文件
# =========================

def master_story_path(project_dir: Path) -> Path:
    return project_paths(project_dir)["master"] / "01_当前正史正文.md"


def master_bible_path(project_dir: Path) -> Path:
    return project_paths(project_dir)["master"] / "02_当前设定状态.md"


def discarded_log_path(project_dir: Path) -> Path:
    return project_paths(project_dir)["master"] / "03_废案和覆盖记录.md"


def absorb_log_path(project_dir: Path) -> Path:
    return project_paths(project_dir)["master"] / "04_吸收日志.md"


def state_path(project_dir: Path) -> Path:
    return project_paths(project_dir)["master"] / "master_state.json"


def snapshot_master(project_dir: Path) -> None:
    paths = project_paths(project_dir)
    snap_dir = paths["snapshots"] / stamp_now()
    snap_dir.mkdir(parents=True, exist_ok=True)

    for p in [
        master_story_path(project_dir),
        master_bible_path(project_dir),
        discarded_log_path(project_dir),
        absorb_log_path(project_dir),
        state_path(project_dir),
    ]:
        if p.exists():
            shutil.copy2(p, snap_dir / p.name)


def load_master_state(project_dir: Path) -> Dict[str, Any]:
    return read_json(state_path(project_dir))


def save_master_state(project_dir: Path, state: Dict[str, Any]) -> None:
    write_json(state_path(project_dir), state)


# =========================
# 重叠修剪与应用 patch
# =========================

def normalize_for_overlap(s: str) -> str:
    s = re.sub(r"\s+", "", s)
    return s


def find_exact_overlap_chars(old_text: str, new_text: str, *, max_check: int = 16000, min_overlap: int = 400) -> int:
    """
    找 old_text 尾部与 new_text 开头的精确重叠。
    返回 new_text 开头应裁掉的字符数。
    """
    old_tail = old_text[-max_check:]
    new_head = new_text[:max_check]

    max_len = min(len(old_tail), len(new_head))
    best = 0

    # 为了稳，不做太复杂的 fuzzy；先从长到短找原文精确 overlap
    for n in range(max_len, min_overlap - 1, -100):
        if old_tail[-n:] == new_head[:n]:
            best = n
            break

    if best:
        return best

    # 段落级弱匹配：如果 new_text 前几个段落已经在 old_text 尾部出现，则裁掉这些段落
    paras = [p.strip() for p in re.split(r"\n{2,}", new_head) if p.strip()]
    cut = 0
    for p in paras[:8]:
        if len(p) < 80:
            break
        if p in old_tail:
            # 包含这个段落及其后两个换行
            idx = new_text.find(p, cut)
            if idx >= 0:
                cut = idx + len(p)
                # 吃掉后面的空白
                m = re.match(r"\s*", new_text[cut:])
                if m:
                    cut += len(m.group(0))
        else:
            break

    return cut if cut >= min_overlap else 0


def clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
    except Exception:
        return default
    return max(lo, min(hi, n))


def apply_absorb_plan(
    *,
    old_story: str,
    new_story: str,
    plan: Dict[str, Any],
    auto_trim_chars: int,
) -> Tuple[str, str]:
    action = str(plan.get("action") or "append").strip().lower()
    trim_head_chars = clamp_int(
        plan.get("trim_head_chars", auto_trim_chars),
        0,
        min(len(new_story), 50000),
        auto_trim_chars,
    )

    # 如果模型给 0，但自动检测出 overlap，用自动检测兜底
    if trim_head_chars == 0 and auto_trim_chars > 0:
        trim_head_chars = auto_trim_chars

    delta = new_story[trim_head_chars:].strip()
    if not delta:
        return old_story.strip() + "\n", f"新窗口正文在裁剪 {trim_head_chars} 字后为空，未更新 master_story。"

    note = f"action={action}; trim_head_chars={trim_head_chars}; auto_trim_chars={auto_trim_chars}"

    if action in {"discard", "no_story_change"}:
        return old_story.strip() + "\n", note + "\n模型判断本窗口不进入正史正文。"

    if action == "replace_tail":
        quote = str(plan.get("replace_from_quote") or "").strip()
        if quote and len(quote) >= 20:
            idx = old_story.rfind(quote)
            if idx >= 0:
                new_master = old_story[:idx].rstrip() + "\n\n" + delta.strip() + "\n"
                return new_master, note + f"\n已从 quote 替换旧尾巴：{quote[:80]}"
            else:
                # 找不到 quote，不敢删除旧文，改为 append 并记录
                new_master = old_story.rstrip() + "\n\n\n<!-- WARNING: replace_tail quote not found, fallback append -->\n\n" + delta.strip() + "\n"
                return new_master, note + "\n模型要求 replace_tail，但 quote 未找到；已 fallback append。"

        new_master = old_story.rstrip() + "\n\n\n<!-- WARNING: replace_tail without valid quote, fallback append -->\n\n" + delta.strip() + "\n"
        return new_master, note + "\n模型要求 replace_tail，但未给有效 quote；已 fallback append。"

    # 默认 append
    new_master = old_story.rstrip() + "\n\n\n" + delta.strip() + "\n"
    return new_master, note + "\n已 append 新窗口增量正文。"


# =========================
# Prompt
# =========================

def init_bible_prompt(story_head: str, story_tail: str, user_prompts: str, canon_notes: str) -> str:
    return f"""你要为一部长篇小说生成“当前设定状态档案”。

注意：
- 这不是续写，不要写新剧情。
- 只整理当前有效设定、角色状态、关系状态、剧情进度、写作风格。
- 不要把废案/可选方案混入正史。
- 如果不确定，标注“不确定”。
- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。
- 输出 Markdown。
- “已发生正史事件”不要太少：请尽量按时间顺序列出 20～60 条关键事件。
- 每条事件要短，但要包含：谁、做了什么、造成了什么状态变化。
- 不要只写最近一段，也要根据正文开头和尾部归纳故事从开端到当前的主要正史链。

结构：

# 当前设定状态

## 1. 当前故事进度

## 2. 主要角色状态

## 3. 关系状态

## 4. 已发生正史事件

## 5. 当前场景/停顿点

## 6. 世界观、规则、仪式、物件、意象

## 7. 写作风格与作者偏好

## 8. 废案/不要带入/待确认

以下是当前正文开头，用来理解故事起点和早期正史事件：
<<<STORY_HEAD
{story_head}
STORY_HEAD>>>

以下是当前正文尾部，用来理解最新状态和停顿点：
<<<STORY_TAIL
{story_tail}
STORY_TAIL>>>

以下是用户提示词/作者意图：
<<<USER_PROMPTS
{user_prompts}
USER_PROMPTS>>>

以下是正文抽取判断记录：
<<<CANON_NOTES
{canon_notes}
CANON_NOTES>>>"""



def split_text_by_chars(text: str, max_chars: int) -> List[str]:
    """尽量按段落切分，避免把超长 story 一口塞给模型。"""
    text = text.strip()
    if not text:
        return []
    paras = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    buf: List[str] = []
    size = 0
    for para in paras:
        p = para.strip()
        if not p:
            continue
        # 单段极长时硬切
        if len(p) > max_chars:
            if buf:
                chunks.append("\n\n".join(buf).strip())
                buf, size = [], 0
            for i in range(0, len(p), max_chars):
                chunks.append(p[i:i + max_chars].strip())
            continue
        if size + len(p) + 2 > max_chars and buf:
            chunks.append("\n\n".join(buf).strip())
            buf, size = [p], len(p)
        else:
            buf.append(p)
            size += len(p) + 2
    if buf:
        chunks.append("\n\n".join(buf).strip())
    return [c for c in chunks if c.strip()]


def safe_cache_name(tag: str) -> str:
    return re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", tag).strip("_") or "untitled"


def rich_cache_dir(debug_dir: Path) -> Path:
    return debug_dir / "init_bible_cache_v3_5"


def rich_section_complete(
    client: LMStudioClient,
    prompt: str,
    *,
    model: str,
    temperature: float,
    debug_dir: Path,
    tag: str,
    no_think: bool,
    max_tokens: int = 2200,
) -> str:
    """
    v3.5：所有成功的栏目/分块结果都立刻落盘。
    - 失败后重新运行同一版本，会优先复用已有成功结果。
    - 缓存目录：project/debug/init_bible_cache_v3_5/
    - 每次也会保存 .prompt.txt，方便排查某一步到底喂了什么。
    """
    cache_dir = rich_cache_dir(debug_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = safe_cache_name(tag)
    cache_path = cache_dir / f"{name}.md"
    prompt_path = cache_dir / f"{name}.prompt.txt"

    cached = read_text(cache_path).strip()
    if cached:
        print(f"[cache] 复用已完成结果：{cache_path.name}")
        return cached

    write_text(prompt_path, prompt)
    result = client.complete(
        prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        debug_dir=debug_dir,
        tag=tag,
        no_think=no_think,
    ).strip()
    if not result:
        raise RuntimeError(f"模型返回空内容：{tag}")
    write_text(cache_path, result + "\n")
    return result


def build_events_timeline_rich(
    *,
    story: str,
    client: LMStudioClient,
    model: str,
    temperature: float,
    debug_dir: Path,
    no_think: bool,
) -> str:
    """v3.3：正史事件单独跑，多块提取，再合并。"""
    chunks = split_text_by_chars(story, 16000)
    event_notes: List[str] = []
    total = len(chunks)
    print(f"[init_bible/events] 正史事件分块提取：{total} 块")
    for i, chunk in enumerate(chunks, 1):
        prompt = f"""你正在为长篇小说建立“已发生正史事件”时间线。

任务：只阅读本段正文，提取本段中明确发生过、应进入正史的事件。
重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>；第一行必须直接从“1.”开始。
要求：
- 不续写，不脑补。
- 不要写风格分析。
- 不要写候选方案。
- 按发生顺序列出。
- 每条包含：谁、做了什么、造成了什么状态变化。
- 如果本段没有明确事件，写“本段无新增明确正史事件”。
- 成人/亲密/身体内容只做概括性记录，不扩写细节。
- 输出 8～25 条以内，Markdown 编号列表。

这是第 {i}/{total} 段正文：
<<<STORY_CHUNK
{chunk}
STORY_CHUNK>>>"""
        print(f"[init_bible/events {i}/{total}] 提取本段事件……")
        note = rich_section_complete(
            client,
            prompt,
            model=model,
            temperature=temperature,
            debug_dir=debug_dir,
            tag=f"init_events_chunk_{i:03d}",
            no_think=no_think,
            max_tokens=12000,
        )
        event_notes.append(f"## 分段事件 {i}/{total}\n\n{note}")
        write_text(rich_cache_dir(debug_dir) / "_events_chunks_so_far.md", "\n\n".join(event_notes).strip() + "\n")

    joined = "\n\n".join(event_notes)
    # 合并输入如果过长，只取头尾和分段标题附近，避免再次爆 ctx。多数情况下事件 notes 不会太长。
    if len(joined) > 42000:
        joined = head_text(joined, 21000) + "\n\n【中间事件草稿过长，已省略部分重复草稿，合并时以保留时间线骨架为主。】\n\n" + tail_text(joined, 21000)

    merge_prompt = f"""你要把多段“正史事件草稿”合并成一个统一时间线。

重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>；第一行必须直接从“1.”开始。
要求：
- 去重、合并同义项，按故事发生顺序排列。
- 不要丢掉关键状态变化。
- 重点保留：角色关系变化、地点变化、冲突升级、仪式/规则/物件变化、身体/心理状态变化、作者明确推进过的事件。
- 不要写废案、候选方案、AI 交互。
- 输出 30～100 条。故事较短可以少于 30 条，但不要偷懒。
- 每条尽量 1 句，必要时 2 句。
- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。
- 只输出 Markdown 编号列表。

分段事件草稿：
<<<EVENT_NOTES
{joined}
EVENT_NOTES>>>"""
    print("[init_bible/events] 合并正史事件时间线……")
    return rich_section_complete(
        client,
        merge_prompt,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        tag="init_events_merge",
        no_think=no_think,
        max_tokens=12000,
    )


def merge_section_notes_rich(
    *,
    notes: List[str],
    section_name: str,
    merge_requirements: str,
    client: LMStudioClient,
    model: str,
    temperature: float,
    debug_dir: Path,
    no_think: bool,
    tag_prefix: str,
    max_chars_per_merge: int = 26000,
    max_tokens: int = 14000,
) -> str:
    """v3.5：把分块抽取的栏目笔记分批合并，避免单次 prompt 贴满上下文。"""
    items = [x.strip() for x in notes if x and x.strip()]
    if not items:
        return "暂无明确记录。"

    round_no = 1
    while True:
        joined = "\n\n".join(items)
        if len(joined) <= max_chars_per_merge or len(items) == 1:
            prompt = f"""你要把多段“{section_name}草稿”合并成正式资料。\n\n重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>。\n{merge_requirements}\n\n草稿：\n<<<NOTES\n{joined}\nNOTES>>>"""
            print(f"[init_bible/{tag_prefix}] 合并{section_name}……")
            return rich_section_complete(
                client,
                prompt,
                model=model,
                temperature=temperature,
                debug_dir=debug_dir,
                tag=f"init_{tag_prefix}_merge_final",
                no_think=no_think,
                max_tokens=max_tokens,
            )

        groups: List[List[str]] = []
        buf: List[str] = []
        size = 0
        for it in items:
            add = len(it) + 2
            if buf and size + add > max_chars_per_merge:
                groups.append(buf)
                buf = [it]
                size = add
            else:
                buf.append(it)
                size += add
        if buf:
            groups.append(buf)

        partials: List[str] = []
        for gi, group in enumerate(groups, 1):
            joined_group = "\n\n".join(group)
            prompt = f"""你要把一部分“{section_name}草稿”合并成中间稿。\n\n重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>。\n要求：\n- 保留具体信息，不要压成空泛概述。\n- 去重，但不要删掉关键状态变化。\n- 不续写，不脑补。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown。\n\n草稿：\n<<<NOTES\n{joined_group}\nNOTES>>>"""
            print(f"[init_bible/{tag_prefix}] 分组合并 {gi}/{len(groups)}……")
            partial = rich_section_complete(
                client,
                prompt,
                model=model,
                temperature=temperature,
                debug_dir=debug_dir,
                tag=f"init_{tag_prefix}_merge_r{round_no}_{gi:02d}",
                no_think=no_think,
                max_tokens=max_tokens,
            )
            partials.append(partial)
            write_text(rich_cache_dir(debug_dir) / f"_{tag_prefix}_merge_round{round_no}_partials_so_far.md", "\n\n".join(partials).strip() + "\n")
        items = partials
        round_no += 1


def extract_chunk_notes_rich(
    *,
    story: str,
    section_name: str,
    chunk_prompt_body: str,
    client: LMStudioClient,
    model: str,
    temperature: float,
    debug_dir: Path,
    no_think: bool,
    tag_prefix: str,
    chunk_chars: int = 14000,
    max_tokens: int = 12000,
) -> List[str]:
    """v3.5：逐段抽取某一栏目事实，宁可慢，不要省。"""
    chunks = split_text_by_chars(story, chunk_chars)
    total = len(chunks)
    print(f"[init_bible/{tag_prefix}] {section_name}分块提取：{total} 块")
    out: List[str] = []
    for i, chunk in enumerate(chunks, 1):
        prompt = f"""你正在为长篇小说建立“{section_name}”资料。\n\n重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>；第一行必须直接进入内容。\n{chunk_prompt_body}\n\n这是第 {i}/{total} 段正文：\n<<<STORY_CHUNK\n{chunk}\nSTORY_CHUNK>>>"""
        print(f"[init_bible/{tag_prefix} {i}/{total}] 提取本段{section_name}……")
        note = rich_section_complete(
            client,
            prompt,
            model=model,
            temperature=temperature,
            debug_dir=debug_dir,
            tag=f"init_{tag_prefix}_chunk_{i:03d}",
            no_think=no_think,
            max_tokens=max_tokens,
        )
        out.append(f"## {section_name}分段笔记 {i}/{total}\n\n{note}")
        write_text(rich_cache_dir(debug_dir) / f"_{tag_prefix}_chunks_so_far.md", "\n\n".join(out).strip() + "\n")
    return out


def build_events_timeline_deep(
    *,
    story: str,
    client: LMStudioClient,
    model: str,
    temperature: float,
    debug_dir: Path,
    no_think: bool,
) -> str:
    body = """任务：只阅读本段正文，提取本段中明确发生过、应进入正史的事件。\n要求：\n- 不续写，不脑补。\n- 按发生顺序列出。\n- 每条包含：谁、做了什么、造成了什么状态变化。\n- 重点保留角色关系变化、地点变化、冲突升级、仪式/规则/物件变化、身体/心理状态变化。\n- 如果本段没有明确事件，写“本段无新增明确正史事件”。\n- 成人/亲密/身体内容只做概括性记录，不扩写细节。\n- 输出 10～35 条以内，Markdown 编号列表。"""
    notes = extract_chunk_notes_rich(
        story=story,
        section_name="已发生正史事件",
        chunk_prompt_body=body,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="events",
        chunk_chars=14000,
        max_tokens=12000,
    )
    req = """要求：\n- 去重、合并同义项，按故事发生顺序排列。\n- 不要丢掉关键状态变化，不要只保留大纲。\n- 输出 50～160 条，除非故事确实极短。\n- 每条尽量 1 句，必要时 2 句。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 只输出 Markdown 编号列表。"""
    return merge_section_notes_rich(
        notes=notes,
        section_name="已发生正史事件",
        merge_requirements=req,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="events",
        max_chars_per_merge=26000,
        max_tokens=14000,
    )


def build_rich_bible_sections(
    *,
    story: str,
    run_dir: Path,
    client: LMStudioClient,
    model: str,
    temperature: float,
    debug_dir: Path,
    no_think: bool,
) -> str:
    """v3.5：深挖 + 中间结果落盘版。事件、角色、关系都分块抽取再合并；慢，但信息量更厚。"""
    user_prompts = tail_text(read_text(run_dir / "user_only.txt"), 12000)
    canon_notes = tail_text(read_text(run_dir / "canon_notes.md"), 8000)
    removed_meta = tail_text(read_text(run_dir / "removed_meta.md"), 7000)
    story_head = head_text(story, 9000)
    story_tail = tail_text(story, 18000)

    section_dir = debug_dir / "init_bible_sections_v3_5"
    section_dir.mkdir(parents=True, exist_ok=True)
    draft_sections: List[Tuple[str, str]] = []

    def save_section(filename: str, title: str, content: str) -> None:
        clean = strip_top_title(content).strip()
        write_text(section_dir / filename, f"# {title}\n\n{clean}\n")
        draft_sections.append((title, clean))
        draft = ["# 当前设定状态（v3.5 中间草稿）", ""]
        for idx, (t, c) in enumerate(draft_sections, 1):
            draft.append(f"## {idx}. {t}")
            draft.append("")
            draft.append(c)
            draft.append("")
        write_text(section_dir / "00_当前设定状态_中间草稿_失败也能看.md", "\n".join(draft).strip() + "\n")
        print(f"[checkpoint] 已写入栏目中间结果：{section_dir / filename}")

    events = build_events_timeline_deep(
        story=story,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
    )
    save_section("02_已发生正史事件.md", "已发生正史事件", events)

    # 当前进度不再把全部 source + 全部 events 一锅塞爆；只用事件尾部 + 正文尾部。
    print("[init_bible/progress] 生成当前故事进度与停顿点……")
    progress = rich_section_complete(
        client,
        f"""你要整理长篇小说的“当前故事进度”和“当前场景/停顿点”。\n\n重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>。\n要求：\n- 不续写，不脑补。\n- 写清故事现在推进到哪、当前人物在哪、局面卡在什么动作/情绪/冲突上。\n- 用 8～18 条概括整体阶段变化，并单独写“当前停顿点”。\n- 信息要具体，不要只写空泛概述。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown。\n\n已发生正史事件尾部：\n<<<EVENTS_TAIL\n{tail_text(events, 18000)}\nEVENTS_TAIL>>>\n\n正文尾部：\n<<<STORY_TAIL\n{story_tail}\nSTORY_TAIL>>>\n\n用户最近提示词/作者意图：\n<<<USER_PROMPTS\n{tail_text(user_prompts, 6000)}\nUSER_PROMPTS>>>""",
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        tag="init_progress",
        no_think=no_think,
        max_tokens=14000,
    )
    save_section("01_当前故事进度与停顿点.md", "当前故事进度与停顿点", progress)

    character_body = """任务：只阅读本段正文，提取本段里的“角色状态事实”。\n要求：\n- 按角色名分组。\n- 每个角色尽量记录：身份/职能、行动、身体状态、心理状态、目标、秘密/压力、与其他人的关系变化。\n- 哪怕是配角，只要本段有有效状态变化，也要记录。\n- 不要写风格分析，不要续写，不要脑补。\n- 不确定就标注“不确定”。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown，信息越具体越好，不要省略。"""
    char_notes = extract_chunk_notes_rich(
        story=story,
        section_name="主要角色当前状态",
        chunk_prompt_body=character_body,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="characters",
        chunk_chars=14000,
        max_tokens=12000,
    )
    char_req = f"""要求：\n- 按角色分组，合并每个角色的最新有效状态。\n- 每个重要角色写：身份/功能、已发生关键经历、当前身体状态、心理状态、目标、秘密/压力、与当前场景的关系。\n- 如果早期状态已被后文更新，以后文最新状态为准，但可保留必要来龙去脉。\n- 不要把废案写成正史。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown，不要省略到只剩几句。\n\n可参考的最新剧情尾部：\n<<<CURRENT_PROGRESS\n{progress}\nCURRENT_PROGRESS>>>"""
    characters = merge_section_notes_rich(
        notes=char_notes,
        section_name="主要角色当前状态",
        merge_requirements=char_req,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="characters",
        max_chars_per_merge=26000,
        max_tokens=14000,
    )
    save_section("03_主要角色当前状态.md", "主要角色当前状态", characters)

    relationship_body = """任务：只阅读本段正文，提取本段里的“角色关系事实”。\n要求：\n- 按关系对/关系组记录，例如 A-B、A-B-C。\n- 写清：谁与谁、发生了什么互动、权力/信任/依赖/误解/控制/保护/敌意/暧昧等状态如何变化。\n- 不要写没有文本依据的关系。\n- 不要续写，不要脑补。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown，信息越具体越好，不要省略。"""
    rel_notes = extract_chunk_notes_rich(
        story=story,
        section_name="角色关系状态",
        chunk_prompt_body=relationship_body,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="relationships",
        chunk_chars=14000,
        max_tokens=12000,
    )
    rel_req = f"""要求：\n- 按关系对/关系组整理，保留具体变化链。\n- 写清：关系起点、已经发生的变化、当前张力、权力结构、信任/误解/依赖/控制/保护/敌意等状态。\n- 结合角色状态，但不要脑补文本外关系。\n- 不要把废案写成正史。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown，不要省略到只剩几句。\n\n主要角色当前状态参考：\n<<<CHARACTERS\n{characters}\nCHARACTERS>>>"""
    relationships = merge_section_notes_rich(
        notes=rel_notes,
        section_name="角色关系状态",
        merge_requirements=rel_req,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="relationships",
        max_chars_per_merge=24000,
        max_tokens=14000,
    )
    save_section("04_角色关系状态.md", "角色关系状态", relationships)

    world_body = """任务：只阅读本段正文，提取世界观、规则、仪式、物件、意象、地点、组织、风格偏好。\n要求：\n- 按类别记录。\n- 只记录文本里出现或作者明确要求的内容。\n- 不要把废案/候选方案写成正史。\n- 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。\n- 输出 Markdown。"""
    world_notes = extract_chunk_notes_rich(
        story=story,
        section_name="世界观规则风格",
        chunk_prompt_body=world_body,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="world_style",
        chunk_chars=18000,
        max_tokens=10000,
    )
    world_req = """要求：\n- 分成：世界观/规则/仪式；地点/组织；物件/意象；写作风格与作者偏好。\n- 只记录当前有效信息。\n- 不要把废案、备选方案、AI 建议混入正史。\n- 输出 Markdown，信息要具体。"""
    world_style = merge_section_notes_rich(
        notes=world_notes,
        section_name="世界观规则风格",
        merge_requirements=world_req,
        client=client,
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        no_think=no_think,
        tag_prefix="world_style",
        max_chars_per_merge=24000,
        max_tokens=12000,
    )
    save_section("05_世界观规则风格.md", "世界观、规则、仪式、地点、物件、意象", world_style)

    print("[init_bible/discard] 生成废案/不要带入/待确认……")
    discard = rich_section_complete(
        client,
        f"""你要整理长篇小说的“废案/不要带入/待确认”。\n\n重要：不要思考、不要解释、不要输出分析过程；禁止输出 <think>。\n要求：\n- 只记录明确不是正史、被覆盖、候选方案、AI 交互建议、需要作者确认的内容。\n- 如果没有，写“暂无明确废案”。\n- 不要展开成人/亲密/身体细节。\n- 输出 Markdown。\n\n正文抽取判断记录：\n<<<CANON_NOTES\n{canon_notes}\nCANON_NOTES>>>\n\n被剔除交互记录节选：\n<<<REMOVED_META\n{removed_meta}\nREMOVED_META>>>\n\n用户提示词节选：\n<<<USER_PROMPTS\n{user_prompts}\nUSER_PROMPTS>>>""",
        model=model,
        temperature=temperature,
        debug_dir=debug_dir,
        tag="init_discard",
        no_think=no_think,
        max_tokens=10000,
    )
    save_section("07_废案不要带入待确认.md", "废案/不要带入/待确认", discard)

    return f"""# 当前设定状态

## 1. 当前故事进度与停顿点

{strip_top_title(progress)}

## 2. 已发生正史事件

{strip_top_title(events)}

## 3. 主要角色当前状态

{strip_top_title(characters)}

## 4. 角色关系状态

{strip_top_title(relationships)}

## 5. 世界观、规则、仪式、地点、物件、意象

{strip_top_title(world_style)}

## 6. 写作风格与作者偏好

{strip_top_title(world_style)}

## 7. 废案/不要带入/待确认

{strip_top_title(discard)}
"""

def absorb_plan_prompt(
    *,
    old_bible: str,
    old_recent: str,
    new_head: str,
    new_tail: str,
    omitted_notice: str,
    new_user_prompts: str,
    new_canon_notes: str,
    auto_trim_chars: int,
) -> str:
    return f"""你是“长篇小说正史吸收器”。

你会看到：
1. 旧 master 的当前设定状态。
2. 旧 master 的最近正文。
3. 新 Grok 窗口抽取出的 story_canon 的开头与结尾。
4. 新窗口里的用户提示词与抽取判断记录。

你的任务：
判断这个新窗口应该如何吸收到旧 master，不是简单硬合并。

你必须返回严格 JSON，不要 Markdown，不要解释 JSON 外的任何文字。

JSON 格式：

{{
  "action": "append | replace_tail | discard | no_story_change",
  "trim_head_chars": 0,
  "replace_from_quote": "",
  "reason": "为什么这样吸收，简短中文",
  "current_bible": "# 当前设定状态\\n...",
  "discarded_or_overridden": "本次发现的废案、覆盖旧设定、不要带入内容；没有则写无",
  "absorb_report": "本次吸收报告：新增了什么，替换了什么，当前停在哪里"
}}

字段解释：
- action:
  - append：新窗口是旧文之后的自然续写，把新窗口正文裁掉开头重复后追加到 master。
  - replace_tail：新窗口重写/覆盖了旧 master 结尾，应从旧文中的 replace_from_quote 开始替换到末尾，再接入新窗口正文。
  - discard：新窗口主要是废案、测试、总结或不应进入正史。
  - no_story_change：没有新增正文，只更新设定/备注。
- trim_head_chars:
  - 新窗口 story_canon 开头有多少字符是重复旧文/启动包/回声，应该裁掉。
  - 脚本自动检测到的重叠字符数是：{auto_trim_chars}
  - 如果你没有更可靠判断，可以使用这个数。
- replace_from_quote:
  - 只有 action=replace_tail 时填写。
  - 必须是旧 master 最近正文里能精确找到的一小段原文，20-120 字。
  - 如果找不到可靠替换点，就不要用 replace_tail，改用 append。
- current_bible:
  - 输出更新后的“当前设定状态”，不是本次摘要。
  - 必须以 Markdown 字符串形式放进 JSON。
  - 只保留当前有效设定；废案放 discarded_or_overridden。
- discarded_or_overridden:
  - 本窗口导致哪些旧内容作废、哪些候选路线不要带入。
- absorb_report:
  - 给作者看的吸收报告。

判断原则：
1. 用户最新提示优先于旧设定。
2. 新窗口如果开头只是复述旧正文，应裁掉重复开头。
3. 如果新窗口明显重写旧结尾，用 replace_tail。
4. 不要把总结、设定表、候选方案当作正文。
5. 不要新增资料中没有的信息。
6. current_bible 要面向下一个 Grok 窗口，清楚、稳定、可执行。
7. 成人/亲密/身体内容只做概括性上下文记录，不扩写细节。

旧 master 当前设定：
<<<OLD_BIBLE
{old_bible}
OLD_BIBLE>>>

旧 master 最近正文：
<<<OLD_RECENT_STORY
{old_recent}
OLD_RECENT_STORY>>>

新窗口 story_canon 开头：
<<<NEW_STORY_HEAD
{new_head}
NEW_STORY_HEAD>>>

{omitted_notice}

新窗口 story_canon 结尾：
<<<NEW_STORY_TAIL
{new_tail}
NEW_STORY_TAIL>>>

新窗口用户提示词：
<<<NEW_USER_PROMPTS
{new_user_prompts}
NEW_USER_PROMPTS>>>

新窗口正文抽取判断记录：
<<<NEW_CANON_NOTES
{new_canon_notes}
NEW_CANON_NOTES>>>"""


# =========================
# 吸收逻辑
# =========================

def init_master_from_run(
    *,
    project_dir: Path,
    run_dir: Path,
    client: LMStudioClient,
    model: str,
    temperature: float,
    no_think: bool,
) -> None:
    paths = project_paths(project_dir)
    story = read_text(run_dir / "story_canon.md").strip()
    if not story:
        raise RuntimeError(f"run 目录缺少 story_canon.md：{run_dir}")

    snapshot_master(project_dir)

    write_text(master_story_path(project_dir), "# 当前正史正文\n\n" + strip_top_title(story).strip() + "\n")

    # 优先用 v6 完整跑出的 final_bible/worldbook；否则本脚本生成一个 master_bible
    context = read_text(run_dir / "final_bible.md").strip()
    if not context:
        context = read_text(run_dir / "worldbook.md").strip()

    if context:
        bible = strip_top_title(context)
    else:
        print("[init] 没有 final_bible/worldbook，调用模型分栏目生成当前设定状态……")
        # v3.3：不再把“当前设定状态”一锅炖。
        # 先按全文分块抽取“已发生正史事件”，再分别生成：进度、角色、关系、世界观/风格、废案。
        # 每个栏目都有独立输出预算，质量更厚；代价是初始化会慢一些。
        bible = build_rich_bible_sections(
            story=story,
            run_dir=run_dir,
            client=client,
            model=model,
            temperature=temperature,
            debug_dir=paths["debug"],
            no_think=no_think,
        )

    write_text(master_bible_path(project_dir), "# 当前设定状态\n\n" + strip_top_title(bible).strip() + "\n")
    write_text(discarded_log_path(project_dir), "# 废案和覆盖记录\n\n暂无。\n")
    write_text(absorb_log_path(project_dir), f"# 吸收日志\n\n## {now_str()} 初始化 master\n\n来源：`{run_dir}`\n")

    state = load_master_state(project_dir)
    state.setdefault("absorbed_runs", [])
    state["absorbed_runs"].append(str(run_dir.resolve()))
    state["updated_at"] = now_str()
    save_master_state(project_dir, state)

    print("[init] master 初始化完成。")


def absorb_run_incrementally(
    *,
    project_dir: Path,
    run_dir: Path,
    client: LMStudioClient,
    model: str,
    temperature: float,
    old_recent_chars: int,
    new_head_chars: int,
    new_tail_chars: int,
    no_think: bool,
    force: bool,
) -> None:
    run_key = str(run_dir.resolve())
    state = load_master_state(project_dir)
    absorbed = set(state.get("absorbed_runs") or [])

    if run_key in absorbed and not force:
        print(f"[SKIP] 这个 run 已经吸收过：{run_dir}")
        return

    new_story = read_text(run_dir / "story_canon.md").strip()
    if not new_story:
        raise RuntimeError(f"run 目录缺少 story_canon.md：{run_dir}")

    old_story = read_text(master_story_path(project_dir)).strip()
    old_bible = read_text(master_bible_path(project_dir)).strip()

    # v3.3.3：rich bible 可能很厚。吸收判断不需要把整份 02_当前设定状态 全塞进去，
    # 否则 old_bible + old_recent + new_head/tail 会超过 LM Studio 上下文。
    # master 文件本身不删减，只对“吸收判断 prompt”做安全裁剪。
    ABSORB_BIBLE_MAX_CHARS = 18000

    def _compress_bible_for_prompt(src: str, limit: int) -> str:
        if len(src) <= limit:
            return src
        half = max(2000, limit // 2)
        return (
            head_text(src, half)
            + "\n\n【中间设定省略：仅用于本次吸收判断，master\\02_当前设定状态.md 原文不删减。】\n\n"
            + tail_text(src, half)
        )

    old_bible_for_prompt = _compress_bible_for_prompt(old_bible, ABSORB_BIBLE_MAX_CHARS)

    if not old_story:
        init_master_from_run(
            project_dir=project_dir,
            run_dir=run_dir,
            client=client,
            model=model,
            temperature=temperature,
            no_think=no_think,
        )
        return

    snapshot_master(project_dir)

    auto_trim = find_exact_overlap_chars(old_story, new_story)

    new_head = head_text(new_story, new_head_chars)
    new_tail = tail_text(new_story, new_tail_chars)
    notice = middle_notice(new_story, new_head, new_tail)

    new_user_prompts = tail_text(read_text(run_dir / "user_only.txt"), 8000)
    new_canon_notes = tail_text(read_text(run_dir / "canon_notes.md"), 6000)
    old_recent = tail_text(old_story, old_recent_chars)

    paths = project_paths(project_dir)
    print("[absorb] evaluating incremental absorb strategy...")
    print(f"[absorb] prompt trimmed: old_bible {len(old_bible)} -> {len(old_bible_for_prompt)} chars; old_recent={old_recent_chars}, new_head={new_head_chars}, new_tail={new_tail_chars}")
    absorb_tag = f"absorb_{safe_name(run_dir.name, 40)}"
    budget = ABSORB_BIBLE_MAX_CHARS
    last_err: Optional[Exception] = None
    raw = ""
    for round_idx in range(4):
        old_bible_for_prompt = _compress_bible_for_prompt(old_bible, budget)
        try:
            raw = client.complete(
                absorb_plan_prompt(
                    old_bible=old_bible_for_prompt,
                    old_recent=old_recent,
                    new_head=new_head,
                    new_tail=new_tail,
                    omitted_notice=notice,
                    new_user_prompts=new_user_prompts,
                    new_canon_notes=new_canon_notes,
                    auto_trim_chars=auto_trim,
                ),
                model=model,
                max_tokens=10000,
                temperature=temperature,
                debug_dir=paths["debug"],
                tag=absorb_tag,
                no_think=no_think,
            )
            break
        except RuntimeError as e:
            last_err = e
            msg = str(e)
            is_ctx_overflow = (
                ("n_keep" in msg and "n_ctx" in msg)
                or ("exceeds the available context size" in msg)
                or ("greater than the context length" in msg)
                or ("request (" in msg and "context" in msg)
            )
            if is_ctx_overflow and round_idx < 3:
                budget = max(4000, int(budget * 0.65))
                print(f"[absorb] context overflow; retrying with smaller old_bible budget={budget}")
                continue
            raise
    if not raw and last_err:
        raise last_err

    write_text(paths["debug"] / f"{stamp_now()}_absorb_raw.txt", raw)

    try:
        plan = extract_json_object(raw)
    except Exception as e:
        write_text(paths["debug"] / f"{stamp_now()}_absorb_json_parse_failed.txt", raw)
        raise RuntimeError(f"吸收模型没有返回合法 JSON：{e}")

    write_json(paths["debug"] / f"{stamp_now()}_absorb_plan.json", plan)

    new_master_story, apply_note = apply_absorb_plan(
        old_story=old_story,
        new_story=new_story,
        plan=plan,
        auto_trim_chars=auto_trim,
    )

    current_bible = str(plan.get("current_bible") or "").strip()
    if not current_bible:
        current_bible = old_bible

    discarded = str(plan.get("discarded_or_overridden") or "无").strip()
    report = str(plan.get("absorb_report") or plan.get("reason") or "").strip()
    reason = str(plan.get("reason") or "").strip()

    write_text(master_story_path(project_dir), new_master_story.strip() + "\n")
    write_text(master_bible_path(project_dir), "# 当前设定状态\n\n" + strip_top_title(current_bible).strip() + "\n")

    old_discarded = read_text(discarded_log_path(project_dir)).strip()
    new_discarded = (
        old_discarded
        + f"\n\n---\n\n## {now_str()} / {run_dir.name}\n\n"
        + discarded.strip()
        + "\n"
    )
    write_text(discarded_log_path(project_dir), new_discarded.strip() + "\n")

    old_log = read_text(absorb_log_path(project_dir)).strip()
    log_entry = f"""
---

## {now_str()} / 吸收 {run_dir.name}

- action：{plan.get("action")}
- reason：{reason}
- apply_note：{apply_note}

### 吸收报告

{report}

### run 目录

`{run_dir}`
"""
    write_text(absorb_log_path(project_dir), (old_log + "\n\n" + log_entry).strip() + "\n")

    state.setdefault("absorbed_runs", [])
    if run_key not in state["absorbed_runs"]:
        state["absorbed_runs"].append(run_key)
    state["updated_at"] = now_str()
    save_master_state(project_dir, state)

    print("[absorb] 已更新 master。")
    print(f"  action: {plan.get('action')}")
    print(f"  {apply_note}")


# =========================
# handoff 生成
# =========================

def build_handoff_prompt(*, bible: str, recent_story: str, recent_chars: int, project_dir: Path) -> str:
    return f"""# 下个 Grok 窗口直接复制这个

你现在接手一部长篇故事续写。请严格基于我提供的上下文继续写，不要重启故事，不要总结，不要解释，不要输出创作分析。

你的任务不是改写设定，也不是概括剧情，而是像之前一样，根据我给出的剧情方向，把下一段扩写成沉浸式小说正文。

## 硬规则

1. 只输出小说正文。
2. 不要说“好的”“我明白了”“下面是扩写”。
3. 不要在文末给建议。
4. 不要擅自跳过情绪过程。
5. 不要突然改变角色性格、关系状态、身体状态、场景位置。
6. 如果我的新要求和旧设定冲突，以我最新要求为准，但不要主动解释冲突。
7. 保持前文的叙事密度、心理压迫感、身体细节感、场景连续性和角色之间的张力。
8. 你可以补足动作、心理、环境、停顿、潜台词，但不要新增重大世界观设定。
9. 每次只写当前这一段，不要替我规划后续。
10. 不要把下面的设定档当成要复述的内容，它只用于理解上下文。

## 来源说明

- 项目目录：`{project_dir}`
- 最近正文截取：约 {recent_chars} 字

## 当前设定状态

<<<CURRENT_BIBLE
{bible}
CURRENT_BIBLE>>>

## 最近正文

以下是当前正史正文末尾的一段。请从它之后承接语气、节奏、情绪和场景连续性。

<<<RECENT_STORY
{recent_story}
RECENT_STORY>>>

## 我接下来要写的是

把你的新剧情方向、关键台词、角色动作、情绪目标写在这里。

<<<NEXT_DIRECTION

NEXT_DIRECTION>>>
"""


def build_status(project_dir: Path, recent_chars: int) -> str:
    run_dirs = discover_run_dirs(project_dir)
    state = load_master_state(project_dir)
    absorbed = set(state.get("absorbed_runs") or [])

    lines = [
        "# 状态说明",
        "",
        f"- 更新时间：{now_str()}",
        f"- 项目目录：`{project_dir}`",
        f"- 已归档窗口数：{len(run_dirs)}",
        f"- 已吸收窗口数：{len(absorbed)}",
        f"- 最近正文截取长度：{recent_chars}",
        "",
        "## 你真正要用的文件",
        "",
        "1. `03_下个窗口直接复制这个.md`：最推荐，直接复制给 Grok。",
        "2. `01_当前设定状态_喂给Grok.md`：如果想分开发，这是设定文件。",
        "3. `02_最近正文_喂给Grok.md`：如果想分开发，这是最近正文。",
        "",
        "## 窗口列表",
        "",
        "| 序号 | 状态 | 标题 | 消息数 | USER | GROK | run_dir |",
        "|---:|---|---|---:|---:|---:|---|",
    ]

    for i, d in enumerate(run_dirs, 1):
        key = str(d.resolve())
        msg_count, user_count, grok_count = count_raw_messages(d / "raw_messages.jsonl")
        lines.append(
            f"| {i} | {'已吸收' if key in absorbed else '未吸收'} | "
            f"{session_title(d, i)} | "
            f"{msg_count if msg_count else ''} | "
            f"{user_count if msg_count else ''} | "
            f"{grok_count if msg_count else ''} | "
            f"`{d}` |"
        )

    lines.extend([
        "",
        "## 循环方式",
        "",
        "1. Grok 新窗口写到快失忆。",
        "2. 保存当前窗口为 `.mhtml`。",
        "3. 运行本脚本，选 `1`。",
        "4. 打开 `handoff\\03_下个窗口直接复制这个.md`，复制给下一个 Grok。",
        "",
        "注意：每个窗口独立归档；master 不是硬合并，而是增量吸收。",
    ])

    return "\n".join(lines).strip() + "\n"


def generate_handoff(project_dir: Path, recent_chars: int) -> None:
    paths = project_paths(project_dir)
    bible = read_text(master_bible_path(project_dir)).strip()
    story = read_text(master_story_path(project_dir)).strip()

    if not story:
        raise RuntimeError("还没有 master 正文。请先吸收至少一个窗口。")

    if not bible:
        bible = "【暂无当前设定状态】\n请主要依据最近正文和我的新剧情方向续写，不要擅自新增重大设定。"

    recent = tail_text(story, recent_chars)
    prompt = build_handoff_prompt(
        bible=bible,
        recent_story=recent,
        recent_chars=recent_chars,
        project_dir=project_dir,
    )

    handoff = paths["handoff"]
    write_text(handoff / "01_当前设定状态_喂给Grok.md", bible.strip() + "\n")
    write_text(handoff / "02_最近正文_喂给Grok.md", recent.strip() + "\n")
    write_text(handoff / "03_下个窗口直接复制这个.md", prompt.strip() + "\n")
    write_text(handoff / "04_废案和覆盖记录_自己查.md", read_text(discarded_log_path(project_dir)).strip() + "\n")
    write_text(handoff / "05_吸收日志_自己查.md", read_text(absorb_log_path(project_dir)).strip() + "\n")
    write_text(handoff / "99_状态说明.md", build_status(project_dir, recent_chars))

    print("\n[DONE] 已生成下个窗口投喂包：")
    print(f"  {handoff}")
    print("\n最重要的是这个：")
    print(f"  {handoff / '03_下个窗口直接复制这个.md'}")


# =========================
# 菜单
# =========================

def make_client_and_model(base_url: str, timeout: int, max_retries: int, model: Optional[str]) -> Tuple[LMStudioClient, str]:
    client = LMStudioClient(base_url, timeout_seconds=timeout, max_retries=max_retries)
    model_id = model or client.auto_model()
    print(f"[LM Studio] 使用模型：{model_id}")
    return client, model_id


def print_header() -> None:
    print("=" * 74)
    print("Grok 故事投喂包整理器 v3.5（深挖设定 + 中间结果落盘版）")
    print("=" * 74)
    print()


def print_config(mhtml_path: Path, v6_script: Path, project_dir: Path, base_url: str, model: Optional[str]) -> None:
    paths = project_paths(project_dir)
    print("当前配置：")
    print(f"  当前要吸收的 MHTML : {mhtml_path}")
    print(f"  v6 脚本            : {v6_script}")
    print(f"  项目总目录         : {project_dir}")
    print(f"  每窗口独立输出目录 : {paths['runs']}")
    print(f"  master 活档案目录  : {paths['master']}")
    print(f"  最终投喂包目录     : {paths['handoff']}")
    print(f"  LM Studio          : {base_url}")
    print(f"  模型               : {model or '自动选择第一个'}")
    print()


def interactive_main() -> None:
    mhtml_path = Path(DEFAULT_MHTML)
    v6_script = Path(DEFAULT_V6_SCRIPT)
    project_dir = Path(DEFAULT_PROJECT_DIR)

    base_url = DEFAULT_BASE_URL
    model: Optional[str] = None
    part_chars = DEFAULT_PART_CHARS
    canon_part_chars = DEFAULT_CANON_PART_CHARS
    recent_chars = DEFAULT_RECENT_CHARS
    old_recent_chars = DEFAULT_OLD_RECENT_CHARS
    new_head_chars = DEFAULT_NEW_HEAD_CHARS
    new_tail_chars = DEFAULT_NEW_TAIL_CHARS
    timeout = DEFAULT_TIMEOUT_SECONDS
    max_retries = DEFAULT_MAX_RETRIES
    temperature = DEFAULT_TEMPERATURE
    no_think = True

    while True:
        print_header()
        print_config(mhtml_path, v6_script, project_dir, base_url, model)

        print("你要做什么？")
        print("  1. 吸收当前 MHTML：跑 v6 → 增量更新 master → 生成投喂包（推荐）")
        print("  2. 只根据现有 master 重新生成投喂包")
        print("  3. 吸收当前 MHTML，但跑完整 v6（更慢，会生成 worldbook/final_bible）")
        print("  4. 只跑 v6 归档当前 MHTML，不吸收进 master")
        print("  5. 吸收一个已经跑好的 run 目录")
        print("  6. 修改路径 / 参数")
        print("  7. 查看状态")
        print("  8. 退出")
        print()

        choice = input("输入 1/2/3/4/5/6/7/8: ").strip()

        try:
            if choice == "1":
                redo_run = ask_yes_no("是否强制重跑这个窗口的 v6？", default=False)
                force_absorb = ask_yes_no("如果这个窗口之前吸收过，是否强制再吸收？", default=False)

                run_dir = process_one_mhtml(
                    mhtml_path=mhtml_path,
                    v6_script=v6_script,
                    project_dir=project_dir,
                    part_chars=part_chars,
                    canon_part_chars=canon_part_chars,
                    full_v6=False,
                    redo=redo_run,
                )

                client, model_id = make_client_and_model(base_url, timeout, max_retries, model)
                absorb_run_incrementally(
                    project_dir=project_dir,
                    run_dir=run_dir,
                    client=client,
                    model=model_id,
                    temperature=temperature,
                    old_recent_chars=old_recent_chars,
                    new_head_chars=new_head_chars,
                    new_tail_chars=new_tail_chars,
                    no_think=no_think,
                    force=force_absorb,
                )
                generate_handoff(project_dir, recent_chars)
                pause()

            elif choice == "2":
                generate_handoff(project_dir, recent_chars)
                pause()

            elif choice == "3":
                redo_run = ask_yes_no("是否强制重跑完整 v6？", default=False)
                force_absorb = ask_yes_no("如果这个窗口之前吸收过，是否强制再吸收？", default=False)

                run_dir = process_one_mhtml(
                    mhtml_path=mhtml_path,
                    v6_script=v6_script,
                    project_dir=project_dir,
                    part_chars=part_chars,
                    canon_part_chars=canon_part_chars,
                    full_v6=True,
                    redo=redo_run,
                )

                client, model_id = make_client_and_model(base_url, timeout, max_retries, model)
                absorb_run_incrementally(
                    project_dir=project_dir,
                    run_dir=run_dir,
                    client=client,
                    model=model_id,
                    temperature=temperature,
                    old_recent_chars=old_recent_chars,
                    new_head_chars=new_head_chars,
                    new_tail_chars=new_tail_chars,
                    no_think=no_think,
                    force=force_absorb,
                )
                generate_handoff(project_dir, recent_chars)
                pause()

            elif choice == "4":
                redo_run = ask_yes_no("是否强制重跑这个窗口的 v6？", default=False)
                full_v6 = ask_yes_no("是否跑完整 v6？默认只跑正文抽取", default=False)
                run_dir = process_one_mhtml(
                    mhtml_path=mhtml_path,
                    v6_script=v6_script,
                    project_dir=project_dir,
                    part_chars=part_chars,
                    canon_part_chars=canon_part_chars,
                    full_v6=full_v6,
                    redo=redo_run,
                )
                print(f"\n已生成 run：{run_dir}")
                pause()

            elif choice == "5":
                raw = ask("输入已经跑好的 run 目录")
                run_dir = Path(raw)
                if not run_dir.exists():
                    raise FileNotFoundError(run_dir)

                force_absorb = ask_yes_no("如果这个 run 之前吸收过，是否强制再吸收？", default=False)
                client, model_id = make_client_and_model(base_url, timeout, max_retries, model)
                absorb_run_incrementally(
                    project_dir=project_dir,
                    run_dir=run_dir,
                    client=client,
                    model=model_id,
                    temperature=temperature,
                    old_recent_chars=old_recent_chars,
                    new_head_chars=new_head_chars,
                    new_tail_chars=new_tail_chars,
                    no_think=no_think,
                    force=force_absorb,
                )
                generate_handoff(project_dir, recent_chars)
                pause()

            elif choice == "6":
                print()
                mhtml_path = Path(ask("当前要吸收的 MHTML", str(mhtml_path)))
                v6_script = Path(ask("v6 脚本", str(v6_script)))
                project_dir = Path(ask("项目总目录", str(project_dir)))
                base_url = ask("LM Studio base_url", base_url)
                model_in = ask("模型 ID，留空则自动", model or "")
                model = model_in or None
                part_chars = int(ask("part_chars", str(part_chars)))
                canon_part_chars = int(ask("canon_part_chars", str(canon_part_chars)))
                recent_chars = int(ask("recent_chars 给 Grok 的最近正文长度", str(recent_chars)))
                old_recent_chars = int(ask("old_recent_chars 吸收判断用旧正文尾巴", str(old_recent_chars)))
                new_head_chars = int(ask("new_head_chars 吸收判断用新窗口开头", str(new_head_chars)))
                new_tail_chars = int(ask("new_tail_chars 吸收判断用新窗口结尾", str(new_tail_chars)))
                temperature = float(ask("temperature", str(temperature)))
                no_think = ask_yes_no("是否默认加 /no_think？", default=no_think)

            elif choice == "7":
                print()
                print(build_status(project_dir, recent_chars))
                pause()

            elif choice == "8":
                print("退出。")
                return

            else:
                print("没看懂，输入 1/2/3/4/5/6/7/8。")
                pause()

        except subprocess.CalledProcessError as e:
            print("\n[ERROR] v6 脚本运行失败。")
            print(f"退出码：{e.returncode}")
            pause()
        except Exception as e:
            print("\n[ERROR]")
            print(e)
            pause()


# =========================
# CLI 模式
# =========================

def cli_main(argv: List[str]) -> bool:
    if len(argv) <= 1:
        return False

    ap = argparse.ArgumentParser(description="Grok 故事投喂包整理器 v3.5（深挖设定 + 中间结果落盘版）")
    ap.add_argument("--mhtml", default=DEFAULT_MHTML)
    ap.add_argument("--v6", default=DEFAULT_V6_SCRIPT)
    ap.add_argument("--project-dir", default=DEFAULT_PROJECT_DIR)
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ap.add_argument("--model", default=None)

    ap.add_argument("--part-chars", type=int, default=DEFAULT_PART_CHARS)
    ap.add_argument("--canon-part-chars", type=int, default=DEFAULT_CANON_PART_CHARS)
    ap.add_argument("--recent-chars", type=int, default=DEFAULT_RECENT_CHARS)
    ap.add_argument("--old-recent-chars", type=int, default=DEFAULT_OLD_RECENT_CHARS)
    ap.add_argument("--new-head-chars", type=int, default=DEFAULT_NEW_HEAD_CHARS)
    ap.add_argument("--new-tail-chars", type=int, default=DEFAULT_NEW_TAIL_CHARS)

    ap.add_argument("--run-v6", action="store_true", help="先跑 v6 处理当前 mhtml")
    ap.add_argument("--full-v6", action="store_true", help="跑完整 v6，而不是 --only-canon")
    ap.add_argument("--redo-run", action="store_true", help="强制重跑 v6")
    ap.add_argument("--absorb", action="store_true", help="吸收当前 mhtml 对应 run 到 master")
    ap.add_argument("--force-absorb", action="store_true", help="已吸收过也强制再吸收")
    ap.add_argument("--handoff", action="store_true", help="生成 handoff")
    ap.add_argument("--run-dir", default=None, help="直接吸收已有 run 目录")
    ap.add_argument("--think", action="store_true", help="不加 /no_think")
    ap.add_argument("--test-lm", action="store_true", help="仅测试 LM Studio 连接与模型可用性")

    args = ap.parse_args(argv[1:])

    project_dir = Path(args.project_dir)
    mhtml_path = Path(args.mhtml)
    v6_script = Path(args.v6)

    run_dir: Optional[Path] = Path(args.run_dir) if args.run_dir else None

    if args.test_lm:
        client = LMStudioClient(args.base_url, timeout_seconds=DEFAULT_TIMEOUT_SECONDS, max_retries=DEFAULT_MAX_RETRIES)
        model_id = args.model or client.auto_model()
        print(f"[LM Studio] 连接正常，模型：{model_id}")
        return True

    if args.run_v6:
        run_dir = process_one_mhtml(
            mhtml_path=mhtml_path,
            v6_script=v6_script,
            project_dir=project_dir,
            part_chars=args.part_chars,
            canon_part_chars=args.canon_part_chars,
            full_v6=args.full_v6,
            redo=args.redo_run,
        )

    if args.absorb:
        if run_dir is None:
            paths = project_paths(project_dir)
            archived = archive_mhtml(mhtml_path, paths["archive"])
            run_dir = run_dir_for_archived_mhtml(archived, paths["runs"])
        client = LMStudioClient(args.base_url, timeout_seconds=DEFAULT_TIMEOUT_SECONDS, max_retries=DEFAULT_MAX_RETRIES)
        model_id = args.model or client.auto_model()
        absorb_run_incrementally(
            project_dir=project_dir,
            run_dir=run_dir,
            client=client,
            model=model_id,
            temperature=DEFAULT_TEMPERATURE,
            old_recent_chars=args.old_recent_chars,
            new_head_chars=args.new_head_chars,
            new_tail_chars=args.new_tail_chars,
            no_think=not args.think,
            force=args.force_absorb,
        )

    if args.handoff:
        generate_handoff(project_dir, args.recent_chars)

    return True


def main() -> None:
    if not cli_main(sys.argv):
        interactive_main()


if __name__ == "__main__":
    main()
