# 零基础使用指南

**醒目说明：本工具的输入不是普通 txt，也不是截图，而是 Grok 页面通过 Ctrl+S 保存出来的 `.mhtml` 对话窗口。**

这份文档写给完全不会代码的用户。你只需要会打开 PowerShell、复制命令、选择文件。

## 0. 使用前准备

你需要：

- Windows 上安装 Python 3.10 或更高版本。
- 安装并启动 LM Studio。
- 在 LM Studio 里加载一个本地模型。
- 打开 LM Studio 的 OpenAI-compatible server。

默认 Base URL：

```text
http://127.0.0.1:1234/v1
```

如果 PowerShell 提示 `python` 不是可识别命令，说明 Python 没装好或不在 PATH。重新安装 Python 时勾选 `Add Python to PATH`。

## 1. 安装依赖

打开 PowerShell：

```powershell
cd D:\Grok
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

以后每次重新打开 PowerShell，如果要使用这个工具，先运行：

```powershell
cd D:\Grok
.\.venv\Scripts\Activate.ps1
```

## 2. 启动 GUI

一键命令：

```powershell
cd D:\Grok
.\.venv\Scripts\Activate.ps1
python grok_handoff_gui.py
```

也可以通过 CLI 启动 GUI：

```powershell
python grok_handoff_cli.py gui
```

GUI 支持中文 / 日本語 / English。默认会根据系统语言自动选择：

- 中文系统显示中文。
- 日文系统显示日本語。
- 其他系统显示 English。

你也可以在右上角语言下拉框手动切换。手动选择会保存到 `grok_config.json`，下次启动优先使用这个设置。

注意：日志中的模型输出和命令行输出不会被翻译，这样方便排查原始错误。

## 3. 第一次清洗 .mhtml

先保存 Grok 对话：

1. 打开 Grok 对话页面。
2. 等页面内容加载完整。
3. 按 `Ctrl+S`。
4. 保存为 `.mhtml` 或“网页，单个文件”。

然后在 GUI 中：

1. 点击 `MHTML 文件` 旁边的 `选择`。
2. 选择刚保存的 `.mhtml`。
3. 点击 `项目目录` 旁边的 `选择`，选择或新建项目目录，例如 `D:\Grok_Project`。
4. 确认 Base URL 是 `http://127.0.0.1:1234/v1`。
5. 模型名可以先留空。
6. `canon_part_chars` 建议先用 `12000`。
7. 点击 `清洗当前 MHTML`。

命令行方式：

```powershell
python grok_handoff_cli.py clean --input "D:\path\story.mhtml" --output "D:\Grok_Project\runs\story_run" --canon-part-chars 12000
```

路径里有空格时必须加英文双引号。

## 3.1 GUI 完整流程

1. 启动 `GrokStoryHandoff.exe` 或运行：

```powershell
python grok_handoff_gui.py
```

2. 选择 `.mhtml` 文件。
3. 选择 `project_dir` 项目目录。
4. 点击 `清洗当前 MHTML`。
5. 查看日志窗口滚动，确认 subprocess 输出持续出现。
6. 进度条转动时不要关闭窗口。
7. 清洗完成后点击 `吸收已跑好的 run 目录`。
8. 点击 `生成 handoff 包`。
9. 点击 `打开 handoff 文件夹`。
10. 复制 `03_下个窗口直接复制这个.md` 到下一个 Grok 窗口。

## 4. 第二个 Grok 窗口满了之后怎么继续

当一个 Grok 窗口写满后：

1. 点击 `吸收已跑好的 run 目录`，把这次窗口吸收到 `master/`。
2. 点击 `生成 handoff 包`。
3. 点击 `打开输出目录`。
4. 打开 `handoff/03_下个窗口直接复制这个.md`。
5. 把内容复制到下一个 Grok 窗口。
6. 新窗口继续写。
7. 新窗口也满了以后，再保存新的 `.mhtml`，重复清洗、吸收、生成 handoff。

命令行方式：

```powershell
python grok_handoff_cli.py absorb-run --run-dir "D:\Grok_Project\runs\story_run" --project-dir "D:\Grok_Project"
python grok_handoff_cli.py handoff --project-dir "D:\Grok_Project"
```

## 5. Token 与切块建议

