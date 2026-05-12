# 自动化说明（中文）

## 全自动发布
以后不需要本地打包。流程是：
1. Codex 修改代码并开 PR。
2. 合并 PR 到 main。
3. 打开 GitHub → Actions → Release Windows。
4. 点击 Run workflow。
5. 输入版本号，例如 v0.1.1。
6. Actions 会自动打包 Windows exe、生成 zip、创建 Release、上传资产。

## 自动化合并
- 如果机器人账号有权限，会尝试自动创建 PR、处理冲突重做，并在检查通过后执行 squash merge。
- 如果权限不足，只需要在网页上点击 **Merge pull request**。
