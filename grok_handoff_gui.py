#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tkinter GUI shell for the Grok story handoff helper.

The GUI does not reimplement the v6/v3.5 business logic. It only collects a
few paths/options and runs the existing scripts in subprocesses.
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
from pathlib import Path
from tkinter import END, filedialog, messagebox, ttk
import tkinter as tk
from typing import Any, Dict, List, Optional

from grok_i18n import detect_system_language, get_supported_languages, normalize_language_code, t


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "grok_config.json"
V6_SCRIPT = ROOT / "grok_mhtml_bible_pipeline_v6.py"
HANDOFF_SCRIPT = ROOT / "grok_story_handoff_manager_v3_5_checkpoint_bible.py"
DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"


def safe_name(name: str, max_len: int = 90) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(" .")
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
        return
    if sys.platform == "darwin":
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
    raise ValueError(f"Unknown script key: {script_key}")


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
    raise ValueError(f"Unknown script key: {script_key}")


class GrokHandoffGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.geometry("1020x760")
        self.minsize(920, 660)

        self.config_data = load_config()
        self.lang = normalize_language_code(self.config_data.get("language") or detect_system_language())
        self.supported_languages = get_supported_languages()
        self.language_name_to_code = {name: code for code, name in self.supported_languages.items()}

        self.output_queue: queue.Queue = queue.Queue()
        self.worker: Optional[threading.Thread] = None
        self.current_process: Optional[subprocess.Popen] = None
        self.stop_requested = False

        self.mhtml_var = tk.StringVar()
        self.project_dir_var = tk.StringVar(value=str(ROOT / "Grok_Project"))
        self.run_dir_var = tk.StringVar()
        self.base_url_var = tk.StringVar(value=DEFAULT_BASE_URL)
        self.model_var = tk.StringVar(value="")
        self.canon_part_chars_var = tk.StringVar(value="12000")
        self.language_var = tk.StringVar(value=self.supported_languages.get(self.lang, "English"))
        self.status_var = tk.StringVar()
        self.status_key = "status_idle"
        self.current_task_status_key = "status_idle"

        self._build_ui()
        self._refresh_run_dir()
        self.update_texts()
        self.after(100, self._drain_output_queue)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(header, font=("TkDefaultFont", 16, "bold"))
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.intro_label = ttk.Label(header, justify="left", wraplength=760)
        self.intro_label.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        language_box = ttk.Frame(header)
        language_box.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(16, 0))
        self.language_label = ttk.Label(language_box)
        self.language_label.pack(anchor="e")
        self.language_combo = ttk.Combobox(
            language_box,
            textvariable=self.language_var,
            values=list(self.supported_languages.values()),
            state="readonly",
            width=14,
        )
        self.language_combo.pack(anchor="e", pady=(4, 0))
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_changed)

        self.input_frame = ttk.LabelFrame(outer)
        form = self.input_frame
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.mhtml_label, self.mhtml_browse_button = self._path_row(
            form, 0, self.mhtml_var, self.choose_mhtml, refresh_run_dir=True
        )
        self.project_dir_label, self.project_dir_browse_button = self._path_row(
            form, 1, self.project_dir_var, self.choose_project_dir, refresh_run_dir=True
        )
        self.run_dir_label, self.run_dir_browse_button = self._path_row(
            form, 2, self.run_dir_var, self.choose_run_dir
        )

        self.base_url_label = self._entry_row(form, 3, self.base_url_var)
        self.model_label, self.model_hint_label = self._entry_row(form, 4, self.model_var, with_hint=True)
        self.canon_part_chars_label = self._entry_row(form, 5, self.canon_part_chars_var)

        self.actions_frame = ttk.LabelFrame(outer)
        buttons = self.actions_frame
        buttons.pack(fill="x", pady=(12, 10))

        self.clean_button = ttk.Button(buttons, command=self.clean_current_mhtml)
        self.absorb_button = ttk.Button(buttons, command=self.absorb_run)
        self.handoff_button = ttk.Button(buttons, command=self.generate_handoff)
        self.open_handoff_button = ttk.Button(buttons, command=self.open_handoff_folder)
        self.open_output_button = ttk.Button(buttons, command=self.open_output_dir)
        self.test_connection_button = ttk.Button(buttons, command=self.test_lm_studio_connection)
        self.stop_button = ttk.Button(buttons, command=self.stop_current_task, state="disabled")

        self.clean_button.pack(side="left", padx=(0, 8), pady=4)
        self.absorb_button.pack(side="left", padx=(0, 8), pady=4)
        self.handoff_button.pack(side="left", padx=(0, 8), pady=4)
        self.open_handoff_button.pack(side="left", padx=(0, 8), pady=4)
        self.open_output_button.pack(side="left", padx=(0, 8), pady=4)
        self.test_connection_button.pack(side="left", padx=(0, 8), pady=4)
        self.stop_button.pack(side="left", padx=(0, 8), pady=4)

        self.progress_frame = ttk.LabelFrame(outer)
        self.progress_frame.pack(fill="x", pady=(0, 10))
        self.progress_frame.columnconfigure(0, weight=1)

        self.progressbar = ttk.Progressbar(self.progress_frame, mode="indeterminate")
        self.progressbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.status_label = ttk.Label(self.progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))

        self.log_frame = ttk.LabelFrame(outer)
        self.log_frame.pack(fill="both", expand=True)
        self.log_frame.rowconfigure(0, weight=1)
        self.log_frame.columnconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_frame, wrap="word", height=24)
        scrollbar = ttk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        variable: tk.StringVar,
        command,
        refresh_run_dir: bool = False,
    ) -> tuple[ttk.Label, ttk.Button]:
        label = ttk.Label(parent)
        label.grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=8, pady=5)
        button = ttk.Button(parent, command=command)
        button.grid(row=row, column=2, pady=5)
        if refresh_run_dir:
            variable.trace_add("write", lambda *_: self._refresh_run_dir())
        return label, button

    def _entry_row(
        self,
        parent: ttk.Frame,
        row: int,
        variable: tk.StringVar,
        with_hint: bool = False,
    ):
        label = ttk.Label(parent)
        label.grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=5)
        if with_hint:
            hint = ttk.Label(parent)
            hint.grid(row=row, column=2, sticky="w", pady=5)
            return label, hint
        return label

    def update_texts(self) -> None:
        self.title(t("app_title", self.lang))
        self.title_label.configure(text=t("main_title", self.lang))
        self.intro_label.configure(text=t("intro", self.lang))
        self.language_label.configure(text=t("language", self.lang))
        self.input_frame.configure(text=t("input_section", self.lang))
        self.actions_frame.configure(text=t("actions_section", self.lang))
        self.progress_frame.configure(text=t("progress_section", self.lang))

        self.mhtml_label.configure(text=t("mhtml_file", self.lang))
        self.project_dir_label.configure(text=t("project_dir", self.lang))
        self.run_dir_label.configure(text=t("run_dir", self.lang))
        self.base_url_label.configure(text=t("base_url", self.lang))
        self.model_label.configure(text=t("model_name", self.lang))
        self.model_hint_label.configure(text=t("model_hint", self.lang))
        self.canon_part_chars_label.configure(text=t("canon_part_chars", self.lang))

        for button in (self.mhtml_browse_button, self.project_dir_browse_button, self.run_dir_browse_button):
            button.configure(text=t("browse", self.lang))

        self.clean_button.configure(text=t("clean_current_mhtml", self.lang))
        self.absorb_button.configure(text=t("absorb_run", self.lang))
        self.handoff_button.configure(text=t("generate_handoff", self.lang))
        self.open_handoff_button.configure(text=t("open_handoff_folder", self.lang))
        self.open_output_button.configure(text=t("open_output_folder", self.lang))
        self.test_connection_button.configure(text=t("test_lm_studio_connection", self.lang))
        self.stop_button.configure(text=t("stop_current_task", self.lang))
        self.log_frame.configure(text=t("log", self.lang))

        self.status_var.set(t(self.status_key, self.lang))

    def on_language_changed(self, _event=None) -> None:
        selected = self.language_var.get()
        self.lang = self.language_name_to_code.get(selected, "en-US")
        self.config_data["language"] = self.lang
        save_config(self.config_data)
        self.update_texts()

    def choose_mhtml(self) -> None:
        path = filedialog.askopenfilename(
            title=t("choose_mhtml_title", self.lang),
            filetypes=[("MHTML files", "*.mhtml *.mht *.mhtm"), ("All files", "*.*")],
        )
        if path:
            self.mhtml_var.set(path)

    def choose_project_dir(self) -> None:
        path = filedialog.askdirectory(title=t("choose_project_title", self.lang))
        if path:
            self.project_dir_var.set(path)

    def choose_run_dir(self) -> None:
        path = filedialog.askdirectory(title=t("choose_run_title", self.lang))
        if path:
            self.run_dir_var.set(path)

    def _refresh_run_dir(self) -> None:
        mhtml = self.mhtml_var.get().strip()
        project_dir = self.project_dir_var.get().strip()
        if not mhtml or not project_dir:
            return
        stem = safe_name(Path(mhtml).stem, max_len=140)
        self.run_dir_var.set(str(Path(project_dir) / "runs" / stem))

    def clean_current_mhtml(self) -> None:
        mhtml = self._require_path(self.mhtml_var.get(), "select_mhtml", "mhtml_missing")
        project_dir = self._require_text(self.project_dir_var.get(), "select_project_dir")
        run_dir = self._require_text(self.run_dir_var.get(), "select_run_dir")
        canon_part_chars = self._require_int(self.canon_part_chars_var.get(), "canon_part_chars_invalid")
        if not mhtml or not project_dir or not run_dir or canon_part_chars is None:
            return

        cmd = [
            *script_command("v6"),
            "--input",
            str(mhtml),
            "--output",
            run_dir,
            "--base-url",
            self._normalize_base_url(self.base_url_var.get().strip() or DEFAULT_BASE_URL),
            "--canon-part-chars",
            str(canon_part_chars),
        ]
        self._append_model_arg(cmd)
        self.run_subprocess(cmd, "status_cleaning")

    def absorb_run(self) -> None:
        run_dir = self._require_path(self.run_dir_var.get(), "select_run_dir", "run_dir_missing")
        project_dir = self._require_text(self.project_dir_var.get(), "select_project_dir")
        if not run_dir or not project_dir:
            return

        cmd = [
            *script_command("manager"),
            "--run-dir",
            str(run_dir),
            "--project-dir",
            str(project_dir),
            "--base-url",
            self._normalize_base_url(self.base_url_var.get().strip() or DEFAULT_BASE_URL),
            "--absorb",
        ]
        self._append_model_arg(cmd)
        self.run_subprocess(cmd, "status_absorbing")

    def generate_handoff(self) -> None:
        project_dir = self._require_text(self.project_dir_var.get(), "select_project_dir")
        if not project_dir:
            return

        cmd = [
            *script_command("manager"),
            "--project-dir",
            str(project_dir),
            "--handoff",
        ]
        self.run_subprocess(cmd, "status_handoff")

    def open_handoff_folder(self) -> None:
        handoff_dir = Path(self.project_dir_var.get().strip()) / "handoff"
        if not handoff_dir.exists():
            messagebox.showwarning(t("handoff_missing_title", self.lang), t("handoff_missing", self.lang))
            return
        open_path(handoff_dir)

    def open_output_dir(self) -> None:
        candidates = [
            Path(self.run_dir_var.get().strip()),
            Path(self.project_dir_var.get().strip()),
            ROOT,
        ]
        for path in candidates:
            if path.exists():
                open_path(path)
                return
        messagebox.showwarning(t("output_missing_title", self.lang), t("output_missing", self.lang))



    def _normalize_base_url(self, base_url: str) -> str:
        text = (base_url or DEFAULT_BASE_URL).strip().rstrip('/')
        if text.endswith('/v1'):
            return text
        return text + '/v1'

    def _models_url(self, base_url: str) -> str:
        return self._normalize_base_url(base_url).rstrip('/') + '/models'

    def test_lm_studio_connection(self) -> None:
        try:
            import urllib.request
            url = self._models_url(self.base_url_var.get().strip() or DEFAULT_BASE_URL)
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f'HTTP {resp.status}')
            messagebox.showinfo(t('task_completed_title', self.lang), t('lm_test_ok', self.lang) + f"\n{url}")
            self.log_text.insert(END, f"[LM Studio] {t('lm_test_ok', self.lang)}: {url}\n")
        except Exception as exc:
            messagebox.showwarning(t('task_failed_title', self.lang), t('lm_test_fail', self.lang) + f"\n{exc}")
            self.log_text.insert(END, f"[LM Studio] {t('lm_test_fail', self.lang)}: {exc}\n")
            self.log_text.insert(END, t('lm_studio_hint', self.lang) + "\n")
        self.log_text.see(END)
    def _append_model_arg(self, cmd: List[str]) -> None:
        model = self.model_var.get().strip()
        if model:
            cmd.extend(["--model", model])

    def _require_text(self, value: str, message_key: str) -> Optional[str]:
        value = value.strip()
        if not value:
            messagebox.showwarning(t("missing_info_title", self.lang), t(message_key, self.lang))
            return None
        return value

    def _require_path(self, value: str, missing_key: str, path_missing_key: str) -> Optional[Path]:
        text = self._require_text(value, missing_key)
        if text is None:
            return None
        path = Path(text)
        if not path.exists():
            messagebox.showwarning(t("path_missing_title", self.lang), f"{t(path_missing_key, self.lang)}\n\n{path}")
            return None
        return path

    def _require_int(self, value: str, message_key: str) -> Optional[int]:
        try:
            return int(value)
        except ValueError:
            messagebox.showwarning(t("bad_format_title", self.lang), t(message_key, self.lang))
            return None

    def run_subprocess(self, cmd: List[str], status_key: str) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(t("task_running_title", self.lang), t("task_running", self.lang))
            return

        self.status_key = status_key
        self.current_task_status_key = status_key
        self.stop_requested = False
        self.status_var.set(t(self.status_key, self.lang))
        self._set_buttons_enabled(False)
        self.progressbar.start(12)
        self.log_text.insert(END, "\n$ " + " ".join(f'"{x}"' if " " in x else x for x in cmd) + "\n")
        self.log_text.insert(END, t("lm_studio_hint", self.lang) + "\n")
        self.log_text.see(END)

        self.worker = threading.Thread(target=self._worker_run, args=(cmd,), daemon=True)
        self.worker.start()

    def _worker_run(self, cmd: List[str]) -> None:
        try:
            child_env = os.environ.copy()
            child_env["PYTHONUTF8"] = "1"
            child_env["PYTHONIOENCODING"] = "utf-8"
            self.current_process = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=child_env,
            )
            assert self.current_process.stdout is not None
            for line in self.current_process.stdout:
                self.output_queue.put(line)
            code = self.current_process.wait()
            self.output_queue.put(f"\n[process exited with code {code}]\n")
            self.output_queue.put(("DONE", code))
        except Exception as exc:
            self.output_queue.put(f"\n[GUI error] {exc}\n")
            self.output_queue.put(("DONE", 1))
        finally:
            self.current_process = None
            self.output_queue.put(("ENABLE_BUTTONS", None))

    def _drain_output_queue(self) -> None:
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, tuple):
                event, value = item
                if event == "ENABLE_BUTTONS":
                    self._set_buttons_enabled(True)
                    self.progressbar.stop()
                elif event == "DONE":
                    self.progressbar.stop()
                    if self.stop_requested:
                        self.status_key = "status_stopped"
                        self.status_var.set(t(self.status_key, self.lang))
                        self.log_text.insert(END, t("task_stopped", self.lang) + "\n")
                        self.log_text.see(END)
                        messagebox.showinfo(t("task_stopped_title", self.lang), t("task_stopped", self.lang))
                    elif value == 0:
                        self.status_key = "status_completed"
                        self.status_var.set(t(self.status_key, self.lang))
                        success_message = self._success_message_for_current_task()
                        self.log_text.insert(END, success_message + "\n")
                        self.log_text.see(END)
                        messagebox.showinfo(t("task_completed_title", self.lang), success_message)
                    else:
                        self.status_key = "status_failed"
                        self.status_var.set(t(self.status_key, self.lang))
                        self.log_text.insert(END, t("lm_studio_hint", self.lang) + "\n")
                        self.log_text.see(END)
                        messagebox.showerror(t("task_failed_title", self.lang), t("task_failed", self.lang))
                continue

            self.log_text.insert(END, item)
            self.log_text.see(END)
        self.after(100, self._drain_output_queue)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in (
            self.clean_button,
            self.absorb_button,
            self.handoff_button,
            self.open_handoff_button,
            self.open_output_button,
            self.test_connection_button,
        ):
            button.configure(state=state)
        self.stop_button.configure(state="disabled" if enabled else "normal")

    def stop_current_task(self) -> None:
        if not self.current_process or self.current_process.poll() is not None or self.stop_requested:
            return
        self.stop_requested = True
        self.status_key = "status_stopping"
        self.status_var.set(t(self.status_key, self.lang))
        self.log_text.insert(END, t("stop_requested", self.lang) + "\n")
        self.log_text.insert(END, t("stopping_process", self.lang) + "\n")
        self.log_text.see(END)
        threading.Thread(target=self._stop_worker_process, daemon=True).start()

    def _stop_worker_process(self) -> None:
        proc = self.current_process
        if proc is None:
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], check=False, capture_output=True)
            else:
                proc.terminate()
            deadline = time.time() + 3
            while time.time() < deadline:
                if proc.poll() is not None:
                    return
                time.sleep(0.1)
            proc.kill()
        except Exception as exc:
            self.output_queue.put(f"\n[GUI stop error] {exc}\n")

    def _success_message_for_current_task(self) -> str:
        handoff_file = Path(self.project_dir_var.get().strip()) / "handoff" / "03_下个窗口直接复制这个.md"
        if self.current_task_status_key == "status_cleaning":
            return t("clean_success", self.lang)
        if self.current_task_status_key == "status_absorbing":
            message = t("absorb_success", self.lang)
            if handoff_file.exists():
                message += f"\n{t('handoff_file_ready', self.lang)} {handoff_file}"
            return message
        if self.current_task_status_key == "status_handoff":
            message = t("handoff_success", self.lang)
            if handoff_file.exists():
                message += f"\n{t('handoff_file_ready', self.lang)} {handoff_file}"
            return message
        return t("task_completed", self.lang)




    def on_close(self) -> None:
        if self.current_process and self.current_process.poll() is None and not self.stop_requested:
            if not messagebox.askyesno(t('task_running_title', self.lang), t('confirm_stop_on_close', self.lang)):
                return
            self.stop_current_task()
        self.destroy()
def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":
        raise SystemExit(run_internal_script(sys.argv[2], sys.argv[3:]))
    app = GrokHandoffGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
