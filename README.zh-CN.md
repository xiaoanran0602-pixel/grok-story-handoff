# Grok Story Handoff

把 Grok 长对话变成可持续创作的「故事目录向导」。

Windows 下载： https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases

## 30 秒理解

这个工具不是让你管理一堆技术文件。你只需要准备一个**故事目录**。

每次 Grok 窗口写满：
1. 在 Grok 页面 `Ctrl+S` 保存成 `.mhtml`。
2. 把 `.mhtml` 放进这个故事目录。
3. 打开软件，选择这个故事目录。
4. 软件会自动扫描，并告诉你「发现了什么」。
5. 点「追加这个新 Grok 窗口」。
6. 完成后复制 `handoff/03_下个窗口直接复制这个.md` 给下一个 Grok 窗口。

**同一个故事，请一直使用同一个故事目录。不同故事，请使用不同目录。**

## 软件发现了什么（怎么理解）

- 发现 `master/`：这个目录已经是故事项目。
- 发现新的 `.mhtml`：可以继续追加新窗口内容。
- 发现 `handoff/03_下个窗口直接复制这个.md`：已经能给下一个 Grok 用。
- 什么都没发现：这是一个新故事目录，可以从头创建。

## 三种常见操作

### 1) 追加新 Grok 窗口（最常用）
- 用于第二个、第三个窗口继续写。
- 在旧 master 基础上增加新内容。
- 流程是自动 `clean → absorb → handoff`。

### 2) 从头重新整理故事目录
- 用于之前跑错、设定错乱、想重建。
- 可能覆盖 `master/handoff`。
- 不会删除原始 `.mhtml`。

### 3) 只重新生成下个窗口交接包
- 用于 master 已经整理好，只想刷新 handoff。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python grok_handoff_gui.py
```

## 说明

- 核心脚本保持不变：
  - `grok_mhtml_bible_pipeline_v6.py`
  - `grok_story_handoff_manager_v3_5_checkpoint_bible.py`
- GUI 是向导层，负责更好理解和操作。

更多细节请看 `docs/USAGE_zh.md`。


## Creator Pack 上架

如果你要把这个项目包装成“创作者可直接购买的成品包”，请看：

- [`docs/CREATOR_PACK_GO_TO_MARKET_zh.md`](docs/CREATOR_PACK_GO_TO_MARKET_zh.md)

这份清单覆盖定价、渠道、截图要求与 48 小时上架动作。

## 打包与发布口径

默认推荐使用 `--onedir`：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
``` 

默认产物：

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
``` 

`--onefile` 可选，但为调试和发布稳定性，推荐 `--onedir`。
