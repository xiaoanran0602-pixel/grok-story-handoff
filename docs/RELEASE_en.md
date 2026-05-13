# Release Workflow

This document may describe planned/internal details; for current usage, see README and USAGE.

This document only prepares the release workflow. It does not create a real GitHub Release.

## 1. Local Test

```powershell
cd D:\Grok
python grok_handoff_cli.py --help
python grok_handoff_gui.py
```

Check that:

- The GUI starts.
- The language dropdown works.
- The log box scrolls.
- The progress bar moves during long tasks.
- CLI help clearly says the input is a Grok conversation saved as `.mhtml`.

## 2. Build the EXE

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The script runs (default):

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --onedir --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
```

Recommended output:

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
```

`--onefile` is optional, but `--onedir` is recommended for debugging and release stability.

Optional onefile build:

```powershell
python -m PyInstaller --onefile --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
```

## 3. Check dist

Confirm this file exists:

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
```

Run it and make sure the GUI opens.

## 4. Zip the Release Package

Zip the whole folder:

```text
dist\GrokStoryHandoff
```

Suggested zip name:

```text
GrokStoryHandoff-windows-v0.1.0.zip
```

## 5. Create a GitHub Release

1. Open the GitHub repository.
2. Click `Releases`.
3. Click `Draft a new release`.
4. Tag: `v0.1.0`.
5. Title: `Grok Story Handoff v0.1.0`.
6. Upload `GrokStoryHandoff-windows-v0.1.0.zip`.
7. Suggested release notes:

```text
- First public preview
- Tkinter GUI
- CLI wrapper
- Grok .mhtml canon extraction
- Handoff pack generation
- Toast workshop docs
```

## 6. Privacy Check

Before publishing, make sure you did not upload:

- `.mhtml`
- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `story_canon.md`
- `clean_corpus.md`
- `removed_meta.md`
- `canon_index.jsonl`
- `grok_config.json`

These are ignored by `.gitignore`, but always inspect the zip and repository before publishing.

## Fully automated release
No local packaging is required:
1. Codex opens a PR.
2. Merge PR into main.
3. Open GitHub → Actions → Release Windows.
4. Click Run workflow.
5. Enter a version, for example v0.1.1.
6. GitHub Actions builds the Windows executable, zips it, creates a Release, and uploads the asset.

## Windows Actions UTF-8
Windows GitHub Actions may need UTF-8 mode because CLI help contains Chinese/Japanese text. If UnicodeEncodeError / cp1252 appears, workflow should set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.

