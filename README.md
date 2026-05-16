# Grok Story Handoff

**Turn full Grok long-chat windows into a clean next-window handoff pack for continuous fiction writing.**

Grok Story Handoff is a local tool for long-form fiction workflows. Save a Grok chat as `.mhtml`, put it into one story folder, then generate:

- cleaned story canon
- current story bible
- recent context
- next-window handoff prompt

## 30-second workflow

1. Save your full Grok chat as `.mhtml`
2. Put it into one story folder
3. Open Grok Story Handoff GUI
4. Select the story folder and scan
5. Click append new Grok window
6. Copy `handoff/03_下个窗口直接复制这个.md` into the next Grok window

## Download

- Windows release: https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases
- Source code: this repository

## Creator Pack

Want a ready-to-run package + starter templates + beginner guide?

- Commercial launch checklist: [`docs/CREATOR_PACK_GO_TO_MARKET_zh.md`](docs/CREATOR_PACK_GO_TO_MARKET_zh.md)
- Store link placeholder: `TODO: add Gumroad / itch.io link`

中文说明： [README.zh-CN.md](README.zh-CN.md)

## Project Overview

This project is designed for long-form fiction workflows where one Grok window eventually fills up. Instead of pasting a huge conversation into the next window, you can:

1. Keep one story in one story folder.
2. Save each full Grok window as `.mhtml` and put it in that folder.
3. Let the app scan and detect the current story state.
4. Choose whether to append a new window, rebuild the story project, or regenerate handoff only.
5. Copy the generated handoff into the next Grok window.

Intermediate files are written to disk on purpose. Long-running local model tasks should not keep all intermediate results only in memory. v3.5 writes chunk extraction, section merges, and draft bible sections to `debug/init_bible_cache_v3_5/` and `debug/init_bible_sections_v3_5/`. If something fails, users can inspect or reuse partial outputs instead of starting over.


## Who is this for?

- Writers using Grok for long-form fiction, roleplay, character interaction, or worldbuilding.
- Users whose long Grok chats start forgetting details, mixing storylines, or losing character continuity.
- People who want to separate actual story text from chat noise, summaries, and meta comments.
- Anyone who wants a fresh Grok window to continue a story with better memory.

## Quick Start

Install Python 3.10+ if needed, then run:

```powershell
cd D:\Grok
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the GUI:

```powershell
python grok_handoff_gui.py
```

Or start it through the CLI:

```powershell
python grok_handoff_cli.py gui
```

Check CLI help:

```powershell
python grok_handoff_cli.py --help
```

## GUI Usage

Main GUI flow (Story Folder Wizard):

1. Choose a story folder.
2. Put saved Grok `.mhtml` files into that folder.
3. Let the app scan the folder and show what it found.
4. Choose one action: add a new Grok window, rebuild the story project, or regenerate the handoff pack.
5. Copy `handoff/03_下个窗口直接复制这个.md` into the next Grok window.

Advanced operations are still available for power users (`Clean one .mhtml only` and `Absorb one run only`), but they are no longer the primary workflow.

Default LM Studio Base URL:

```text
http://127.0.0.1:1234/v1
```

The model name can be left empty. In that case, the original scripts try to auto-select a model from the local OpenAI-compatible API.

### Multilingual UI

The GUI tries to select the language from your system locale:

- Chinese system → 中文
- Japanese system → 日本語
- Other systems → English

You can also switch language manually from the top-right dropdown. The selection is saved to `grok_config.json`.

The GUI text is translated, but model output, logs, and subprocess command output are kept exactly as they are.

### Stop button and encoding

- GUI now provides **Stop Current Task** for long runs.
- GUI subprocess execution enforces UTF-8 (`-X utf8`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`) to reduce mojibake in Chinese/Japanese logs.
- If your Windows environment still shows garbled text, check system/app locale and UTF-8 settings; most users should not need extra changes.
- Pause/Resume is **not** implemented yet. For now, stop and rerun. v3.5 already writes intermediate cache files, which can reduce rerun cost.

See [docs/I18N_en.md](docs/I18N_en.md) for implementation notes.

## GUI Screenshot Placeholder

Screenshot coming soon.

## Windows EXE Build

PyInstaller can bundle this Python GUI and its dependencies so end users can run it without installing Python.

Recommended build command:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The script runs:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --onedir --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
``` 

Recommended output:

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
``` 

Default build uses `--onedir` so the release package keeps a stable folder layout and is easier to debug.

`--onefile` is optional, but `--onedir` is recommended for debugging and release stability.

The GUI exe uses an internal subprocess handoff (`--run-script v6/manager`) so the packaged app can still run the original core modules without requiring users to install Python.