不要一开始就把 `canon_part_chars` 设太大。

- `24000` 字符可能让单块 prompt 接近 1.6 万 tokens，本地 16GB 显卡会吃力。
- `12000` 字符更稳，实际单块经常约 7000-11000 prompt tokens。
- 块数会变多，例如 12 块变成 24 块，但失败率更低。
- 推荐默认：`canon_part_chars = 12000`。
- 高显存机器可尝试 `16000-24000`。
- 如果出现 `n_keep >= n_ctx`，先把 `canon_part_chars`、`old_recent_chars`、`new_head_chars`、`new_tail_chars` 降低 30%。

不要把完整正文一口气喂给本地模型：

- `story_canon.md` 会越来越长。
- 总正文适合给人读，不适合每次完整塞给模型。
- 正确结构是：
  - 完整正文 = `master/01_当前正史正文.md`
  - 压缩设定 = `master/02_当前设定状态.md`
  - 最近正文 = `handoff/02_最近正文_喂给Grok.md`
  - 直接投喂 = `handoff/03_下个窗口直接复制这个.md`

## 6. 推荐模型与硬件

清洗正文建议使用稳定、听指令、非 thinking 的 instruct 模型。强 thinking 模型可能把输出额度花在 `reasoning_tokens` 上，导致最终 `content` 为空。

硬件经验建议：

| 档位 | 建议 |
| --- | --- |
| 入门 | 8GB VRAM，小模型和小块清洗，速度慢。 |
| 舒适 | 12GB-16GB VRAM，例如 RTX 3060 12GB / 4070 Ti SUPER / 4080S，建议 `canon_part_chars=8000-12000`。 |
| 推荐 | 24GB VRAM，例如 RTX 3090 / 4090 / 5090D V2 24GB。 |
| 理想 | 32GB+ VRAM，例如 RTX 5090 / 5090D 32GB。 |
| Mac | 64GB/96GB/128GB 统一内存适合大模型和长上下文，但不一定比高端 NVIDIA GPU 更快。 |

如果处理 NSFW / 成人向 / 高敏内容，请使用你本地合法可用、未过度限制的本地模型；云端模型可能拒绝或改写内容。用户需要自行遵守当地法律与平台规则。

## 7. 出错如何看日志

GUI 下方有日志框。出错时先看最后几十行。

常见问题：

- `Connection refused`：LM Studio 没启动，或 server 没打开。
- `model not found`：模型名填错了，试试留空。
- `run 目录缺少 story_canon.md`：还没有清洗 `.mhtml`，或选错了 run 目录。
- `n_keep >= n_ctx`：prompt 超过模型上下文，降低切块参数或调高 LM Studio Context Length。
- `finish_reason: length` 且 `content: ""`：thinking 模型把输出 token 吃光，换非 thinking 模型或缩短 prompt。

运行长任务时不要让电脑睡眠，否则本地模型调用可能中断。

更多排障见 [TROUBLESHOOTING_zh.md](TROUBLESHOOTING_zh.md)。

## 8. 停止任务与暂停/恢复说明

- GUI 新增“停止当前任务”按钮：任务运行时可点击停止。
- 停止后会先尝试优雅终止子进程，必要时强制结束；进度条会停止，状态显示“已停止”。
- 当前版本**不支持真正暂停/恢复**。如果中途停止，请直接重新运行。
- v3.5 会落盘部分中间缓存，通常可以降低重跑成本，但这不等于完整断点续跑。

## 9. 日志乱码排查（中文/日文）

- GUI 子进程已按 UTF-8 启动并读取日志，正常情况下不应乱码。
- 若仍偶发乱码，可尝试：
  1) 确认系统区域/终端编码设置；
  2) Windows 可选 UTF-8 兼容设置（Beta）；
  3) 重新打开 GUI 后再跑。

## 测试 LM Studio 连接

GUI 新增了“测试 LM Studio 连接”按钮。点击后会请求 `<Base URL>/models`（自动处理 `.../v1`），超时 5 秒。
- 成功：提示连接成功。
- 失败：给出友好提示（检查 LM Studio、Local Server、Base URL、防火墙）。

当前版本支持“停止当前任务”，不支持真正暂停/恢复。任务被停止后可重新运行；v3.5 的部分中间结果可降低重跑成本。
