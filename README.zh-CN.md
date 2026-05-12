# Grok Story Handoff

这是一个基于 AI 的 Grok 长对话清洗与续写交接工具。

输入：Grok 保存的 `.mhtml` 对话  
输出：清洗后的 story canon + story bible + 下个窗口续写 handoff 包

Windows 下载： https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases

中文说明。英文版请看 [README.md](README.md)。

## 项目简介

这个项目适合长篇小说创作：一个 Grok 窗口写满后，不要把整段超长对话硬塞进下一个窗口，而是：

1. 把当前 Grok 页面保存成 `.mhtml`。
2. 清洗出 `story_canon.md`。
3. 吸收到项目级 `master/`。
4. 生成精简的 `handoff/` 投喂包。
5. 把 handoff 复制给下一个 Grok 窗口继续写。

中间结果落盘很重要：长任务不要只存在内存里。v3.5 应把 chunk 提取、栏目合并、中间草稿写到 `debug/init_bible_cache_v3_5/` 和 `debug/init_bible_sections_v3_5/`。如果中途失败，用户可以从中间文件恢复，不必从头重跑。


## 适合谁？

- 用 Grok 写长篇小说、角色互动、世界观故事的人。
- 经常遇到长对话变笨、串线、忘设定的人。
- 想把 AI 对话里的正文、废话、总结、设定分离出来的人。
- 想让新窗口继续接住剧情的人。

## 快速开始

建议 Python 3.10 或更高版本：

```powershell
cd D:\Grok
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

启动 GUI：

```powershell
python grok_handoff_gui.py
```

通过 CLI 启动 GUI：

```powershell
python grok_handoff_cli.py gui
```

查看 CLI：

```powershell
python grok_handoff_cli.py --help
```

## 图形界面使用

普通用户 GUI 流程：

1. 选 `.mhtml`。
2. 选 `project_dir`，例如 `D:\Grok_Project`。
3. 点击“清洗当前 MHTML”。
4. 点击“吸收已跑好的 run 目录”。
5. 打开 `handoff/03_下个窗口直接复制这个.md`，复制给下一个 Grok 窗口。

LM Studio 默认地址通常是：

```text
http://127.0.0.1:1234/v1
```

模型名可以留空。留空时，原脚本会尝试从本地 OpenAI-compatible API 自动选择模型。

### 多语言界面

GUI 会尝试根据系统语言自动切换：

- 中文系统 → 中文
- 日文系统 → 日本語
- 其他系统 → English

也可以在右上角手动切换语言。手动选择会保存到 `grok_config.json`。

GUI 界面文案会翻译，但模型输出、日志和命令行输出会保留原文，不会强行翻译。

### 停止按钮与日志编码

- GUI 现已支持**停止当前任务**（适合长任务中途取消）。
- GUI 子进程已强制 UTF-8（`-X utf8`、`PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`），用于降低中文/日文日志乱码概率。
- 若 Windows 仍偶发乱码，可检查系统区域/UTF-8 设置；普通用户一般不需要额外操作。
- 当前**不支持真正暂停/恢复**。现阶段建议停止后重跑；v3.5 会落盘部分中间缓存，可降低重跑成本。

实现说明见 [docs/I18N_zh.md](docs/I18N_zh.md)。

## GUI 截图占位

截图待补。

## Windows EXE 打包

PyInstaller 可以把 Python 应用和依赖打包，让普通用户无需安装 Python 也能运行。

推荐打包命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

脚本内部会执行：

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --onedir --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
```

推荐输出：

```text
dist\GrokStoryHandoff\GrokStoryHandoff.exe
```

建议先发布 `onedir` 版本，把整个 `dist\GrokStoryHandoff` 文件夹压缩成 zip。`--onedir` 比 `--onefile` 更适合第一版，因为 `--onefile` 每次启动会解包，启动更慢，也可能更难排查路径问题。

打包后的 GUI exe 会用内部子进程入口（`--run-script v6/manager`）调用原核心模块，因此用户不需要额外安装 Python 也能运行打包版。

如果用户强烈想要单文件，可以手动运行：

```powershell
python -m PyInstaller --onefile --windowed --name GrokStoryHandoff --hidden-import grok_mhtml_bible_pipeline_v6 --hidden-import grok_story_handoff_manager_v3_5_checkpoint_bible grok_handoff_gui.py
```

## GitHub Release / 发布 Release

GitHub Release 用来上传 exe/zip 和写 release notes。

第一版建议：

- Tag: `v0.1.0`
- Title: `Grok Story Handoff v0.1.0`
- 上传：`GrokStoryHandoff-windows-v0.1.0.zip`
- Release notes 写：first public preview、Tkinter GUI、CLI wrapper、Grok `.mhtml` canon extraction、handoff pack generation、toast workshop docs。

