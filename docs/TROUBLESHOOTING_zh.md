# 常见问题与排障

本文档可能包含规划/内部细节；当前实际使用请优先参考 README 和 USAGE。

这份文档专门记录实际使用本地模型、LM Studio、OpenAI-compatible API 时容易踩的坑。

## 1. `n_keep >= n_ctx`

错误示例：

```text
HTTP 400: The number of tokens to keep from the initial prompt is greater than the context length
n_keep: 41859 >= n_ctx: 35072
```

含义：

- 本次 prompt 太长，超过了 LM Studio / llama.cpp 当前上下文长度。
- 字符数不等于 token 数。中文、英文、符号、系统提示、规则 prompt 都会变成 token。
- `canon_part_chars=24000` 时，单块 prompt 可能接近 1.6 万 tokens；再加上其他上下文，很容易把本地模型顶爆。

解决：

- 降低 `canon_part_chars` / `old_recent_chars` / `new_head_chars` / `new_tail_chars`。
- 第一次可以直接把这些值降低 30%。
- 减少 handoff/bible 输入量。
- 在 LM Studio 里调高 Context Length，并重新加载模型。
- 换更大显存硬件或更小模型。

推荐先用：

```text
canon_part_chars = 12000
```

如果仍然失败，试：

```text
canon_part_chars = 8000
```

## 2. 模型返回空内容

常见日志：

```text
finish_reason: length
completion_tokens: 2000
reasoning_tokens: 1997
content: ""
```

含义：

- 有些 thinking 模型即使写了 `/no_think`，也会把输出额度几乎全部用在 `reasoning_content`。
- 最终 answer `content` 为空，脚本会报“模型返回空内容”。

解决：

- 增大 `max_tokens`。
- 降低 prompt 输入长度，给输出留空间。
- 换非 thinking instruct 模型。
- 避免把 prompt 塞到接近上下文上限。

## 3. `finish_reason=length`

含义：

- 模型输出达到当前最大输出 token 限制。
- 这不一定代表模型坏了，只代表它没来得及把最终答案写完。

解决：

- 增大输出 token 限制。
- 缩短输入 prompt。
- 降低 `canon_part_chars`。
- 使用更擅长指令输出的非 thinking 模型。

## 4. `reasoning_tokens` 吃光输出

表现：

- 日志里 `reasoning_tokens` 很高。
- `content` 很短或为空。
- 模型看起来“思考”很久，但没有有效结果。

解决：

- 换非 thinking instruct 模型。
- 如果模型支持关闭 thinking，在 LM Studio 或 prompt 中关闭。
- 缩短输入，给最终 answer 留 token。
- 不要把 prompt 塞满上下文窗口。

## 5. GUI 没反应

可能原因：

- 模型正在慢慢跑，日志暂时没有新输出。
- LM Studio 没启动或模型没加载。
- 本地模型卡在超长 prompt。
- 电脑进入睡眠或显卡被其他程序占用。

处理：

- 先看 GUI 底部日志框。
- 打开 LM Studio 看 server 和模型是否正在响应。
- 长任务运行中不要让电脑睡眠。
- 如果长期无输出，降低 `canon_part_chars` 后重试。

## 6. LM Studio 未启动

常见表现：

```text
Connection refused
Failed to establish a new connection
```

解决：

- 打开 LM Studio。
- 加载模型。
- 开启 Local Server / OpenAI-compatible server。
- 确认 Base URL 是：

```text
http://127.0.0.1:1234/v1
```

## 7. 模型名不对

常见表现：

```text
model not found
404
```

解决：

- GUI 里模型名先留空，让脚本自动选择。
- 或从 LM Studio 的模型列表复制准确模型名。
- 注意大小写、空格和特殊符号。

## 8. Python 不在 PATH

常见表现：

```text
python : 无法将“python”项识别为 cmdlet、函数、脚本文件或可运行程序的名称
```

解决：

- 安装 Python 3.10+。
- 安装时勾选 `Add Python to PATH`。
- 重新打开 PowerShell。
- 再试：

```powershell
python --version
```

## 9. 文件路径有空格

路径里有空格时，命令行必须加英文双引号：

```powershell
python grok_handoff_cli.py clean --input "D:\My Stories\story window.mhtml" --output "D:\Grok Project\runs\story_run" --canon-part-chars 12000
```

## 10. 运行中不要让电脑睡眠

本地模型任务可能运行很久。电脑睡眠会导致：

- LM Studio 中断。
- 显卡任务停止。
- Python subprocess 卡住或失败。
- 中间结果不完整。

建议：

- 插电运行。
- 临时关闭睡眠。
- 长任务前确认散热和显存余量。

## 11. 为什么不直接把完整 story_canon.md 喂给模型

`story_canon.md` 和 `master` 正文会越来越长。完整正文适合给人读，不适合每次完整塞给模型。

推荐使用：

- 完整正文 = `master/01_当前正史正文.md`
- 压缩设定 = `master/02_当前设定状态.md`
- 最近正文 = `handoff/02_最近正文_喂给Grok.md`
- 直接投喂 = `handoff/03_下个窗口直接复制这个.md`

## 12. NSFW / 成人向内容

本工具只处理用户本地文件。如果项目包含 NSFW、成人向或高敏虚构内容，请使用你本地合法可用、未过度限制的本地模型。云端 API 可能拒绝、过滤或改写内容。

用户需要自行遵守当地法律、平台规则以及必要的同意与安全边界。

## 13. GUI 日志出现乱码（中文/日文）

当前 GUI 已对 Python 子进程启用 UTF-8 输出与读取。若仍出现乱码：

- 重启 GUI 与 LM Studio；
- 检查 Windows 区域/编码设置；
- 可尝试启用 Windows 的 UTF-8 兼容选项（Beta）。

一般用户在默认配置下不需要额外设置。

## 14. 如何中止长任务

- 任务运行时可点击“停止当前任务”。
- GUI 会先发送终止请求，若几秒内未退出会强制结束。
- 停止后状态为“已停止”，不会弹“任务失败”。
- 目前不支持真正暂停/恢复；请在停止后重新运行。

## Windows Actions UTF-8
Windows GitHub Actions 可能需要 UTF-8 模式，因为 CLI help 包含中文/日文文本。若出现 UnicodeEncodeError / cp1252，workflow 应设置 `PYTHONUTF8=1` 和 `PYTHONIOENCODING=utf-8`。



