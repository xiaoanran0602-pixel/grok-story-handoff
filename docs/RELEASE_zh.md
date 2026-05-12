# 发布流程

本文档只准备发布流程，不会创建真实 GitHub Release。

## 1. 本地测试

```powershell
cd D:\Grok
python grok_handoff_cli.py --help
python grok_handoff_gui.py
```

建议确认：

- GUI 能启动。
- 语言下拉框能切换。
- 日志窗口能滚动。
- 进度条在长任务时会转动。
- CLI help 明确说明输入是 Grok 保存的 `.mhtml` 对话窗口。

## 2. 打包 exe

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

脚本会执行：

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --onedir --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
```

默认使用 `--onedir`，不默认使用 `--onefile`。`--onefile` 每次启动会解包，启动更慢，也更难排查路径问题。

可选单文件命令：

```powershell
python -m PyInstaller --onefile --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
```

## 3. 检查 dist

确认文件存在：

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
```

运行 exe，确认 GUI 能启动。

## 4. 压缩发布包

把整个文件夹：

```text
dist\GrokStoryHandoff
```

压缩为：

```text
GrokStoryHandoff-windows-v0.1.0.zip
```

## 5. 创建 GitHub Release

1. 打开 GitHub 仓库。
2. 点击 `Releases`。
3. 点击 `Draft a new release`。
4. Tag: `v0.1.0`。
5. Title: `Grok Story Handoff v0.1.0`。
6. 上传 `GrokStoryHandoff-windows-v0.1.0.zip`。
7. Release notes 可写：

```text
- First public preview
- Tkinter GUI
- CLI wrapper
- Grok .mhtml canon extraction
- Handoff pack generation
- Toast workshop docs
```

## 6. 注意隐私

发布前确认没有上传：

- `.mhtml`
- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `story_canon.md`
- `clean_corpus.md`
- `removed_meta.md`
- `canon_index.jsonl`
- `grok_config.json`

`.gitignore` 已排除这些内容，但发布前仍要人工检查 zip 和仓库文件。


## 全自动发布
以后不需要本地打包。流程是：
1. Codex 修改代码并开 PR。
2. 合并 PR 到 main。
3. 打开 GitHub → Actions → Release Windows。
4. 点击 Run workflow。
5. 输入版本号，例如 v0.1.1。
6. Actions 会自动打包 Windows exe、生成 zip、创建 Release、上传资产。

## Windows Actions UTF-8
Windows GitHub Actions 可能需要 UTF-8 模式，因为 CLI help 包含中文/日文文本。若出现 UnicodeEncodeError / cp1252，workflow 应设置 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`。
