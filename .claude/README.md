# Claude Skills

本目录存放自定义 Claude Skills，可在任意会话中通过 `/skill-name` 调用。

## Skills 列表

### find-claude-session

搜索本地所有 Claude 历史会话，通过关键词找到过去的对话。

**调用方式：** `/find-claude-session <关键词>`

**示例：**
- `/find-claude-session 内网穿透`
- `/find-claude-session docker deployment`

**说明：** 扫描 `C:\Users\Windows11\.claude\projects\` 下所有 `.jsonl` 会话文件，匹配关键词后提取 ai-title、项目名、会话 ID 和时间戳并展示。

### upload-skill-to-github

将本地 Claude skill 上传到 GitHub 仓库，支持首次上传和增量同步，并自动更新仓库 README。

**调用方式：** `/upload-skill-to-github <skill-name>`

**说明：** 读取远程仓库目录结构，询问上传目标文件夹，检测是首次上传还是增量同步（通过 SHA 判断），上传 SKILL.md 后自动在目标文件夹的 README.md 中追加该 skill 的说明。