Optional onefile build:

```powershell
python -m PyInstaller --onefile --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
``` 

## GitHub Release

GitHub Releases are the right place to upload the Windows zip/exe and write release notes.

Suggested first release:

- Tag: `v0.1.0`
- Title: `Grok Story Handoff v0.1.0`
- Asset: `GrokStoryHandoff-windows-v0.1.0.zip`
- Notes: first public preview, Tkinter GUI, CLI wrapper, Grok `.mhtml` canon extraction, handoff pack generation, toast workshop docs.

Before publishing, verify that no private story data is included.

See [docs/RELEASE_en.md](docs/RELEASE_en.md).

## GitHub Pages

GitHub Pages can host a simple static project page with:

- One-line project intro.
- Download button linking to GitHub Releases.
- Toast workshop metaphor.
- Quick start.
- Privacy notes.
- Screenshots.

The draft page is [docs/index.md](docs/index.md). For now, the README is enough; no complex website is required.

See [docs/GITHUB_PAGES_en.md](docs/GITHUB_PAGES_en.md).

## CLI Usage

Clean MHTML:

```powershell
python grok_handoff_cli.py clean --input "D:\path\story.mhtml" --output "D:\Grok_Project\runs\story_run" --canon-part-chars 12000
```

Absorb a finished run:

```powershell
python grok_handoff_cli.py absorb-run --run-dir "D:\Grok_Project\runs\story_run" --project-dir "D:\Grok_Project"
```

Generate handoff:

```powershell
python grok_handoff_cli.py handoff --project-dir "D:\Grok_Project"
```

The original scripts can still be run directly.

## Toast Workshop Metaphor

Think of this tool as a “Grok Story Toaster”:

- `.mhtml` = raw dough, containing story text, chat noise, summaries, and meta comments.
- `story_canon_parts/` = sliced bread pieces.
- `story_canon.md` = the toasted canon loaf.
- `removed_meta.md` = burnt edges trimmed away.
- `master/` = the long-term bread cabinet.
- `handoff/` = the breakfast pack for the next Grok window.

Workflow:

```text
Save Grok window -> put it into the toaster -> slice and bake -> build the canon loaf -> pack the breakfast handoff -> feed it to the next Grok window.
```

## Recommended Hardware

These are practical experience notes, not benchmarks.

| Tier | Recommendation |
| --- | --- |
| Entry | 8GB VRAM, small models and small chunks only; slow. |
| Comfortable | 12-16GB VRAM, e.g. RTX 3060 12GB / 4070 Ti SUPER / 4080S, recommended `canon_part_chars=8000-12000`. |
| Recommended | 24GB VRAM, e.g. RTX 3090 / 4090 / 5090D V2 24GB, larger models and longer context. |
| Ideal | 32GB+ VRAM, e.g. RTX 5090 / 5090D 32GB, better for long-context and rich story bible generation. |
| Mac | 64GB/96GB/128GB unified memory is good for large models and long context, but may not be faster than high-end NVIDIA GPUs. |

## Model Recommendations

- This tool needs a local OpenAI-compatible API. LM Studio is recommended.
- Default LM Studio base URL is usually `http://127.0.0.1:1234/v1`.
- For canon extraction: use a stable, instruction-following, non-thinking instruct model.
- For rich story bible generation: use a long-context instruct model with reliable final answers.
- Strong thinking models are not recommended as the default summarizer because `reasoning_tokens` may consume the output budget.
- For NSFW / adult / sensitive fictional material, use a locally available model that can legally process your content; cloud models may refuse or rewrite it.
- Users are responsible for obeying local laws and platform policies.

Reference notes: LM Studio provides a local server and OpenAI-compatible endpoints; Python Tkinter is the standard Python interface to Tcl/Tk; PyInstaller can bundle Python apps into standalone executables; llama.cpp / llama-cpp-python style runtimes may error when requested tokens exceed the context window.

## Token & Chunk Size Guide

- Do not make `canon_part_chars` too large.
- `24000` chars per canon chunk may produce around 16K prompt tokens, which can be heavy for local 16GB GPUs.
- `12000` chars is safer; observed chunks are often around 7K-11K prompt tokens.
- You get more chunks, for example 12 chunks may become 24 chunks, but the failure rate is lower.
- Recommended default: `canon_part_chars = 12000`.
- Larger VRAM machines may try `16000-24000`.
- If you hit `n_keep >= n_ctx`, reduce `canon_part_chars`, `old_recent_chars`, `new_head_chars`, and `new_tail_chars` by about 30%.

Recommended parameters:

