#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiny dictionary-based i18n helper for the Grok handoff GUI."""

from __future__ import annotations

import locale
import os
from typing import Dict


DEFAULT_LANGUAGE = "en-US"
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "zh-CN": "中文",
    "ja-JP": "日本語",
    "en-US": "English",
}
_CACHED_SYSTEM_LANGUAGE: str | None = None


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en-US": {
        "app_title": "Grok Story Handoff / Grok Story Toaster",
        "main_title": "Grok Story Handoff / Grok Story Toaster",
        "language": "Language",
        "input_section": "Input",
        "actions_section": "Actions",
        "progress_section": "Progress",
        "intro": (
            "Input: a Grok conversation window saved as .mhtml\n"
            "Output: cleaned story canon + handoff pack for the next Grok window\n"
            "First press Ctrl+S on the Grok page and save it as \"Webpage, Single File\" to get a .mhtml file.\n"
            "🍞 Raw .mhtml dough → slice and clean → canon toast → breakfast pack for the next window"
        ),
        "mhtml_file": ".mhtml file",
        "project_dir": "Project directory project_dir",
        "run_dir": "run directory",
        "base_url": "LM Studio Base URL",
        "model_name": "Model name",
        "model_hint": "Leave empty to auto-select, or enter a model such as 456@iq3_m",
        "canon_part_chars": "canon_part_chars",
        "browse": "Browse",
        "clean_current_mhtml": "Clean current MHTML",
        "absorb_run": "Absorb existing run directory",
        "generate_handoff": "Generate handoff pack",
        "open_handoff_folder": "Open handoff folder",
        "open_output_folder": "Open log/output folder",
        "stop_current_task": "Stop Current Task",
        "log": "Log",
        "status_idle": "Idle",
        "status_cleaning": "Cleaning MHTML...",
        "status_absorbing": "Absorbing run...",
        "status_handoff": "Generating handoff...",
        "status_completed": "Completed",
        "status_failed": "Failed, please check the log",
        "status_stopping": "Stopping...",
        "status_stopped": "Stopped",
        "choose_mhtml_title": "Select a Grok .mhtml file",
        "choose_project_title": "Select project directory",
        "choose_run_title": "Select an existing run directory",
        "select_mhtml": "Please select a .mhtml file",
        "mhtml_missing": ".mhtml file does not exist",
        "select_project_dir": "Please select a project directory",
        "select_run_dir": "Please select or generate a run directory",
        "run_dir_missing": "run directory does not exist",
        "task_running_title": "Task running",
        "task_running": "A task is already running. Please wait for it to finish.",
        "task_completed_title": "Task completed",
        "task_completed": "Task completed",
        "clean_success": "Cleaning completed. Next step: click \"Absorb existing run directory\".",
        "absorb_success": "Absorb completed. Next step: click \"Generate handoff pack\", then open the handoff folder.",
        "handoff_success": "Handoff generated. You can open the handoff folder and copy 03_下个窗口直接复制这个.md into the next Grok window.",
        "handoff_file_ready": "Handoff file is ready:",
        "task_failed_title": "Task failed",
        "task_failed": "Task failed, please check the log",
        "task_stopped_title": "Task stopped",
        "task_stopped": "Current task has been stopped.",
        "stop_requested": "User requested to stop the current task...",
        "stopping_process": "Stopping subprocess...",
        "lm_studio_hint": "If LM Studio is not running, check http://127.0.0.1:1234/v1 and make sure a model is loaded.",
        "handoff_missing_title": "handoff folder does not exist",
        "handoff_missing": "The handoff folder does not exist yet.",
        "output_missing_title": "Output folder not found",
        "output_missing": "No output folder is available yet.",
        "missing_info_title": "Missing information",
        "path_missing_title": "Path does not exist",
        "bad_format_title": "Invalid value",
        "canon_part_chars_invalid": "canon_part_chars must be a number",
    },
    "zh-CN": {
        "app_title": "Grok Story Handoff / Grok 小说交接面包机",
        "main_title": "Grok Story Handoff / Grok 小说交接面包机",
        "language": "语言",
        "input_section": "输入区",
        "actions_section": "操作区",
        "progress_section": "进度区",
        "intro": (
            "输入端：Grok 保存的 .mhtml 对话窗口\n"
            "输出端：清洗后的小说正文 + 下个 Grok 窗口续写交接包\n"
            "请先在 Grok 页面按 Ctrl+S，保存为“网页，单个文件 / Webpage, Single File”，得到 .mhtml 文件。\n"
            "🍞 原始 .mhtml 面团 → 切片清洗 → 正史吐司 → 下个窗口早餐包"
        ),
        "mhtml_file": ".mhtml 文件",
        "project_dir": "项目目录 project_dir",
        "run_dir": "run 目录",
        "base_url": "LM Studio Base URL",
        "model_name": "模型名",
        "model_hint": "留空则自动选择；也可填 456@iq3_m",
        "canon_part_chars": "canon_part_chars",
        "browse": "选择",
        "clean_current_mhtml": "清洗当前 MHTML",
        "absorb_run": "吸收已跑好的 run 目录",
        "generate_handoff": "生成 handoff 包",
        "open_handoff_folder": "打开 handoff 文件夹",
        "open_output_folder": "打开日志/输出目录",
        "stop_current_task": "停止当前任务",
        "log": "日志",
        "status_idle": "空闲",
        "status_cleaning": "正在清洗 MHTML……",
        "status_absorbing": "正在吸收 run……",
        "status_handoff": "正在生成 handoff……",
        "status_completed": "已完成",
        "status_failed": "失败，请查看日志",
        "status_stopping": "正在停止……",
        "status_stopped": "已停止",
        "choose_mhtml_title": "选择 Grok 保存的 .mhtml 文件",
        "choose_project_title": "选择项目目录",
        "choose_run_title": "选择已跑好的 run 目录",
        "select_mhtml": "请选择 .mhtml 文件",
        "mhtml_missing": ".mhtml 文件不存在",
        "select_project_dir": "请选择项目目录",
        "select_run_dir": "请选择或生成 run 目录",
        "run_dir_missing": "run 目录不存在",
        "task_running_title": "正在运行",
        "task_running": "当前已有任务在运行，请等它结束。",
        "task_completed_title": "任务完成",
        "task_completed": "任务完成",
        "clean_success": "清洗完成。下一步请点击“吸收已跑好的 run 目录”。",
        "absorb_success": "吸收完成。下一步请点击“生成 handoff 包”，然后打开 handoff 文件夹。",
        "handoff_success": "handoff 已生成。可以打开 handoff 文件夹，把 03_下个窗口直接复制这个.md 复制到下一个 Grok 窗口。",
        "handoff_file_ready": "handoff 文件已就绪：",
        "task_failed_title": "任务失败",
        "task_failed": "任务失败，请查看日志",
        "task_stopped_title": "任务已停止",
        "task_stopped": "当前任务已停止。",
        "stop_requested": "用户请求停止当前任务……",
        "stopping_process": "正在终止子进程……",
        "lm_studio_hint": "如果 LM Studio 未启动，请检查 http://127.0.0.1:1234/v1，并确认已经加载模型。",
        "handoff_missing_title": "handoff 文件夹不存在",
        "handoff_missing": "handoff 文件夹不存在",
        "output_missing_title": "找不到输出目录",
        "output_missing": "还没有找到可打开的日志/输出目录。",
        "missing_info_title": "缺少信息",
        "path_missing_title": "路径不存在",
        "bad_format_title": "格式错误",
        "canon_part_chars_invalid": "canon_part_chars 必须是数字",
    },
    "ja-JP": {
        "app_title": "Grok Story Handoff / Grok 小説引き継ぎトースター",
        "main_title": "Grok Story Handoff / Grok 小説引き継ぎトースター",
        "language": "言語",
        "input_section": "入力",
        "actions_section": "操作",
        "progress_section": "進行状況",
        "intro": (
            "入力：Grok の会話ウィンドウを .mhtml として保存したファイル\n"
            "出力：整理済みの小説本文 + 次の Grok ウィンドウへ渡す引き継ぎパック\n"
            "まず Grok ページで Ctrl+S を押し、「Webpage, Single File / 単一ファイルの Web ページ」として保存して .mhtml ファイルを作成してください。\n"
            "🍞 元の .mhtml 生地 → スライスして整理 → 正史トースト → 次のウィンドウ用の朝食パック"
        ),
        "mhtml_file": ".mhtml ファイル",
        "project_dir": "プロジェクトディレクトリ project_dir",
        "run_dir": "run ディレクトリ",
        "base_url": "LM Studio Base URL",
        "model_name": "モデル名",
        "model_hint": "空欄なら自動選択。例: 456@iq3_m",
        "canon_part_chars": "canon_part_chars",
        "browse": "参照",
        "clean_current_mhtml": "現在の MHTML を整理",
        "absorb_run": "完了済み run ディレクトリを吸収",
        "generate_handoff": "handoff パックを生成",
        "open_handoff_folder": "handoff フォルダを開く",
        "open_output_folder": "ログ/出力フォルダを開く",
        "stop_current_task": "現在のタスクを停止",
        "log": "ログ",
        "status_idle": "待機中",
        "status_cleaning": "MHTML を整理中……",
        "status_absorbing": "run を吸収中……",
        "status_handoff": "handoff を生成中……",
        "status_completed": "完了",
        "status_failed": "失敗しました。ログを確認してください",
        "status_stopping": "停止中……",
        "status_stopped": "停止済み",
        "choose_mhtml_title": "Grok の .mhtml ファイルを選択",
        "choose_project_title": "プロジェクトディレクトリを選択",
        "choose_run_title": "完了済み run ディレクトリを選択",
        "select_mhtml": ".mhtml ファイルを選択してください",
        "mhtml_missing": ".mhtml ファイルが存在しません",
        "select_project_dir": "プロジェクトディレクトリを選択してください",
        "select_run_dir": "run ディレクトリを選択または生成してください",
        "run_dir_missing": "run ディレクトリが存在しません",
        "task_running_title": "実行中",
        "task_running": "すでにタスクが実行中です。完了までお待ちください。",
        "task_completed_title": "タスク完了",
        "task_completed": "タスクが完了しました",
        "clean_success": "整理が完了しました。次は「完了済み run ディレクトリを吸収」をクリックしてください。",
        "absorb_success": "吸収が完了しました。次は「handoff パックを生成」をクリックしてから handoff フォルダを開いてください。",
        "handoff_success": "handoff が生成されました。handoff フォルダを開き、03_下个窗口直接复制这个.md を次の Grok ウィンドウにコピーできます。",
        "handoff_file_ready": "handoff ファイルの準備ができました：",
        "task_failed_title": "タスク失敗",
        "task_failed": "タスクが失敗しました。ログを確認してください",
        "task_stopped_title": "タスク停止",
        "task_stopped": "現在のタスクを停止しました。",
        "stop_requested": "ユーザーが現在のタスク停止を要求しました……",
        "stopping_process": "サブプロセスを停止しています……",
        "lm_studio_hint": "LM Studio が起動していない場合は http://127.0.0.1:1234/v1 を確認し、モデルが読み込まれているか確認してください。",
        "handoff_missing_title": "handoff フォルダが存在しません",
        "handoff_missing": "handoff フォルダはまだ存在しません。",
        "output_missing_title": "出力フォルダが見つかりません",
        "output_missing": "開けるログ/出力フォルダがまだありません。",
        "missing_info_title": "情報が不足しています",
        "path_missing_title": "パスが存在しません",
        "bad_format_title": "値が正しくありません",
        "canon_part_chars_invalid": "canon_part_chars は数字で入力してください",
    },
}


