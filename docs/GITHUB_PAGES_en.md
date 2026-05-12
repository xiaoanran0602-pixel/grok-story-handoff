# GitHub Pages Notes

GitHub Pages can host a simple static project website. For the first release, the README may be enough.

## First Version Recommendation

The simplest setup:

- Use `README.md` as the repository landing page.
- Put downloadable builds in GitHub Releases.
- Keep a lightweight Pages draft.

Current draft page:

```text
docs/index.md
```

## Enabling GitHub Pages

In the GitHub repository:

1. Open `Settings`.
2. Go to `Pages`.
3. Source: `Deploy from a branch`.
4. Branch: `main`.
5. Folder: `/docs`.
6. Save.

Then `docs/index.md` can act as the project website homepage.

## Homepage Content

The homepage should include:

- One-line project intro.
- Download button linking to GitHub Releases.
- Toast workshop metaphor.
- Quick start.
- Privacy notes.
- Screenshots.

## Keep It Simple

Do not introduce a complex frontend framework for the first version. Static Markdown or simple HTML is enough.

If a richer website is needed later, you can add:

```text
website/index.html
```

For now, `docs/index.md` is enough.
