# Release Checklist

Use this checklist before publishing a Windows build or a new public release.

## 1. Clean the repository

Check that no private story files are included:

```powershell
git status --short
```

Never release or commit:

- `.mhtml`, `.mht`, `.html` story exports.
- `runs/`, `master/`, `handoff/`, `debug/`, `mhtml_archive/`.
- Logs that include private story text.
- API keys, tokens, local private paths, or cloud credentials.

## 2. Build Windows package

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

Expected output:

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
```

The default `--onedir` package is recommended for stability.

## 3. Smoke test

Before uploading, test:

- App opens.
- Language selector works.
- Story folder can be selected.
- Local API URL can be set.
- A small safe test `.mhtml` can run through the workflow.
- `handoff/03_下个窗口直接复制这个.md` is generated.

## 4. Create release

Use a clear version tag, for example:

```text
v0.1.7
```

Suggested asset name:

```text
GrokStoryHandoff-windows-v0.1.7.zip
```

## 5. Release notes template

```md
## Grok Story Handoff v0.1.7

### Highlights
- Windows GUI for story-folder handoff workflow.
- Local OpenAI-compatible model endpoint support.
- Generates master story canon, story bible, recent context, and next-window handoff prompt.

### Privacy reminder
Do not upload private `.mhtml`, `master/`, `handoff/`, `runs/`, or `debug/` folders when reporting issues.
```
