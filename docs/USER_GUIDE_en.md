# User Guide

Grok Story Handoff helps you continue long Grok fiction projects across multiple chat windows.

## Before you start

Prepare:

- One folder for one story.
- A saved Grok conversation file in `.mhtml` / `.mht` format.
- A local OpenAI-compatible model server if you want the AI cleanup and handoff steps to run locally.

Recommended default model server URL:

```text
http://127.0.0.1:1234/v1
```

## Step 1: Create a story folder

Create a folder such as:

```text
D:\Stories\MyNovel
```

Keep all saved Grok windows for that one story in this folder. Do not mix different stories in the same folder.

## Step 2: Save your Grok window

Open the Grok conversation you want to continue from, then save the full page as a single-file web archive if your browser supports it:

```text
story-window-001.mhtml
```

Place the saved file in your story folder.

## Step 3: Open the app

Run the packaged Windows app, or run from source:

```powershell
python grok_handoff_gui.py
```

Choose your story folder when prompted.

## Step 4: Choose an action

### Append New Grok Window

Use this for the normal continuation workflow. The app processes a new `.mhtml` file, updates the story project, and generates a fresh handoff pack.

### Rebuild Story Project

Use this when you want to rebuild the story folder from saved `.mhtml` files. This may overwrite existing `master/` and `handoff/` outputs.

### Regenerate Handoff Only

Use this when `master/` is already correct and you only want a new next-window handoff pack.

## Step 5: Continue in a new Grok window

After the run finishes, open:

```text
handoff/03_下个窗口直接复制这个.md
```

Copy the full content into a fresh Grok window and continue writing.

## Good story folder habits

- Keep one story per folder.
- Use clear file names such as `window-001.mhtml`, `window-002.mhtml`.
- Keep original `.mhtml` files until you are sure the outputs look right.
- Do not upload raw story folders publicly.
- Back up important story projects before rebuilding.

## What the app may create

| Folder | Meaning |
| --- | --- |
| `runs/` | Per-window processing output. |
| `master/` | Long-term story canon and story bible. |
| `handoff/` | Files prepared for the next Grok window. |
| `debug/` | Intermediate checkpoint files for long runs. |
| `mhtml_archive/` | Optional archive location for processed `.mhtml` files. |

## Tips for local models

- Start with moderate chunk sizes before trying large values.
- If the model returns empty output, use a non-thinking instruct model or increase output tokens.
- If the context window is too small, lower chunk sizes or increase model context length.
- For long stories, prefer a stable instruction-following model over a model that spends most of its output budget on reasoning.
