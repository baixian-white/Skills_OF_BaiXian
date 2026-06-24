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
