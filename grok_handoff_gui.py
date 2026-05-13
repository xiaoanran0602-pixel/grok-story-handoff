#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import END, filedialog, messagebox, ttk
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional

from grok_i18n import detect_system_language, get_supported_languages, normalize_language_code, t

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "grok_config.json"
V6_SCRIPT = ROOT / "grok_mhtml_bible_pipeline_v6.py"
HANDOFF_SCRIPT = ROOT / "grok_story_handoff_manager_v3_5_checkpoint_bible.py"
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
STOP_WAIT_SECONDS = 3.0


@dataclass
class StoryFolderState:
    folder: Path
    mhtml_files: List[Path]
    has_master: bool
    has_handoff: bool
    run_dirs: List[Path]
    latest_handoff_path: Optional[Path]
    likely_unprocessed_mhtml_files: List[Path]
    summary_text: str = ""


def safe_name(name: str, max_len: int = 90) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().strip(" .")
    return (name or "untitled")[:max_len]


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(config: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def open_path(path: Path) -> None:
    if hasattr(os, "startfile"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def script_command(script_key: str) -> List[str]:
    if is_frozen_app():
        return [sys.executable, "--run-script", script_key]
    if script_key == "v6":
        return [sys.executable, "-X", "utf8", str(V6_SCRIPT)]
    if script_key == "manager":
        return [sys.executable, "-X", "utf8", str(HANDOFF_SCRIPT)]
    raise ValueError(script_key)


def run_internal_script(script_key: str, argv: List[str]) -> int:
    sys.argv = [script_key] + argv
    if script_key == "v6":
        import grok_mhtml_bible_pipeline_v6 as script

        script.main()
        return 0
    if script_key == "manager":
        import grok_story_handoff_manager_v3_5_checkpoint_bible as script

        script.main()
        return 0
    raise ValueError(script_key)


def scan_story_folder(folder: Path, lang: str) -> StoryFolderState:
    mhtml_files = sorted([*folder.glob("*.mhtml"), *folder.glob("*.mht")], key=lambda p: p.stat().st_mtime, reverse=True)
    run_dirs = sorted([p for p in (folder / "runs").glob("*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True) if (folder / "runs").exists() else []
    has_master = (folder / "master" / "01_当前正史正文.md").exists() and (folder / "master" / "02_当前设定状态.md").exists()
    latest_handoff = folder / "handoff" / "03_下个窗口直接复制这个.md"
    has_handoff = latest_handoff.exists()

    processed_stems = {safe_name(p.stem, 140) for p in mhtml_files if (folder / "runs" / safe_name(p.stem, 140) / "story_canon.md").exists()}
    archive_names = {p.name for p in (folder / "mhtml_archive").glob("*.mht*")} if (folder / "mhtml_archive").exists() else set()
    likely_unprocessed = [p for p in mhtml_files if safe_name(p.stem, 140) not in processed_stems and p.name not in archive_names]

    state = StoryFolderState(folder, mhtml_files, has_master, has_handoff, run_dirs, latest_handoff if has_handoff else None, likely_unprocessed)
    state.summary_text = "\n".join(
        [
            t("scan_found", lang),
            f"- {len(mhtml_files)} {t('scan_mhtml_count', lang)}",
            f"- {t('scan_has_master', lang) if has_master else t('scan_no_master', lang)}",
            f"- {len([r for r in run_dirs if (r / 'story_canon.md').exists()])} {t('scan_run_count', lang)}",
            f"- {t('scan_has_handoff', lang) if has_handoff else t('scan_no_handoff', lang)}",
            f"- {len(likely_unprocessed)} {t('scan_unprocessed_count', lang)}",
        ]
    )
    return state


class GrokHandoffGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1040x820")
        self.minsize(960, 700)
        self.config_data = load_config()
        self.lang = normalize_language_code(self.config_data.get("language") or detect_system_language())
        self.supported_languages = get_supported_languages()
        self.language_name_to_code = {v: k for k, v in self.supported_languages.items()}
        self.output_queue: queue.Queue = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.current_process: Optional[subprocess.Popen[str]] = None
        self.stop_requested = False
        self.post_action: Optional[Callable[[], None]] = None

        self.story_folder_var = tk.StringVar(value=str(ROOT / "Grok_Project"))
        self.mhtml_var = tk.StringVar()
        self.run_dir_var = tk.StringVar()
        self.base_url_var = tk.StringVar(value=DEFAULT_BASE_URL)
        self.model_var = tk.StringVar(value="")
        self.canon_part_chars_var = tk.StringVar(value="12000")
        self.language_var = tk.StringVar(value=self.supported_languages.get(self.lang, "English"))
        self.status_var = tk.StringVar()
        self.status_key = "status_idle"
        self.current_task_status_key = "status_idle"
        self.story_state: Optional[StoryFolderState] = None

        self._build_ui()
        self.update_texts()
        self.after(100, self._drain_output_queue)

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        top = ttk.Frame(outer)
        top.pack(fill="x")
        self.title_label = ttk.Label(top, font=("TkDefaultFont", 16, "bold"))
        self.title_label.pack(side="left")
        self.language_combo = ttk.Combobox(top, textvariable=self.language_var, values=list(self.supported_languages.values()), state="readonly", width=12)
        self.language_combo.pack(side="right")
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_changed)
        self.language_label = ttk.Label(top)
        self.language_label.pack(side="right", padx=6)
        self.intro_label = ttk.Label(outer, justify="left", wraplength=930)
        self.intro_label.pack(fill="x", pady=(8, 10))

        sf = ttk.LabelFrame(outer)
        sf.pack(fill="x")
        sf.columnconfigure(1, weight=1)
        self.story_frame = sf
        self.story_folder_label = ttk.Label(sf)
        self.story_folder_label.grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(sf, textvariable=self.story_folder_var).grid(row=0, column=1, sticky="ew", padx=8)
        self.choose_story_button = ttk.Button(sf, command=self.choose_story_folder)
        self.choose_story_button.grid(row=0, column=2)

        self.summary_frame = ttk.LabelFrame(outer)
        self.summary_frame.pack(fill="x", pady=(10, 8))
        self.summary_label = ttk.Label(self.summary_frame, justify="left", wraplength=920)
        self.summary_label.pack(anchor="w", padx=8, pady=8)
        self.main_action_button = ttk.Button(self.summary_frame, command=self.run_recommended_action)
        self.main_action_button.pack(anchor="w", padx=8, pady=(0, 8))

        self.quick_actions = ttk.Frame(outer)
        self.quick_actions.pack(fill="x", pady=(0, 8))
        self.append_button = ttk.Button(self.quick_actions, command=self.append_new_window)
        self.rebuild_button = ttk.Button(self.quick_actions, command=self.rebuild_story)
        self.handoff_button = ttk.Button(self.quick_actions, command=self.generate_handoff_only)
        self.open_results_button = ttk.Button(self.quick_actions, command=self.open_results)
        for b in (self.append_button, self.rebuild_button, self.handoff_button, self.open_results_button):
            b.pack(side="left", padx=(0, 8))

        self.advanced = ttk.LabelFrame(outer)
        self.advanced.pack(fill="x", pady=(0, 8))
        a = self.advanced
        a.columnconfigure(1, weight=1)
        ttk.Label(a, text=".mhtml").grid(row=0, column=0, sticky="w")
        ttk.Entry(a, textvariable=self.mhtml_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(a, text="...", command=self.choose_mhtml).grid(row=0, column=2)
        ttk.Label(a, text="run").grid(row=1, column=0, sticky="w")
        ttk.Entry(a, textvariable=self.run_dir_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(a, text="...", command=self.choose_run_dir).grid(row=1, column=2)
        self.clean_button = ttk.Button(a, command=self.clean_current_mhtml)
        self.absorb_button = ttk.Button(a, command=self.absorb_run)
        self.test_button = ttk.Button(a, command=self.test_lm_studio_connection)
        self.stop_button = ttk.Button(a, command=self.stop_current_task, state="disabled")
        self.clean_button.grid(row=2, column=0, pady=6)
        self.absorb_button.grid(row=2, column=1, sticky="w", pady=6)
        self.test_button.grid(row=2, column=1, sticky="e", pady=6)
        self.stop_button.grid(row=2, column=2, pady=6)

        self.progress_frame = ttk.LabelFrame(outer)
        self.progress_frame.pack(fill="x")
        self.progressbar = ttk.Progressbar(self.progress_frame, mode="indeterminate")
        self.progressbar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(self.progress_frame, textvariable=self.status_var).pack(anchor="w", padx=8, pady=(0, 8))

        self.next_steps = ttk.LabelFrame(outer)
        self.next_steps.pack(fill="x", pady=(8, 8))
        self.next_steps_label = ttk.Label(self.next_steps, justify="left", wraplength=920)
        self.next_steps_label.pack(anchor="w", padx=8, pady=6)
        bf = ttk.Frame(self.next_steps)
        bf.pack(anchor="w", padx=8, pady=(0, 8))
        self.open_handoff_folder_button = ttk.Button(bf, command=self.open_handoff_folder)
        self.open_handoff_file_button = ttk.Button(bf, command=self.open_handoff_file)
        self.open_master_button = ttk.Button(bf, command=self.open_master_file)
        self.copy_handoff_button = ttk.Button(bf, command=self.copy_handoff)
        for b in (self.open_handoff_folder_button, self.open_handoff_file_button, self.open_master_button, self.copy_handoff_button):
            b.pack(side="left", padx=(0, 8))

        self.log_frame = ttk.LabelFrame(outer)
        self.log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(self.log_frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def choose_story_folder(self):
        path = filedialog.askdirectory(title=t("choose_story_folder", self.lang))
        if path:
            self.story_folder_var.set(path)
            self.scan_current_folder()

    def choose_mhtml(self):
        path = filedialog.askopenfilename(title=t("choose_mhtml_title", self.lang), filetypes=[("MHTML files", "*.mhtml *.mht")])
        if path:
            self.mhtml_var.set(path)
            self.run_dir_var.set(str(Path(self.story_folder_var.get()) / "runs" / safe_name(Path(path).stem, 140)))

    def choose_run_dir(self):
        path = filedialog.askdirectory(title=t("choose_run_title", self.lang))
        if path:
            self.run_dir_var.set(path)

    def scan_current_folder(self):
        folder = Path(self.story_folder_var.get().strip())
        if not folder.exists():
            return
        self.story_state = scan_story_folder(folder, self.lang)
        self.summary_label.configure(text=self.story_state.summary_text)
        self._refresh_main_action_label()

    def _refresh_main_action_label(self):
        s = self.story_state
        if not s:
            return
        if not s.has_master:
            key = "main_create_story"
        elif s.likely_unprocessed_mhtml_files:
            key = "main_add_window"
        else:
            key = "main_regen_handoff"
        self.main_action_key = key
        self.main_action_button.configure(text=t(key, self.lang))

    def run_recommended_action(self):
        if self.main_action_key == "main_create_story" or self.main_action_key == "main_add_window":
            self.append_new_window()
        else:
            self.generate_handoff_only()

    def append_new_window(self):
        if not self.story_state:
            self.scan_current_folder()
        if self.story_state and self.story_state.likely_unprocessed_mhtml_files:
            target = self.story_state.likely_unprocessed_mhtml_files[0]
        elif self.mhtml_var.get().strip():
            target = Path(self.mhtml_var.get().strip())
        else:
            self.choose_mhtml()
            if not self.mhtml_var.get().strip():
                return
            target = Path(self.mhtml_var.get().strip())
        self.mhtml_var.set(str(target))
        self.run_dir_var.set(str(Path(self.story_folder_var.get()) / "runs" / safe_name(target.stem, 140)))
        self.clean_current_mhtml(chain_absorb=True)

    def clean_current_mhtml(self, chain_absorb: bool = False):
        m = Path(self.mhtml_var.get().strip())
        p = Path(self.story_folder_var.get().strip())
        r = Path(self.run_dir_var.get().strip() or p / "runs" / safe_name(m.stem, 140))
        if not m.exists():
            return
        cmd = [
            *script_command("v6"),
            "--input",
            str(m),
            "--output",
            str(r),
            "--base-url",
            self._normalize_base_url(self.base_url_var.get()),
            "--canon-part-chars",
            self.canon_part_chars_var.get().strip() or "12000",
        ]
        self._append_model_arg(cmd)
        self.run_subprocess(cmd, "status_step1", post_action=(lambda: self.absorb_run(chain_handoff=True)) if chain_absorb else None)

    def absorb_run(self, chain_handoff: bool = False):
        p = Path(self.story_folder_var.get().strip())
        r = Path(self.run_dir_var.get().strip())
        if not r.exists():
            return
        cmd = [
            *script_command("manager"),
            "--run-dir",
            str(r),
            "--project-dir",
            str(p),
            "--base-url",
            self._normalize_base_url(self.base_url_var.get()),
            "--absorb",
        ]
        self._append_model_arg(cmd)
        self.run_subprocess(cmd, "status_step2", post_action=self.generate_handoff_only if chain_handoff else None)

    def generate_handoff_only(self):
        p = Path(self.story_folder_var.get().strip())
        cmd = [*script_command("manager"), "--project-dir", str(p), "--handoff"]
        self.run_subprocess(cmd, "status_step3", post_action=self._show_next_steps)

    def rebuild_story(self):
        if not messagebox.askyesno(t("confirm_rebuild_title", self.lang), t("confirm_rebuild", self.lang)):
            return
        self.append_new_window()

    def open_results(self):
        self.open_handoff_folder()
        self.open_handoff_file()
        self.open_master_file()

    def open_handoff_folder(self):
        d = Path(self.story_folder_var.get().strip()) / "handoff"
        if d.exists():
            open_path(d)
        else:
            messagebox.showwarning(t("handoff_missing_title", self.lang), t("handoff_missing", self.lang))

    def open_handoff_file(self):
        p = Path(self.story_folder_var.get().strip()) / "handoff" / "03_下个窗口直接复制这个.md"
        if p.exists():
            open_path(p)
        else:
            messagebox.showwarning(t("handoff_missing_title", self.lang), t("handoff_missing", self.lang))

    def open_master_file(self):
        p = Path(self.story_folder_var.get().strip()) / "master" / "01_当前正史正文.md"
        if p.exists():
            open_path(p)
        else:
            messagebox.showwarning(t("output_missing_title", self.lang), t("output_missing", self.lang))

    def copy_handoff(self):
        p = Path(self.story_folder_var.get().strip()) / "handoff" / "03_下个窗口直接复制这个.md"
        if not p.exists():
            return
        self.clipboard_clear()
        self.clipboard_append(p.read_text(encoding="utf-8"))
        self.update()
        messagebox.showinfo(t("task_completed_title", self.lang), t("copied_handoff", self.lang))

    def _show_next_steps(self):
        self.next_steps_label.configure(text=t("next_steps", self.lang))
        self.scan_current_folder()

    def _normalize_base_url(self, base_url: str) -> str:
        text = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
        return text if text.endswith("/v1") else text + "/v1"

    def _append_model_arg(self, cmd: List[str]):
        if self.model_var.get().strip():
            cmd.extend(["--model", self.model_var.get().strip()])

    def test_lm_studio_connection(self):
        cmd = [*script_command("manager"), "--test-lm", "--base-url", self._normalize_base_url(self.base_url_var.get())]
        self._append_model_arg(cmd)
        self.run_subprocess(cmd, "status_idle")

    def update_texts(self):
        self.title(t("app_title", self.lang))
        self.title_label.configure(text=t("main_title", self.lang))
        self.language_label.configure(text=t("language", self.lang))
        self.intro_label.configure(text=t("intro_wizard", self.lang))
        self.story_frame.configure(text=t("story_folder_section", self.lang))
        self.story_folder_label.configure(text=t("story_folder", self.lang))
        self.choose_story_button.configure(text=t("choose_story_folder_btn", self.lang))
        self.summary_frame.configure(text=t("scan_section", self.lang))
        self.append_button.configure(text=t("action_append", self.lang))
        self.rebuild_button.configure(text=t("action_rebuild", self.lang))
        self.handoff_button.configure(text=t("action_handoff_only", self.lang))
        self.open_results_button.configure(text=t("action_open_results", self.lang))
        self.advanced.configure(text=t("advanced_section", self.lang))
        self.clean_button.configure(text=t("clean_current_mhtml", self.lang))
        self.absorb_button.configure(text=t("absorb_run", self.lang))
        self.test_button.configure(text=t("test_lm_studio_connection", self.lang))
        self.stop_button.configure(text=t("stop_current_task", self.lang))
        self.progress_frame.configure(text=t("progress_section", self.lang))
        self.next_steps.configure(text=t("next_section", self.lang))
        self.next_steps_label.configure(text=t("next_steps_placeholder", self.lang))
        self.open_handoff_folder_button.configure(text=t("open_handoff_folder", self.lang))
        self.open_handoff_file_button.configure(text=t("open_handoff_file", self.lang))
        self.open_master_button.configure(text=t("open_master", self.lang))
        self.copy_handoff_button.configure(text=t("copy_handoff", self.lang))
        self.log_frame.configure(text=t("log", self.lang))
        self.status_var.set(t(self.status_key, self.lang))
        self.scan_current_folder()

    def on_language_changed(self, _event=None):
        self.lang = self.language_name_to_code.get(self.language_var.get(), "en-US")
        self.config_data["language"] = self.lang
        save_config(self.config_data)
        self.update_texts()

    def run_subprocess(self, cmd: List[str], status_key: str, post_action=None):
        if self.worker and self.worker.is_alive():
            return
        self.stop_requested = False
        self.post_action = post_action
        self.status_key = status_key
        self.status_var.set(t(status_key, self.lang))
        self._set_buttons_enabled(False)
        self.progressbar.start(12)
        self.log_text.insert(END, "\n$ " + " ".join(cmd) + "\n")
        self.worker = threading.Thread(target=self._worker_run, args=(cmd,), daemon=True)
        self.worker.start()

    def _worker_run(self, cmd: List[str]):
        try:
            p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
            self.current_process = p
            assert p.stdout
            for line in p.stdout:
                self.output_queue.put(line)
            code = p.wait()
            self.output_queue.put(("DONE", code))
        except Exception as e:
            self.output_queue.put(str(e) + "\n")
            self.output_queue.put(("DONE", 1))
        finally:
            self.current_process = None
            self.output_queue.put(("ENABLE", None))

    def _drain_output_queue(self):
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, tuple):
                if item[0] == "DONE":
                    self.progressbar.stop()
                    ok = item[1] == 0
                    follow_up = self.post_action if ok and not self.stop_requested else None
                    self.post_action = None

                    if follow_up:
                        follow_up()
                        if self.worker and self.worker.is_alive():
                            continue

                    if self.stop_requested:
                        self.status_key = "status_stopped"
                        self.stop_requested = False
                    else:
                        self.status_key = "status_completed" if ok else "status_failed"
                    self.status_var.set(t(self.status_key, self.lang))

                elif item[0] == "ENABLE":
                    if not (self.worker and self.worker.is_alive()):
                        self._set_buttons_enabled(True)
            else:
                self.log_text.insert(END, item)
                self.log_text.see(END)

        self.after(100, self._drain_output_queue)

    def _set_buttons_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for b in (self.main_action_button, self.append_button, self.rebuild_button, self.handoff_button, self.open_results_button, self.clean_button, self.absorb_button, self.test_button):
            b.configure(state=state)
        self.stop_button.configure(state="disabled" if enabled else "normal")

    def _terminate_process_tree(self, proc: subprocess.Popen[str]) -> None:
        if proc.poll() is not None:
            return

        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return

        try:
            proc.terminate()
            proc.wait(timeout=STOP_WAIT_SECONDS)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def stop_current_task(self):
        proc = self.current_process
        if not proc or proc.poll() is not None:
            return

        self.stop_requested = True
        self.post_action = None
        self.log_text.insert(END, "\n[INFO] stopping current task...\n")
        self.log_text.see(END)
        self._terminate_process_tree(proc)
        self.current_process = None
        self.progressbar.stop()
        self.status_key = "status_stopped"
        self.status_var.set(t(self.status_key, self.lang))
        self._set_buttons_enabled(True)

    def on_close(self):
        proc = self.current_process
        running = bool(proc and proc.poll() is None)
        if running:
            if not messagebox.askyesno(t("confirm_close_running_title", self.lang), t("confirm_close_running", self.lang)):
                return
            self.stop_current_task()
            time.sleep(0.1)
        self.destroy()


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":
        raise SystemExit(run_internal_script(sys.argv[2], sys.argv[3:]))
    app = GrokHandoffGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
