# Privacy & Safety

Grok Story Handoff is designed for local story-folder workflows, but privacy still depends on where you send the text for model processing.

## What stays local

The app reads files from the story folder you choose and writes output folders such as:

- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `mhtml_archive/`

These files may contain private story text.

## Model endpoint

The app sends text to the OpenAI-compatible endpoint you configure.

Default local URL:

```text
http://127.0.0.1:1234/v1
```

If you change the URL to a remote or cloud API, your story content may leave your machine. Check the provider's policies before using private, adult, sensitive, or unpublished writing.

## Do not commit private data

Do not publish:

- Raw `.mhtml`, `.mht`, `.html` exports.
- `runs/`, `master/`, `handoff/`, `debug/`, or `mhtml_archive/` folders.
- `story_canon.md`, `clean_corpus.md`, `removed_meta.md`, `canon_index.jsonl`.
- Logs that include story text, file paths, API keys, or personal data.

The repository `.gitignore` excludes these by default, but always check `git status` before committing.

## Safe bug reports

When opening an issue:

1. Describe what you were doing.
2. Include the error message.
3. Remove private story text.
4. Replace personal file paths with placeholders.
5. Never share API keys or tokens.

## Sensitive fictional material

Use a model and service that are legal and appropriate for your content. You are responsible for following local laws, platform rules, and consent/safety boundaries.
