# 工作流说明

## 文字流程图

```text
.mhtml
  ↓
v6 清洗
  ↓
run/story_canon.md
  ↓
v3.5 吸收
  ↓
master
  ↓
handoff
  ↓
下个 Grok 窗口
```

更完整一点：

```text
Grok 当前窗口
  ↓ 保存为 .mhtml
grok_mhtml_bible_pipeline_v6.py
  ↓ 生成 run 目录
runs/<窗口名>/story_canon.md
  ↓
grok_story_handoff_manager_v3_5_checkpoint_bible.py --absorb
  ↓
master/ 长期正史与设定
  ↓
grok_story_handoff_manager_v3_5_checkpoint_bible.py --handoff
  ↓
handoff/ 给下个窗口复制的投喂包
```

## 面包工坊解释

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

## 每一步做什么

### 1. .mhtml -> v6 清洗

v6 脚本读取浏览器保存的 `.mhtml`，抽取用户和 Grok 的对话内容，生成清洗后的语料和小说正文。

主要输出：

- `clean_corpus.md`
- `raw_messages.jsonl`
- `user_only.txt`
- `assistant_only.txt`
- `story_canon.md`
- `removed_meta.md`
- `canon_index.jsonl`

### 2. run/story_canon.md -> v3.5 吸收

v3.5 脚本读取一个已经跑好的 run 目录，把这次窗口的新正文吸收到项目 `master/` 中。

它会尽量判断：

- 新窗口是否只是续写。
- 是否需要替换旧正文尾巴。
- 是否有新的设定或废稿需要处理。
- 当前故事状态应该怎样交给下一个窗口。

### 3. master -> handoff

当 `master/` 更新后，v3.5 可以生成 `handoff/` 目录。这个目录里的文件就是给下一个 Grok 窗口使用的投喂包。

推荐结构：

- 完整正文 = `master/01_当前正史正文.md`
- 压缩设定 = `master/02_当前设定状态.md`
- 最近正文 = `handoff/02_最近正文_喂给Grok.md`
- 直接投喂 = `handoff/03_下个窗口直接复制这个.md`

总正文适合给人读，不适合每次完整塞给模型。长期写作时，使用 compressed bible + recent story + next direction 更稳。

## 为什么要中间结果落盘

长任务不要只存在内存里。v3.5 的 checkpoint/deep bible 流程会把 chunk 提取、栏目合并、中间草稿写到：

- `debug/init_bible_cache_v3_5/`
- `debug/init_bible_sections_v3_5/`

如果中途失败，用户可以检查这些中间文件，定位是哪一块、哪一栏出问题，也可以在后续版本里复用部分结果，避免从头重跑。

## 推荐目录

```text
D:\Grok
  工具代码

D:\Grok_Project
  runs/
  master/
  handoff/
  debug/
  mhtml_archive/
```

工具代码和故事数据建议分开，这样发布代码时更不容易把私密故事一起传上去。

## 参数位置

GUI 第一版暴露：

- `.mhtml` 文件
- `project_dir`
- LM Studio Base URL
- 模型名
- `canon_part_chars`

CLI 可使用：

```powershell
python grok_handoff_cli.py clean --input "D:\path\story.mhtml" --output "D:\Grok_Project\runs\story_run" --canon-part-chars 12000
python grok_handoff_cli.py absorb-run --run-dir "D:\Grok_Project\runs\story_run" --project-dir "D:\Grok_Project"
python grok_handoff_cli.py handoff --project-dir "D:\Grok_Project"
```
