# GitHub Pages 项目网站说明

GitHub Pages 可作为静态项目网站。第一版可以直接使用 README，不必复杂建站。

## 第一版建议

最简单方案：

- 仓库主页使用 `README.md`。
- Release 下载放在 GitHub Releases。
- Pages 暂时只放一个轻量首页草稿。

当前首页草稿：

```text
docs/index.md
```

## 如果要启用 GitHub Pages

可以在 GitHub 仓库中：

1. 打开 `Settings`。
2. 找到 `Pages`。
3. Source 选择 `Deploy from a branch`。
4. Branch 选择 `main`。
5. Folder 选择 `/docs`。
6. 保存。

这样 `docs/index.md` 可以作为项目网站首页。

## 网站首页应该包含

- 项目一句话介绍。
- 下载按钮，链接到 GitHub Releases。
- 面包工坊比喻。
- 快速开始。
- 隐私提醒。
- 截图。

## 暂时不要做复杂网站

当前阶段不建议引入复杂前端框架。保持静态 Markdown 或简单 HTML 即可。

后续如果需要更漂亮的展示页，可以新建：

```text
website/index.html
```

但第一版先用 `docs/index.md` 足够。
