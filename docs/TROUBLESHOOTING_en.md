# Troubleshooting

## The app cannot find a model

Check that your local OpenAI-compatible server is running and that the base URL is correct.

Default:

```text
http://127.0.0.1:1234/v1
```

If model auto-detection fails, enter the model name manually.

## `n_keep >= n_ctx` or context length error

The prompt is larger than the loaded model context window.

Try:

- Lowering `canon_part_chars`.
- Lowering `old_recent_chars`, `new_head_chars`, or `new_tail_chars`.
- Increasing Context Length in your model server and reloading the model.
- Using a model with a larger context window.

## Empty model response

This often happens when a model spends most of its output budget on hidden reasoning or stops because the output limit is too small.

Try:

- Increasing `max_tokens`.
- Shortening the prompt by lowering chunk sizes.
- Using a stable non-thinking instruct model.
- Avoiding overly full context windows.

## The output is too thin

Long stories are hard to summarize in one pass. Use the rebuild or checkpointed workflow so the app can process the story in sections.

Also try:

- A stronger instruction-following model.
- Slightly larger chunk sizes if your hardware can handle them.
- Regenerating the handoff after the story bible has been rebuilt.

## Text looks garbled on Windows

The GUI tries to enforce UTF-8 subprocess output. If you still see mojibake:

- Check Windows language and locale settings.
- Avoid non-UTF-8 terminals when running from source.
- Keep file paths simple while testing.

## Windows blocks the packaged app

Windows may warn about unsigned apps from independent developers.

Use the packaged app only if you downloaded it from the official GitHub Releases page, or run from source if you prefer to inspect the code first.

## The app finds no `.mhtml` file

Check:

- The file is inside the story folder you selected.
- The file extension is `.mhtml` or `.mht`.
- The file was fully saved by the browser.
- The story folder is not empty.

## A long run failed halfway

The app writes intermediate output on purpose. Check `debug/` and `runs/` before deleting anything. You may be able to rerun with smaller chunk sizes instead of starting from scratch.
