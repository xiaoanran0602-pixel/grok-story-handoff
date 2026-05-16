# Grok Story Handoff

**把写满的 Grok 长篇对话，整理成下个窗口能继续写的故事交接包。**

Grok Story Handoff 是一个给 Grok 长篇小说、角色互动、跑团式剧情和世界观创作者使用的本地工具。你把完整 Grok 对话保存成 `.mhtml` / `.mht`，放进同一个故事目录，软件会整理出当前正史、设定状态、最近剧情，并生成一个可以直接复制到新 Grok 窗口的交接提示词。

[Windows 下载](https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases) · [English README](README.md) · [中文使用指南](docs/USER_GUIDE_zh-CN.md) · [故障排查](docs/TROUBLESHOOTING_zh.md)

> 这是一个独立工具，与 xAI 或 Grok 官方无隶属关系。

## 它解决什么问题

长篇 Grok 对话写到后面，常见问题是：窗口太长、设定遗忘、角色关系漂移、换窗口后需要重新解释一大堆背景。

这个工具会把旧窗口整理成一个可继续使用的故事项目：

- **当前正史正文**：把真正的故事内容从聊天噪音里分离出来。
- **当前设定状态**：整理角色、关系、地点、世界规则、未解决伏笔。
- **最近剧情上下文**：保留下一窗口最需要接上的近段剧情。
- **下个窗口交接包**：生成一个可直接复制给 Grok 的续写提示词。

## 30 秒流程

1. 一个故事准备一个专用目录。
2. 在 Grok 页面把完整对话保存成 `.mhtml` / `.mht`。
3. 把保存的文件放进这个故事目录。
4. 打开 Grok Story Handoff，选择这个故事目录。
5. 点击 **追加新 Grok 窗口**。
6. 完成后复制 `handoff/03_下个窗口直接复制这个.md` 到新的 Grok 窗口。

同一个故事一直用同一个目录；不同故事请分开目录。

## 下载

Windows 打包版下载：

**https://github.com/xiaoanran0602-pixel/grok-story-handoff/releases**

打包版适合不想手动安装 Python 的用户。

## 从源码运行

需要：

- Python 3.10+
- 本地 OpenAI-compatible 模型服务，例如 LM Studio
- 已保存的 Grok `.mhtml` / `.mht` 对话文件

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python grok_handoff_gui.py
```

查看 CLI 帮助：

```powershell
python grok_handoff_cli.py --help
```

默认本地 API 地址：

```text
http://127.0.0.1:1234/v1
```

模型名可以留空，软件会尝试从本地 OpenAI-compatible API 自动识别。

## 三个主要操作

| 操作 | 适合什么时候用 |
| --- | --- |
| **追加新 Grok 窗口** | 又写完一个 Grok 窗口，想继续同一个故事。 |
| **从头重建故事项目** | 之前整理错了，或者想基于保存的 `.mhtml` 重新整理。 |
| **只重新生成交接包** | `master/` 已经整理好，只想刷新下一窗口提示词。 |

## 输出文件

| 路径 | 用途 |
| --- | --- |
| `master/01_当前正史正文.md` | 长期保存的当前正史正文。 |
| `master/02_当前设定状态.md` | 当前设定、角色、关系、世界规则。 |
| `handoff/02_最近正文_喂给Grok.md` | 给下一窗口补充的最近剧情。 |
| `handoff/03_下个窗口直接复制这个.md` | 最终复制到新 Grok 窗口的交接提示词。 |
| `runs/` | 每次窗口处理的运行输出。 |
| `debug/` | 长任务的中间检查点文件。 |

## 隐私说明

软件处理的是你放进故事目录的本地文件。故事文本会发送给你配置的模型服务。如果使用默认本地地址，模型服务在本机；如果你改成云端 API，内容可能会发送给对应服务商。

不要公开上传私人故事数据。仓库 `.gitignore` 默认排除了 `.mhtml`、`runs/`、`master/`、`handoff/`、`debug/` 等常见私密和生成文件，但提交前仍建议自己检查一次。

更多说明见：[隐私与安全](docs/PRIVACY_AND_SAFETY.md)。

## 文档

- [中文使用指南](docs/USER_GUIDE_zh-CN.md)
- [English User Guide](docs/USER_GUIDE_en.md)
- [故障排查](docs/TROUBLESHOOTING_zh.md)
- [发布检查清单](docs/RELEASE_zh.md)
- [仓库结构](REPOSITORY_STRUCTURE.md)

## 许可证

MIT License. See [LICENSE](LICENSE).
