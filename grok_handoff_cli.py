#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified command line entry for the Grok story handoff helper.

This file intentionally stays thin: it calls the existing v6 and v3.5
scripts through subprocess, so the core cleaning and handoff logic remains in
the original scripts.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Union


ROOT = Path(__file__).resolve().parent
V6_SCRIPT = ROOT / "grok_mhtml_bible_pipeline_v6.py"
HANDOFF_SCRIPT = ROOT / "grok_story_handoff_manager_v3_5_checkpoint_bible.py"
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_CANON_PART_CHARS = 12000


def add_common_lm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="LM Studio OpenAI-compatible Base URL",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Model name. 模型名；留空时沿用原脚本自动选择模型的逻辑。",
    )


def extend_if_value(cmd: List[str], flag: str, value: Optional[Union[str, int]]) -> None:
    if value is not None and str(value) != "":
        cmd.extend([flag, str(value)])


def run_command(cmd: Iterable[str]) -> int:
    cmd_list = list(cmd)
    print("[RUN]", " ".join(f'"{x}"' if " " in x else x for x in cmd_list))
    completed = subprocess.run(cmd_list, cwd=str(ROOT))
    return completed.returncode


def command_clean(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(V6_SCRIPT),
        "--input",
        str(args.input),
        "--output",
        str(args.output),
        "--base-url",
        args.base_url,
        "--canon-part-chars",
        str(args.canon_part_chars),
    ]
    extend_if_value(cmd, "--model", args.model)

    if args.only_canon:
        cmd.append("--only-canon")
    if args.redo:
        cmd.append("--redo")
    if args.dry_run:
        cmd.append("--dry-run")

    return run_command(cmd)


def command_absorb_run(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(HANDOFF_SCRIPT),
        "--run-dir",
        str(args.run_dir),
        "--project-dir",
        str(args.project_dir),
        "--base-url",
        args.base_url,
        "--absorb",
    ]
    extend_if_value(cmd, "--model", args.model)
    if args.force:
        cmd.append("--force-absorb")
    return run_command(cmd)


def command_handoff(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(HANDOFF_SCRIPT),
        "--project-dir",
        str(args.project_dir),
        "--handoff",
        "--recent-chars",
        str(args.recent_chars),
    ]
    return run_command(cmd)


def command_gui(_args: argparse.Namespace) -> int:
    cmd = [sys.executable, str(ROOT / "grok_handoff_gui.py")]
    return run_command(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Grok Story Handoff CLI. Input should be a Grok conversation saved as .mhtml. "
            "输入应该是 Grok 保存的 .mhtml 对话窗口。"
        ),
        epilog=(
            "Examples:\n"
            "  python grok_handoff_cli.py gui\n"
            "  python grok_handoff_cli.py clean --input \"D:\\path\\story.mhtml\" "
            "--output \"D:\\Grok_Project\\runs\\story_run\" --canon-part-chars 12000\n"
            "  python grok_handoff_cli.py absorb-run --run-dir "
            "\"D:\\Grok_Project\\runs\\story_run\" --project-dir \"D:\\Grok_Project\"\n"
            "  python grok_handoff_cli.py handoff --project-dir \"D:\\Grok_Project\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean = subparsers.add_parser(
        "clean",
        help="Clean a Grok .mhtml conversation into a run directory. 清洗 Grok 保存的 .mhtml 对话窗口。",
    )
    clean.add_argument("--input", required=True, help="Grok conversation saved as .mhtml/.mht. Grok 保存的 .mhtml 对话窗口。")
    clean.add_argument("--output", required=True, help="Output run directory. 输出 run 目录，例如 runs/window_001。")
    clean.add_argument(
        "--canon-part-chars",
        type=int,
        default=DEFAULT_CANON_PART_CHARS,
        help="Canon extraction chunk size in characters. 正文抽取阶段每块字符数。",
    )
    clean.add_argument("--only-canon", action="store_true", help="Only generate story_canon files. 只生成 story_canon 等正文文件。")
    clean.add_argument("--redo", action="store_true", help="Ask the original script to redo existing stages. 要求原脚本重做已有阶段。")
    clean.add_argument("--dry-run", action="store_true", help="Parse and split only, without calling the LLM. 只检查解析和切分，不调用 LLM。")
    add_common_lm_args(clean)
    clean.set_defaults(func=command_clean)

    absorb = subparsers.add_parser("absorb-run", help="Absorb a finished run into project master. 把已跑好的 run 目录吸收到项目 master。")
    absorb.add_argument("--run-dir", required=True, help="Run directory containing story_canon.md. 已生成 story_canon.md 的 run 目录。")
    absorb.add_argument("--project-dir", required=True, help="Project root directory. 项目总目录。")
    absorb.add_argument("--force", action="store_true", help="Force absorb even if already absorbed. 已吸收过也强制再吸收。")
    add_common_lm_args(absorb)
    absorb.set_defaults(func=command_absorb_run)

    handoff = subparsers.add_parser("handoff", help="Generate a handoff pack from project master. 从 project_dir/master 生成 handoff 包。")
    handoff.add_argument("--project-dir", required=True, help="Project root directory. 项目总目录。")
    handoff.add_argument("--recent-chars", type=int, default=9000, help="Recent story characters to include. 最近正文截取字符数。")
    handoff.set_defaults(func=command_handoff)

    gui = subparsers.add_parser("gui", help="Start the Tkinter GUI. 启动 Tkinter 图形界面。")
    gui.set_defaults(func=command_gui)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