def get_supported_languages() -> Dict[str, str]:
    """Return supported language codes and display names."""
    return dict(SUPPORTED_LANGUAGES)


def normalize_language_code(raw: str) -> str:
    """Normalize OS/browser-style locale strings to one supported code."""
    value = (raw or "").strip()
    if not value:
        return DEFAULT_LANGUAGE

    value = value.split(":")[0].split(".")[0].replace("_", "-").strip()
    lower = value.lower()

    if lower.startswith("zh") or lower.startswith("chinese"):
        return "zh-CN"
    if lower.startswith("ja") or lower.startswith("japanese"):
        return "ja-JP"
    if lower.startswith("en") or lower.startswith("english"):
        return "en-US"
    return DEFAULT_LANGUAGE


def detect_system_language() -> str:
    """Detect system language without using deprecated getdefaultlocale()."""
    candidates = []

    try:
        locale.setlocale(locale.LC_ALL, "")
        loc = locale.getlocale()[0]
        if loc:
            candidates.append(loc)
    except Exception:
        pass

    for name in ("LC_ALL", "LANGUAGE", "LANG"):
        value = os.environ.get(name)
        if value:
            candidates.append(value)

    for candidate in candidates:
        value = (candidate or "").split(":")[0].split(".")[0].replace("_", "-").strip().lower()
        if value.startswith("zh") or value.startswith("chinese"):
            return "zh-CN"
        if value.startswith("ja") or value.startswith("japanese"):
            return "ja-JP"
        if value.startswith("en") or value.startswith("english"):
            return "en-US"

    return DEFAULT_LANGUAGE


def t(key: str, lang: str | None = None) -> str:
    """Translate a UI key, falling back to English and then the key itself."""
    global _CACHED_SYSTEM_LANGUAGE
    if lang is None:
        if _CACHED_SYSTEM_LANGUAGE is None:
            _CACHED_SYSTEM_LANGUAGE = detect_system_language()
        language = _CACHED_SYSTEM_LANGUAGE
    else:
        language = normalize_language_code(lang)
    return (
        TRANSLATIONS.get(language, {}).get(key)
        or TRANSLATIONS[DEFAULT_LANGUAGE].get(key)
        or key
    )