| Scenario | canon_part_chars | old_recent_chars | new_head_chars | new_tail_chars | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Low VRAM safe | 8000 | 8000 | 6000 | 8000 | Best first try on small GPUs. |
| 4080S recommended | 12000 | 10000 | 8000 | 10000 | Balanced default. |
| 24GB VRAM | 16000 | 14000 | 10000 | 14000 | Longer chunks if stable. |
| 32GB+ VRAM | 20000-24000 | 18000 | 12000 | 18000 | For long-context runs. |

If `n_keep >= n_ctx` appears, reduce these values by about 30%. If the result is too thin, do not simply increase a single prompt. Prefer the v3.5 section-by-section, chunked, checkpointed bible workflow.

Also, do not feed the full canon into every local model call:

- `story_canon.md` and master canon will grow over time.
- The full canon is for humans, not for every model call.
- Use:
  - Full canon = `master/01_当前正史正文.md`
  - Compressed bible = `master/02_当前设定状态.md`
  - Recent story = `handoff/02_最近正文_喂给Grok.md`
  - Final handoff = `handoff/03_下个窗口直接复制这个.md`

## Troubleshooting

See [docs/TROUBLESHOOTING_en.md](docs/TROUBLESHOOTING_en.md) for the full troubleshooting guide.

### `n_keep >= n_ctx`

Error example:

```text
HTTP 400: The number of tokens to keep from the initial prompt is greater than the context length
n_keep: 41859 >= n_ctx: 35072
```

Meaning: the prompt is larger than the loaded model context window.

Fixes:

- Reduce `canon_part_chars` / `old_recent_chars` / `new_head_chars` / `new_tail_chars`.
- Feed less bible/handoff text into each call.
- Increase Context Length in LM Studio and reload the model.
- Use more VRAM or a smaller model.

### Empty Model Response

Typical log:

```text
finish_reason: length
completion_tokens: 2000
reasoning_tokens: 1997
content: ""
```

Meaning:

- Some thinking models ignore `/no_think` and spend almost all output tokens on `reasoning_content`.
- The final answer content is empty, so the script reports “empty model response”.

Fixes:

- Increase `max_tokens`.
- Shorten the prompt to leave room for final output.
- Use a non-thinking instruct model.
- Avoid filling the context window too tightly.

### FAQ

**Q: Why can 24000 chars fail more often?**  
A: Characters are not tokens. Chinese, English, symbols, and system instructions all become tokens. With extraction rules added, a single prompt can easily exceed 15K tokens.

**Q: Why does the model “think” for a long time but output nothing?**  
A: Thinking models may spend completion tokens on `reasoning_content`, leaving final content empty. Increase `max_tokens`, shorten the prompt, or use a non-thinking model.

**Q: Why not feed the full story_canon.md to Grok?**  
A: If it is short, you can try. But long-running stories grow quickly. Prefer compressed bible + recent story + next direction.

**Q: Why is the generated story bible too thin?**  
A: One-shot summaries miss details. Use the v3.5 checkpoint/deep bible workflow: extract and merge events, characters, relationships, and world rules section by section.

**Q: Can it process NSFW content?**  
A: This tool only processes local user files. Use a locally available model that can legally process your content, and follow local laws and platform policies. Cloud APIs may refuse adult material.

## Privacy & Safety

Do not commit or publish private story data:

- `.mhtml`, `.mht`, `.html`
- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `mhtml_archive/`
- `story_canon.md`
- `clean_corpus.md`
- `removed_meta.md`
- `canon_index.jsonl`

The `.gitignore` excludes these by default, but always check before publishing.

## NSFW / Adult Content Note

This tool only processes local user files. If your project contains NSFW, adult, or sensitive fictional material, use a local model that is legal for you to use and appropriate for your content. Cloud APIs may refuse, filter, or rewrite adult material. You are responsible for local laws, platform rules, and consent/safety boundaries.

## License

MIT License. See [LICENSE](LICENSE).


## Fully automated release
No local packaging is required:
1. Codex opens a PR.
2. Merge PR into main.
3. Open GitHub → Actions → Release Windows.
4. Click Run workflow.
5. Enter a version, for example v0.1.1.
6. GitHub Actions builds the Windows executable, zips it, creates a Release, and uploads the asset.


## Feedback

Issues, logs, bug reports, and feature suggestions are welcome:
https://github.com/xiaoanran0602-pixel/grok-story-handoff/issues

Before posting logs, screenshots, or bug reports, remove private story text, local paths, API keys, tokens, and personal data.

Keywords: Grok, AI writing, long conversation cleanup, story canon, story bible, handoff pack, roleplay, worldbuilding, local AI, LM Studio, MHTML export.






