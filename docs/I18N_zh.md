# 多语言界面说明

GUI 支持三种界面语言：

- 中文
- 日本語
- English

## 自动选择语言

启动时，GUI 会优先读取 `grok_config.json` 里的 `language` 字段。

如果没有配置文件，GUI 会尝试根据系统语言自动选择：

- 中文系统 → `zh-CN`
- 日文系统 → `ja-JP`
- 其他系统 → `en-US`

语言检测逻辑在 `grok_i18n.py` 中：

1. 尝试 `locale.setlocale(locale.LC_ALL, "")`。
2. 读取 `locale.getlocale()[0]`。
3. 如果失败或无法识别，再检查环境变量 `LC_ALL` / `LANGUAGE` / `LANG`。
4. 如果仍然无法识别，默认 `en-US`。

没有使用 `locale.getdefaultlocale()`，因为它在 Python 3.11 后已废弃，未来会移除。

## 手动切换语言

GUI 右上角有语言下拉框：

- 中文
- 日本語
- English

切换后 UI 文案会立即刷新，不需要重启程序。

手动选择会保存到：

```text
grok_config.json
```

字段：

```json
{
  "language": "zh-CN"
}
```

`grok_config.json` 是本地个人配置，已经加入 `.gitignore`，不建议提交到公开仓库。

## 什么不会被翻译

以下内容不会被翻译：

- 用户输入的文件路径。
- 日志框里的原始命令。
- subprocess 输出。
- 模型返回的内容。
- LM Studio / Python / 系统错误原文。

这样做是为了方便排查真实错误，避免翻译后丢失关键信息。

## 当前实现

当前使用轻量 dict 翻译表，集中在：

```text
grok_i18n.py
```

主要函数：

- `detect_system_language() -> str`
- `normalize_language_code(raw: str) -> str`
- `t(key: str, lang: str | None = None) -> str`
- `get_supported_languages() -> dict`

如果某个翻译 key 缺失，`t()` 会回退到英文；英文也没有时返回 key 本身，避免 UI 崩溃。

## 未来迁移

如果未来 UI 文案、文档和错误提示越来越多，可以迁移到 Python 标准库 `gettext`，使用 `.po` / `.mo` 文件管理翻译。
