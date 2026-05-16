# Repository Structure

This repository keeps the public project simple: user-facing documentation at the top, source files in the root, and detailed guides in `docs/`.

## Root files

| Path | Purpose |
| --- | --- |
| `README.md` | Main English overview and quick start. |
| `README.zh-CN.md` | Chinese overview and quick start. |
| `grok_handoff_gui.py` | GUI entry point. |
| `grok_handoff_cli.py` | CLI entry point. |
| `grok_i18n.py` | UI translation strings. |
| `grok_mhtml_bible_pipeline_v6.py` | Grok `.mhtml` cleanup and canon extraction pipeline. |
| `grok_story_handoff_manager_v3_5_checkpoint_bible.py` | Story project manager and handoff generation logic. |
| `build_windows.ps1` | Windows packaging script. |
| `requirements.txt` | Python dependencies. |
| `.gitignore` | Excludes local config, private story files, and generated outputs. |

## Folders

| Path | Purpose |
| --- | --- |
| `.github/workflows/` | GitHub Actions workflows for release builds. |
| `docs/` | User guides, release checklist, privacy notes, troubleshooting. |
| `examples/` | Safe example config and folder notes. |
| `scripts/` | Helper scripts. |

## Private folders created by the app

These folders may appear inside a user story folder and should not be committed:

- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `mhtml_archive/`

The repository `.gitignore` excludes them by default.
