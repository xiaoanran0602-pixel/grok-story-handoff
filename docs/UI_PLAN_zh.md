# GUI 路线计划

## 第一版：Tkinter 简单界面

目标是能用、稳定、少依赖，优先照顾普通用户双击或一键启动。

已规划能力：

- 选择 `.mhtml` 文件。
- 选择项目目录 `project_dir`。
- 中文 / 日本語 / English 三语界面。
- 根据系统语言自动选择界面语言。
- 右上角语言下拉框即时切换，不需要重启。
- 手动语言选择保存到 `grok_config.json`。
- 设置 LM Studio Base URL，默认 `http://127.0.0.1:1234/v1`。
- 设置模型名，可留空。
- 设置 `canon_part_chars`，默认建议 `12000`。
- 一键清洗当前 MHTML。
- 一键吸收已跑好的 run 目录。
- 一键生成 handoff 包。
- 打开输出目录。
- 日志框实时显示命令行输出。

第一版只做入口壳，不重写 v6/v3.5 的核心逻辑。

当前多语言实现使用轻量 dict 翻译表，集中在 `grok_i18n.py`。如果未来 UI 文案和文档翻译量变大，可以迁移到 Python `gettext`。

## 第二版：更顺手的日常使用

可以继续加入：

- 自动保存上次使用的配置。
- 最近项目列表。
- 任务进度条。
- “打开 story_canon.md”按钮。
- “打开 master 文件夹”按钮。
- “打开 handoff 文件夹”按钮。
- 常见错误提示翻译成更友好的中文。
- 更多语言和更完整的翻译检查。
- 参数预设：低显存安全、4080S 推荐、24GB 显存、32GB+ 显存。
- 防睡眠提示：长任务运行中提醒用户不要让电脑睡眠。

第二版尤其适合把实际踩坑收进 UI：

- `n_keep >= n_ctx`：提示降低 `canon_part_chars` 等参数。
- `finish_reason=length`：提示输出 token 不够。
- `reasoning_tokens` 很高且 `content` 为空：提示换非 thinking 模型。
- LM Studio 未启动：提示检查本地 server。
- 模型名不对：提示留空或复制 LM Studio 模型名。

## 第三版：PyInstaller 打包成 exe

等 GUI 稳定后，可以考虑用 PyInstaller 打包：

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed grok_handoff_gui.py
```

第三版目标：

- 普通用户不用打开命令行。
- 双击 exe 启动。
- 附带默认配置示例。
- 文档中加入完整截图教程。
- 打包前检查 `.gitignore` 和发布目录，避免把 `.mhtml`、`runs/`、`master/`、`handoff/`、`debug/` 等用户故事数据打进发布包。

## 长期方向

后续可以考虑：

- 保存多套模型配置。
- 显示每个 run 是否已经吸收。
- GUI 内直接打开 `handoff/03_下个窗口直接复制这个.md`。
- GUI 内显示 token/chunk 经验提示。
- 为 NSFW / 成人向项目提供本地模型合规提醒，但不上传、不审核、不替用户判断法律风险。