发布前必须确认没有上传私人故事数据。

详细流程见 [docs/RELEASE_zh.md](docs/RELEASE_zh.md)。

## GitHub Pages / 项目网站

GitHub Pages 可用于放一个简单项目介绍页和下载入口。

首页可以包含：

- 项目一句话介绍。
- 下载按钮，链接到 GitHub Releases。
- 面包工坊比喻。
- 快速开始。
- 隐私提醒。
- 截图。

当前草稿见 [docs/index.md](docs/index.md)。第一版可以直接用 README，不必复杂建站。

详细说明见 [docs/GITHUB_PAGES_zh.md](docs/GITHUB_PAGES_zh.md)。

## 命令行使用

清洗 MHTML：

```powershell
python grok_handoff_cli.py clean --input "D:\path\story.mhtml" --output "D:\Grok_Project\runs\story_run" --canon-part-chars 12000
```

吸收 run：

```powershell
python grok_handoff_cli.py absorb-run --run-dir "D:\Grok_Project\runs\story_run" --project-dir "D:\Grok_Project"
```

生成 handoff：

```powershell
python grok_handoff_cli.py handoff --project-dir "D:\Grok_Project"
```

原来的两个核心脚本仍然可以直接运行。

## 面包工坊比喻

你可以把这个工具理解成一个“Grok 故事面包机”：

- `.mhtml` = 原始面团，里面混着正文、聊天、总结、废话。
- `story_canon_parts/` = 切片。
- `story_canon.md` = 烤好的正史吐司。
- `removed_meta.md` = 削掉的焦边。
- `master/` = 长期面包柜。
- `handoff/` = 给下一个 Grok 窗口的早餐包。

流程：

```text
保存 Grok 窗口 -> 放进面包机 -> 切片烘烤 -> 合成正史吐司 -> 打包早餐包 -> 喂给下一个 Grok。
```

## 推荐硬件

以下是经验建议，不是 benchmark。

| 档位 | 建议 |
| --- | --- |
| 入门 | 8GB VRAM，可跑小模型和小块清洗，但速度慢。 |
| 舒适 | 12GB-16GB VRAM，例如 RTX 3060 12GB / 4070 Ti SUPER / 4080S，建议 `canon_part_chars=8000-12000`。 |
| 推荐 | 24GB VRAM，例如 RTX 3090 / 4090 / 5090D V2 24GB，可跑更大模型和更长上下文。 |
| 理想 | 32GB+ VRAM，例如 RTX 5090 / 5090D 32GB，适合更长上下文和更厚 story bible。 |
| Mac | 64GB/96GB/128GB 统一内存适合更大模型和长上下文，但不一定比高端 NVIDIA GPU 更快。 |

## 推荐模型

- 本工具需要本地 OpenAI-compatible API，推荐 LM Studio。
- LM Studio 默认地址通常是 `http://127.0.0.1:1234/v1`。
- 清洗正文：建议使用稳定、听指令、非 thinking 的 instruct 模型。
- 生成详细 story bible：建议使用上下文较长、输出稳定的 instruct 模型。
- 不推荐强 thinking 模型作为默认整理模型，因为可能出现 `reasoning_tokens` 吃光输出。
- 如果处理 NSFW / 成人向 / 高敏内容，请使用你本地合法可用、未过度限制的本地模型；云端模型可能拒绝或改写内容。
- 用户需要自行遵守当地法律与平台规则。

资料提示：LM Studio 提供本地 server 和 OpenAI-compatible endpoints；Python Tkinter 是 Python 标准 Tcl/Tk 图形界面；PyInstaller 可把 Python 应用打包成独立可执行文件；llama.cpp / llama-cpp-python 风格运行时在请求 token 超过上下文窗口时可能报错。

## Token 与切块建议

- `canon_part_chars` 不要太大。
- `24000` 字符可能导致单块 prompt 接近 1.6 万 tokens，本地 16GB 显卡会比较吃力。
- `12000` 字符更稳，实际单块经常约 7000-11000 prompt tokens。
- 块数会变多，例如 12 块变成 24 块，但失败率更低。
- 推荐默认：`canon_part_chars = 12000`。
- 高显存机器可尝试 `16000-24000`。
- 如果出现 `n_keep >= n_ctx`，先把 `canon_part_chars`、`old_recent_chars`、`new_head_chars`、`new_tail_chars` 降低 30%。

推荐参数表：

