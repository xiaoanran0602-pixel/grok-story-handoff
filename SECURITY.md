# Security Policy

## Reporting security issues

Please do not publish security-sensitive details in a public issue. Open a minimal issue asking for a private contact path, or contact the repository owner through GitHub.

## Privacy-sensitive reports

This project often processes private fiction drafts, roleplay logs, and worldbuilding material. When reporting bugs, do not attach raw `.mhtml` files or generated story folders unless you are certain they are safe to share.

Remove or redact:

- Story text and private character details.
- Local usernames and file paths.
- API keys and tokens.
- Model server URLs that are not meant to be public.

## Local model endpoint warning

The app sends text to the OpenAI-compatible endpoint you configure. The default URL is local (`http://127.0.0.1:1234/v1`). If you change it to a remote or cloud endpoint, your story content may leave your machine.
