# Internationalization Notes

The GUI supports three interface languages:

- 中文
- 日本語
- English

## Automatic Language Selection

On startup, the GUI first reads the `language` field from `grok_config.json`.

If no config file exists, it tries to select the language from the system locale:

- Chinese system → `zh-CN`
- Japanese system → `ja-JP`
- Other systems → `en-US`

The detection logic lives in `grok_i18n.py`:

1. Try `locale.setlocale(locale.LC_ALL, "")`.
2. Read `locale.getlocale()[0]`.
3. If that fails or cannot be recognized, check `LC_ALL` / `LANGUAGE` / `LANG`.
4. If nothing can be recognized, fall back to `en-US`.

It does not use `locale.getdefaultlocale()`, because that API is deprecated after Python 3.11 and will be removed in the future.

## Manual Language Switching

The GUI has a top-right language dropdown:

- 中文
- 日本語
- English

Changing the dropdown refreshes the UI immediately. Restarting the program is not required.

Manual selection is saved to:

```text
grok_config.json
```

Example:

```json
{
  "language": "en-US"
}
```

`grok_config.json` is a local user preference file and is ignored by `.gitignore`.

## What Is Not Translated

The following content is intentionally not translated:

- User-entered file paths.
- Raw command lines in the log box.
- subprocess output.
- Model output.
- LM Studio / Python / operating system error messages.

Keeping raw output intact makes troubleshooting easier and avoids hiding important details.

## Current Implementation

The current implementation uses a lightweight in-code dictionary in:

```text
grok_i18n.py
```

Main functions:

- `detect_system_language() -> str`
- `normalize_language_code(raw: str) -> str`
- `t(key: str, lang: str | None = None) -> str`
- `get_supported_languages() -> dict`

If a translation key is missing, `t()` falls back to English. If English is also missing, it returns the key itself so the UI does not crash.

## Future Migration

If the amount of UI text and documentation translation grows, this can be migrated to Python's standard `gettext` workflow with `.po` / `.mo` files.
