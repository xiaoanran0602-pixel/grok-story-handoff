# Examples

This folder contains safe example files only. Do not place private story exports here.

## Example config

`config.example.json` shows a minimal local-model configuration:

```json
{
  "project_dir": "D:\\Stories\\MyNovel",
  "base_url": "http://127.0.0.1:1234/v1",
  "model": "",
  "canon_part_chars": 12000,
  "recent_chars": 9000
}
```

Copy it to your own private location before editing. Do not commit your real `grok_config.json`.

## Safe test story folder layout

```text
MyNovel/
  window-001.mhtml
  window-002.mhtml
```

After running the app, the story folder may contain:

```text
MyNovel/
  runs/
  master/
  handoff/
  debug/
```

Those generated folders may contain private story text and should not be committed.
