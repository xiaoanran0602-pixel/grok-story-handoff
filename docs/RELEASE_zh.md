# 发布检查清单

发布 Windows 打包版或新版本前，用这个清单检查一遍。

## 1. 清理仓库

确认没有私人故事文件：

```powershell
git status --short
```

不要提交或发布：

- `.mhtml`、`.mht`、`.html` 故事导出文件。
- `runs/`、`master/`、`handoff/`、`debug/`、`mhtml_archive/`。
- 包含私人故事文本的日志。
- API key、token、本地私人路径、云端凭据。

## 2. 构建 Windows 包

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

预期输出：

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
```

默认推荐 `--onedir`，稳定性更好。

## 3. 冒烟测试

上传前至少测试：

- 软件可以打开。
- 语言选择可用。
- 可以选择故事目录。
- 可以设置本地 API URL。
- 一个安全的小型测试 `.mhtml` 可以跑完整流程。
- 能生成 `handoff/03_下个窗口直接复制这个.md`。

## 4. 创建 Release

版本标签建议清晰，例如：

```text
v0.1.7
```

资产文件名建议：

```text
GrokStoryHandoff-windows-v0.1.7.zip
```

## 5. Release Notes 模板

```md
## Grok Story Handoff v0.1.7

### Highlights
- Windows GUI story-folder handoff workflow.
- Local OpenAI-compatible model endpoint support.
- Generates master story canon, story bible, recent context, and next-window handoff prompt.

### Privacy reminder
Do not upload private `.mhtml`, `master/`, `handoff/`, `runs/`, or `debug/` folders when reporting issues.
```
