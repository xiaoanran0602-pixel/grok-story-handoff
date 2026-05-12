# Automation Guide (English)

## Fully automated release
No local packaging is required:
1. Codex opens a PR.
2. Merge PR into main.
3. Open GitHub → Actions → Release Windows.
4. Click Run workflow.
5. Enter a version, for example v0.1.1.
6. GitHub Actions builds the Windows executable, zips it, creates a Release, and uploads the asset.

## Automated merge behavior
- If bot permissions allow it, Codex can open PRs, redo conflict resolution on a fresh branch, and try squash merge after checks pass.
- If permissions are limited, only a web click on **Merge pull request** is needed.
