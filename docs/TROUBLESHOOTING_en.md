# Troubleshooting

This document may describe planned/internal details; for current usage, see README and USAGE.

This document collects common issues when using local models, LM Studio, and OpenAI-compatible APIs.

## 1. `n_keep >= n_ctx`

Error example:

```text
HTTP 400: The number of tokens to keep from the initial prompt is greater than the context length
n_keep: 41859 >= n_ctx: 35072
```

Meaning:

- The prompt is larger than the loaded model context window.
- Characters are not tokens. Chinese, English, symbols, system prompts, and extraction rules all become tokens.
- With `canon_part_chars=24000`, a single canon chunk may approach 16K prompt tokens. Extra rules and context can push the request over the limit.

Fixes:

- Reduce `canon_part_chars` / `old_recent_chars` / `new_head_chars` / `new_tail_chars`.
- First try reducing these values by about 30%.
- Feed less bible/handoff text into each call.
- Increase Context Length in LM Studio and reload the model.
- Use more VRAM or a smaller model.

Recommended first try:

```text
canon_part_chars = 12000
```

If it still fails:

```text
canon_part_chars = 8000
```

## 2. Empty Model Response

Typical log:

```text
finish_reason: length
completion_tokens: 2000
reasoning_tokens: 1997
content: ""
```

Meaning:

- Some thinking models ignore `/no_think` and spend almost all output tokens on `reasoning_content`.
- The final answer `content` is empty, so the script reports “empty model response”.

Fixes:

- Increase `max_tokens`.
- Shorten the prompt to leave room for final output.
- Use a non-thinking instruct model.
- Avoid filling the context window too tightly.

## 3. `finish_reason=length`

Meaning:

- The model hit the current output token limit.
- This does not necessarily mean the model is broken; it may simply have run out of output budget.

Fixes:

- Increase the output token limit.
- Shorten the input prompt.
- Reduce `canon_part_chars`.
- Use a non-thinking model that produces reliable final answers.

## 4. `reasoning_tokens` Consumed the Output

Symptoms:

- `reasoning_tokens` is very high.
- `content` is short or empty.
- The model appears to “think” for a long time but returns no useful final answer.

Fixes:

- Use a non-thinking instruct model.
- If supported, disable thinking in LM Studio or in the prompt.
- Shorten the input to leave output room.
- Do not fill the context window too tightly.

## 5. GUI Seems Frozen

Possible causes:

- The local model is still running and has not produced new logs yet.
- LM Studio is not running or no model is loaded.
- The model is stuck on an oversized prompt.
- The computer went to sleep or the GPU is occupied by another process.

What to do:

- Check the log box at the bottom of the GUI.
- Check LM Studio server status and model activity.
- Do not let the computer sleep during long runs.
- If the run stalls repeatedly, reduce `canon_part_chars`.

## 6. LM Studio Is Not Running

Typical errors:

```text
Connection refused
Failed to establish a new connection
```

Fixes:

- Open LM Studio.
- Load a model.
- Start the Local Server / OpenAI-compatible server.
- Confirm the Base URL:

```text
http://127.0.0.1:1234/v1
```

## 7. Wrong Model Name

Typical errors:

```text
model not found
404
```

Fixes:

- Leave the GUI model field empty and let the scripts auto-select.
- Or copy the exact model name from LM Studio.
- Watch capitalization, spaces, and special characters.

## 8. Python Is Not in PATH

Typical Windows error:

```text
python : The term 'python' is not recognized as the name of a cmdlet, function, script file, or operable program
```

Fixes:

- Install Python 3.10+.
- Enable `Add Python to PATH` during installation.
- Restart PowerShell.
- Try:

```powershell
python --version
```

## 9. Paths with Spaces

Quote paths that contain spaces:

```powershell
python grok_handoff_cli.py clean --input "D:\My Stories\story window.mhtml" --output "D:\Grok Project\runs\story_run" --canon-part-chars 12000
```

## 10. Do Not Let the Computer Sleep

Local model runs can take a long time. Sleep mode may cause:

- LM Studio interruption.
- GPU work stopping.
- Python subprocess hangs or failures.
- Incomplete intermediate outputs.

Suggestions:

- Keep the machine plugged in.
- Temporarily disable sleep.
- Check cooling and VRAM headroom before long runs.

## 11. Why Not Feed the Full story_canon.md

`story_canon.md` and master canon will grow over time. The full canon is for humans, not for every model call.

Use:

- Full canon = `master/01_当前正史正文.md`
- Compressed bible = `master/02_当前设定状态.md`
- Recent story = `handoff/02_最近正文_喂给Grok.md`
- Final handoff = `handoff/03_下个窗口直接复制这个.md`

## 12. NSFW / Adult Content

This tool only processes local user files. If your project contains NSFW, adult, or sensitive fictional material, use a locally available model that can legally process your content. Cloud APIs may refuse, filter, or rewrite adult material.

Users are responsible for local laws, platform policies, and consent/safety boundaries.

## 13. Garbled GUI Logs (Chinese/Japanese)

The GUI now forces UTF-8 for Python subprocess output and log decoding. If mojibake still appears:

- Restart GUI and LM Studio.
- Check Windows locale/encoding settings.
- Optionally enable Windows UTF-8 compatibility (Beta).

Most users should not need extra changes.

## 14. Stopping Long Tasks

- Use **Stop Current Task** while a task is running.
- GUI first tries graceful terminate, then force-kills if needed.
- After stopping, status becomes "Stopped" and it is treated as user stop (not task failure).
- True Pause/Resume is not implemented yet; rerun after stop.

## Windows Actions UTF-8
Windows GitHub Actions may need UTF-8 mode because CLI help contains Chinese/Japanese text. If UnicodeEncodeError / cp1252 appears, workflow should set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.


