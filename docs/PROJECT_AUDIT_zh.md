# 项目现状审计报告（基于 main）

审计基线：
- 仓库：`xiaoanran0602-pixel/grok-story-handoff`
- 审计分支：`codex/project-audit-main`（从最新 `origin/main` 新建）
- 审计范围：GUI / CLI / i18n / docs / GitHub Actions / Release / 隐私与安全 / open PR
- 约束：不重写核心逻辑，不删除 `grok_mhtml_bible_pipeline_v6.py` 与 `grok_story_handoff_manager_v3_5_checkpoint_bible.py`

## 1. 当前 main 状态总结

- 当前主形态是“**故事目录向导 + 旧流程兼容入口并存**”。
- GUI 主流程已经是“选择故事目录 -> 自动扫描 -> 推荐动作（追加新窗口/创建项目/重生 handoff）”。
- 同时，GUI 仍保留高级入口（clean/absorb），CLI 也仍以 `clean/absorb-run/handoff` 为主。
- 文档层面出现分裂：
  - `README.zh-CN.md` 与 GUI 新向导思路基本一致。
  - `README.md` 仍大量描述旧的 `Clean current MHTML -> Absorb -> Handoff` 手工串联流程，且有中文乱码（mojibake）文本。
- Release 与打包说明不完全一致（workflow 为 onedir；本地脚本默认 onefile；文档也有混写）。

## 2. 当前可用功能

- GUI：可启动，支持故事目录扫描、追加新窗口、重建、仅重生 handoff、测试 LM Studio、停止当前任务（基础版）。
- CLI：`clean` / `absorb-run` / `handoff` / `gui` 可用；`--help` 正常输出。
- i18n：`zh-CN` / `ja-JP` / `en-US` 三语，支持系统语言检测与手动切换。
- 核心脚本：`v6` 与 `v3.5` 脚本均在 main 且可被 GUI/CLI 调用。
- Actions：存在 `release-windows.yml`，支持 `workflow_dispatch` 与 tag 触发，支持版本输入，使用 `windows-latest` + Python 3.13，含 UTF-8 环境变量。

## 3. 当前不可靠功能

- GUI 关闭窗口时未显式终止正在运行的子进程（可能留后台进程）。
- GUI “停止当前任务”只做 `terminate()`，无等待/强制 kill/状态细分（“已停止”与“失败”语义不完全一致）。
- GUI 链式任务状态在某些链路下可能出现“提前 completed/提前解锁”风险（open PR #10 的唯一未合入点之一）。
- Release 形态认知不统一（onefile vs onedir），用户可能按文档得到与 Actions 不同产物。
- 英文 README 与当前 GUI 产品叙事不一致，且存在乱码段落影响专业感与可读性。

## 4. 当前 open PR 处理建议

当前 open PR：
- #10 `codex/fix-json-parsing-issue-in-model-s9h8oh`（`DIRTY`，冲突）

判断：
- 该 PR 与已合并的 #8 / #9 高度重叠，改动文件重合明显（`README.md`、`build_windows.ps1`、`docs/RELEASE_*`、`grok_handoff_gui.py`、`grok_story_handoff_manager_v3_5_checkpoint_bible.py`）。
- 该分支相对 main“main ahead 6、分支 ahead 1”，说明绝大部分已被 main 覆盖，仅剩少量未合入差异。
- 属于典型“旧分支滞后 + 重复改同批文件导致持续冲突”。

建议：
- 关闭 #10（避免继续在旧冲突分支上修）。
- 如需保留 #10 的剩余价值（GUI 链式状态修复），从最新 main 新开干净分支与新 PR，最小 cherry-pick 或手工摘取单点修复。
- 后续只保留“基于最新 main”的单一修复 PR，避免并行改同一批核心文件。

## 5. GUI 问题清单

核查结论：
- 启动时不会自动请求 LM Studio（通过按钮触发）。
- LM Studio 未启动时不会在 GUI 启动阶段崩溃。
- 存在“测试 LM Studio 连接”按钮。
- 存在“停止当前任务”按钮。
- 关闭窗口时当前实现不会先清理子进程（需补最小收尾逻辑）。
- 子进程日志读取已设 `encoding='utf-8', errors='replace'`，乱码风险已显著降低但不能绝对归零。
- 按钮命名已较普通用户友好（主流程），但高级区仍有技术术语。
- 旧按钮名在 GUI 主流程已弱化，但高级操作仍保留 clean/absorb 技术概念。
- 已实现“选择故事目录 / 自动扫描目录 / 追加新窗口”。

## 6. CLI 问题清单