| 场景 | canon_part_chars | old_recent_chars | new_head_chars | new_tail_chars | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| 低显存安全 | 8000 | 8000 | 6000 | 8000 | 小显存优先从这里试。 |
| 4080S 推荐 | 12000 | 10000 | 8000 | 10000 | 更稳的日常默认。 |
| 24GB 显存 | 16000 | 14000 | 10000 | 14000 | 稳定后再加大。 |
| 32GB+ 显存 | 20000-24000 | 18000 | 12000 | 18000 | 适合长上下文。 |

如果出现 `n_keep >= n_ctx`，先把这些参数降 30%。如果内容太简略，不要只加大单次 prompt；优先使用 v3.5 的分栏目、分块、落盘流程。

也不要把完整正文一口气喂给本地模型：

- `story_canon.md` 会越来越长。
- 总正文适合给人读，不适合每次完整塞给模型。
- 正确结构是：
  - 完整正文 = `master/01_当前正史正文.md`
  - 压缩设定 = `master/02_当前设定状态.md`
  - 最近正文 = `handoff/02_最近正文_喂给Grok.md`
  - 直接投喂 = `handoff/03_下个窗口直接复制这个.md`

## 常见问题

完整排障见 [docs/TROUBLESHOOTING_zh.md](docs/TROUBLESHOOTING_zh.md)。

### `n_keep >= n_ctx`

错误示例：

```text
HTTP 400: The number of tokens to keep from the initial prompt is greater than the context length
n_keep: 41859 >= n_ctx: 35072
```

含义：

- 本次 prompt 太长，超过了 LM Studio / llama.cpp 当前上下文长度。

解决：

- 降低 `canon_part_chars` / `old_recent_chars` / `new_head_chars` / `new_tail_chars`。
- 减少 handoff/bible 输入量。
- 在 LM Studio 里调高 Context Length 并重新加载模型。
- 换更大显存硬件或更小模型。

### 模型返回空内容

常见日志：

```text
finish_reason: length
completion_tokens: 2000
reasoning_tokens: 1997
content: ""
```

含义：

- 有些 thinking 模型即使写了 `/no_think`，也会把输出额度几乎全部用在 `reasoning_content`。
- 最终 answer content 为空，脚本会报“模型返回空内容”。

解决：

- 增大 `max_tokens`。
- 降低 prompt 输入长度，给输出留空间。
- 换非 thinking instruct 模型。
- 避免把 prompt 塞到接近上下文上限。

### FAQ

**Q: 为什么 24000 chars 反而更容易失败？**  
A: 字符不是 token。中文、英文、符号、系统提示都会变成 token。再加上规则 prompt，很容易把单次 prompt 推高到 1.5 万 token 以上。

**Q: 为什么模型“思考”很久但没有输出？**  
A: thinking 模型可能把 completion token 消耗在 `reasoning_content`，最终 content 为空。请增大 `max_tokens`、缩短 prompt，或换非 thinking 模型。

**Q: 为什么不直接把完整 story_canon.md 喂给 Grok？**  
A: 如果很短可以试；但长期写作会越来越长，推荐用 compressed bible + recent story + next direction。

**Q: 为什么生成的设定状态太简略？**  
A: 单次摘要容易漏信息。使用 v3.5 checkpoint/deep bible 流程，让事件、角色、关系、世界观分栏目提取再合并。

**Q: NSFW 内容能用吗？**  
A: 本工具只处理用户本地文件。请使用本地合法可用的模型，并遵守当地法律和平台政策。云端 API 可能拒绝处理成人内容。

## 隐私与安全

不要提交或公开私人故事数据：

- `.mhtml`、`.mht`、`.html`
- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `mhtml_archive/`
- `story_canon.md`
- `clean_corpus.md`
- `removed_meta.md`
- `canon_index.jsonl`

`.gitignore` 已经默认排除这些内容，但发布前仍建议手动检查。

## 成人内容说明

本工具只处理用户本地文件。如果你的项目包含 NSFW、成人向或高敏虚构内容，请使用你本地合法可用、适合该内容的模型。云端 API 可能拒绝、过滤或改写成人内容。用户需要自行遵守当地法律、平台规则以及必要的同意与安全边界。

## License

MIT License. 见 [LICENSE](LICENSE)。


## 全自动发布
以后不需要本地打包。流程是：
1. Codex 修改代码并开 PR。
2. 合并 PR 到 main。
3. 打开 GitHub → Actions → Release Windows。
4. 点击 Run workflow。
5. 输入版本号，例如 v0.1.1。
6. Actions 会自动打包 Windows exe、生成 zip、创建 Release、上传资产。


## 反馈

欢迎通过 Issues 留言建议、报错日志和功能需求。
https://github.com/xiaoanran0602-pixel/grok-story-handoff/issues


关键词：Grok、AI 写作、长对话清洗、小说正文提取、故事 Bible、角色关系、续写交接包、本地 AI、LM Studio、MHTML 导出。
