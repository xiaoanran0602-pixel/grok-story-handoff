# Contributing

Thanks for helping improve Grok Story Handoff.

## Good bug reports

Please include:

- App version or commit hash.
- Windows version or Python version.
- Whether you used the packaged app or source code.
- The action you ran: append, rebuild, handoff only, CLI clean, or CLI absorb.
- The error message or relevant log excerpt.

## Remove private data first

Before posting issues, screenshots, or logs, remove:

- Story text and character names you do not want public.
- Local file paths that include personal names.
- API keys, tokens, and private model server URLs.
- Raw `.mhtml`, `master/`, `handoff/`, `runs/`, and `debug/` contents.

## Feature requests

A useful feature request explains:

1. What you were trying to do.
2. What got in the way.
3. What output or workflow would make the task easier.

## Development notes

Use Python 3.10+ and install dependencies from `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python grok_handoff_gui.py
```