核查结论：
- `python grok_handoff_cli.py --help` 可正常打印（本次实测通过）。
- 存在 stdout/stderr UTF-8 reconfigure fallback（`configure_utf8_stdio`）。
- `clean / absorb-run / handoff / gui` 命令均在。
- `absorb-run` 通过参数调用，不依赖交互式 stdin。
- 路径安全：均以参数 list 传递，支持空格路径。
- subprocess 未使用 shell 拼接字符串。
- 连接失败时有中英双语提示（基于返回码后提示）。

改进点（非 Critical）：
- CLI 与 GUI 能力并不完全等价（如 CLI 的部分细粒度参数 GUI 无入口）。

## 7. Actions / Release 问题清单

核查结论（`.github/workflows/release-windows.yml`）：
- 存在 `release-windows.yml`。
- 支持 `workflow_dispatch`。
- 支持 `version` 输入（示例 `v0.1.1`）。
- `runs-on: windows-latest`。
- Python 3.13。
- 设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`。
- 含 `python -X utf8 ... --help` 校验，规避 cp1252 常见报错。
- 构建方式为 PyInstaller `--onedir`。
- 会将 zip 上传至 GitHub Release（`softprops/action-gh-release`）。
- 不会把 zip 提交回仓库。
- 若同名 Release 已存在，会在“Ensure release does not already exist”步骤失败并退出。

一致性问题：
- workflow（onedir）与本地 `build_windows.ps1` 默认（onefile）及部分文档叙述不一致，容易造成“本地和云端产物不一致”。

## 8. 文档问题清单

主要问题：
- `README.md` 与当前 GUI 产品描述不一致（仍偏旧流程）。
- `README.md` 含明显乱码文本（中英文混排处）。
- `docs/UI_PLAN_zh.md` 偏历史计划文档，部分内容已被实现或过时。
- `docs/RELEASE_zh.md` / `docs/RELEASE_en.md` 与 workflow 的默认打包形态不完全一致。
- 文档总量偏多，重复内容较多（自动发布说明在多处重复）。
- 缺少一个“当前真实能力快照”文档（建议新增并持续维护）。

建议：
- 新增并维护 `docs/PROJECT_STATUS_zh.md`（建议执行）。
- 将“最短使用路径”统一前置到 README 第一屏与 `docs/USAGE_zh.md` 首段。
- 将历史/规划型文档与现行操作文档分层（现行、计划、归档）。

## 9. 隐私风险检查结果

`.gitignore` 检查：
- 已覆盖 `.mhtml/.mht/.html/.jsonl/.log`、`runs/master/handoff/debug/mhtml_archive`、`story_canon.md/clean_corpus.md/removed_meta.md/canon_index.jsonl`、`dist/build/*.zip/*.spec` 等高风险项。

仓库已跟踪文件检查：
- 未发现误提交 `.mhtml`、运行产物目录、私密正文与日志产物。

文档提示：
- README 与 release/troubleshooting 文档已有“不要上传私人故事数据”提醒。

残余风险（流程层）：
- README 中“欢迎提交日志”未明确“请先脱敏”，建议补一句“日志发布前请移除私人故事内容/路径/凭据”。

## 10. 下一步建议路线

### 第一档：止血修复（先做）
- 修复 GUI 关闭窗口时的子进程清理（避免遗留后台任务）。
- 修复 GUI 链式任务状态与按钮解锁时机（摘取 #10 的最小稳定补丁）。
- 统一 Release 口径（workflow / build 脚本 / README / RELEASE 文档）。
- README.md 去乱码并对齐当前真实流程（不改核心逻辑，只改描述）。
- 在隐私章节补“日志与截图提交前请脱敏”。

### 第二档：产品化整理
- 将 GUI 进一步收敛为“故事目录向导”为主，弱化内部术语暴露（clean/absorb/handoff）。
- 增加三种显式操作路径：
  - 追加新窗口
  - 从头重建
  - 只生成 handoff
- CLI 保留专家模式；GUI 面向普通用户，减少概念负担。

### 第三档：正式推广
- 补稳定截图与最短流程 GIF/视频。
- Release 版本节奏固定化（变更摘要模板 + 回归清单）。
- 完整 GitHub Pages 落地（首页、下载、FAQ、隐私提醒）。
- 补仓库 Topics 与示例项目说明，提升可发现性。

---

## 审计执行记录（本次）

- 语法编译检查：`py -3 -m py_compile grok_handoff_gui.py grok_handoff_cli.py grok_i18n.py` 通过。
- CLI 帮助检查：`python grok_handoff_cli.py --help` 通过。
- GUI 点击流：当前环境未进行真实桌面点击回归（仅代码级审计）。
