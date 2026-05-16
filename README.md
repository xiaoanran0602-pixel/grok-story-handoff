# Grok Story Handoff

**Keep long Grok fiction projects continuous when one chat window fills up.**

Grok Story Handoff is a local tool for writers using Grok for long-form fiction, roleplay, character interaction, and worldbuilding. Save a completed Grok conversation as `.mhtml`, place it in one story folder, and generate a compact handoff pack for the next Grok window.

[Download Windows Release](https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases) · [中文说明](README.zh-CN.md) · [User Guide](docs/USER_GUIDE_en.md) · [Troubleshooting](docs/TROUBLESHOOTING_en.md)

> This is an independent tool and is not affiliated with xAI or Grok.

## What it does

Long fiction chats eventually become too large to continue comfortably. This tool turns saved Grok windows into a reusable story project:

- **Cleaned story canon** — the actual story text separated from chat noise.
- **Current story bible** — characters, relationships, setting, rules, and unresolved plot threads.
- **Recent context** — the latest story material that matters for continuity.
- **Next-window handoff prompt** — a ready-to-copy prompt for continuing in a fresh Grok window.

## 30-second workflow

1. Create one folder for one story.
2. Save a completed Grok chat as `.mhtml` / `.mht`.
3. Put the saved file into the story folder.
4. Open Grok Story Handoff and choose that folder.
5. Run **Append New Grok Window**.
6. Copy `handoff/03_下个窗口直接复制这个.md` into the next Grok window.

Use the same story folder for the same story. Use a different folder for a different story.

## Download

Windows users can download the latest packaged build from:

**https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases**

The packaged app is intended for users who do not want to install Python manually.

## Run from source

Requirements:

- Python 3.10+
- A local OpenAI-compatible model server, such as LM Studio
- A saved Grok conversation file in `.mhtml` / `.mht` format

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python grok_handoff_gui.py
```

CLI entry point:

```powershell
python grok_handoff_cli.py --help
```

Default local API URL:

```text
http://127.0.0.1:1234/v1
```

The model field can be left empty if you want the app to try auto-detection from your local OpenAI-compatible API.

## Main actions

| Action | Use it when |
| --- | --- |
| **Append New Grok Window** | You finished another Grok window and want to continue the same story. |
| **Rebuild Story Project** | You want to rebuild the story folder from saved `.mhtml` files. |
| **Regenerate Handoff Only** | The story project is already built and you only want a fresh handoff pack. |

Power users can also run the original cleanup and absorb steps through the CLI.

## Output folders

| Path | Purpose |
| --- | --- |
| `master/01_当前正史正文.md` | Long-term cleaned story canon. |
| `master/02_当前设定状态.md` | Current story bible and state. |
| `handoff/02_最近正文_喂给Grok.md` | Recent story material for continuity. |
| `handoff/03_下个窗口直接复制这个.md` | Final prompt to copy into the next Grok window. |
| `runs/` | Per-window processing output. |
| `debug/` | Intermediate checkpoint files for long local-model runs. |

## Privacy

The app works with files in your local story folder. Your story text is sent to the model endpoint you configure. If you use the default local URL, that endpoint is local; if you configure a cloud API, your data may be sent to that provider.

Do not publish private story data. The repository `.gitignore` excludes common story files and generated folders by default, including `.mhtml`, `runs/`, `master/`, `handoff/`, and `debug/`. Always check before committing or uploading logs.

See [Privacy & Safety](docs/PRIVACY_AND_SAFETY.md).

## Documentation

- [User Guide](docs/USER_GUIDE_en.md)
- [中文使用指南](docs/USER_GUIDE_zh-CN.md)
- [Troubleshooting](docs/TROUBLESHOOTING_en.md)
- [Release Checklist](docs/RELEASE_en.md)
- [Repository Structure](REPOSITORY_STRUCTURE.md)

## License

MIT License. See [LICENSE](LICENSE).
