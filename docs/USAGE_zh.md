# 零基础使用指南（故事目录模式）

## 30 秒理解

你只需要记住一件事：**一个故事 = 一个故事目录**。

每次 Grok 窗口写满：
1. `Ctrl+S` 保存为 `.mhtml`。
2. 把文件放入故事目录。
3. 选择该目录。
4. 点「追加新 Grok 窗口」。
5. 完成后复制 handoff 到下一个 Grok 窗口。

## 软件会自动扫描什么

选择故事目录后，软件会看：
- 当前目录下 `.mhtml/.mht`
- `runs/` `master/` `handoff/` `debug/` `mhtml_archive/`
- 是否有 `master/01_当前正史正文.md`
- 是否有 `handoff/03_下个窗口直接复制这个.md`
- 是否有可能未处理的新 `.mhtml`

## 三种操作怎么选

### 追加新 Grok 窗口（推荐）
- 适合第二个/第三个窗口继续叠加。
- 软件自动完成：清洗 → 吸收 → 生成交接包。

### 从头重新整理
- 适合跑错了、要重建。
- 可能覆盖 master/handoff。
- 不删除原始 `.mhtml`（会弹确认）。

### 只生成 handoff
- master 已经就绪，只想刷新给下一个窗口的复制包。

## 完成后下一步

1. 打开 handoff 文件夹。
2. 打开 `03_下个窗口直接复制这个.md`。
3. 复制全文。
4. 粘贴到新的 Grok 窗口。
5. 在末尾写你下一段剧情方向。

## 安装与启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python grok_handoff_gui.py
```

CLI 帮助：

```powershell
python grok_handoff_cli.py --help
```
