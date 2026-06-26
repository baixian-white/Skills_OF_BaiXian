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
### deploy-aliyun

Deploy local code to the Aliyun server (121.196.203.3). Syncs gitignored config/secret files, runs remote git pull, executes post-deploy commands, then verifies the deployment and returns the URL. Uses mcp-ssh-manager for all remote operations.

**调用方式：** `/deploy-aliyun [本地项目目录]`

**说明：** 自动发现远端项目目录，检查配置文件差异（.env等），同步需要补充/修改的配置项，执行 git pull，运行部署命令，最后验证服务状态并返回访问 URL。

### deploy-aliyun

Deploy local code to the Aliyun server (121.196.203.3). Syncs gitignored config/secret files, runs remote git pull, executes post-deploy commands, then verifies the deployment and returns the URL.

**调用方式：** `/deploy-aliyun [本地项目目录]`

**说明：** 自动发现远端项目路径，对比并同步 .env 等配置文件，执行 git pull 和重启服务，最终返回可访问 URL。

### skill-retro

Record lessons learned from a skill execution and update the skill file. Appends UNVERIFIED notes that get verified on next invocation.

**调用方式：** `/skill-retro <skill-name>`

**说明：** 提示用户总结本次 skill 执行中的问题，追加到 skill 文件的 Runtime Notes 区，标记为 UNVERIFIED 供下次验证。
