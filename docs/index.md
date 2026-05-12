# Grok Story Handoff

# Grok 小说交接面包机

Turn saved Grok `.mhtml` conversations into clean story canon and reusable handoff packs.

把 Grok 保存的 `.mhtml` 对话窗口清洗成小说正文，并生成可喂给下一个 Grok 窗口的续写交接包。

## Links / 链接

- [Download from GitHub Releases](../releases)
- [View README](../README.md)
- [Privacy Notes](../README.md#privacy--safety)

## Toast Workshop / 面包工坊

Think of this tool as a Grok Story Toaster:

- `.mhtml` = raw dough / 原始面团
- `story_canon.md` = canon toast / 正史吐司
- `removed_meta.md` = burnt edges / 削掉的焦边
- `master/` = long-term bread cabinet / 长期面包柜
- `handoff/` = breakfast pack for the next Grok window / 下个窗口早餐包

Workflow:

```text
Save Grok window -> slice and clean -> build canon toast -> pack handoff -> feed the next Grok window
保存 Grok 窗口 -> 切片清洗 -> 合成正史吐司 -> 打包 handoff -> 喂给下一个 Grok
```

## Quick Start / 快速开始

```powershell
cd D:\Grok
python grok_handoff_gui.py
```

Or run the packaged Windows app:

```text
GrokStoryHandoff.exe
```

## Privacy / 隐私提醒

Do not publish private story data:

- `.mhtml`
- `runs/`
- `master/`
- `handoff/`
- `debug/`
- `story_canon.md`

不要把私人故事数据上传到公开仓库或发布包里。

## Screenshot / 截图

Screenshot coming soon.

截图待补。
