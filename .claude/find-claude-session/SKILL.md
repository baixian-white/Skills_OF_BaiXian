---
name: find-claude-session
description: Search across all local Claude conversation sessions by keyword and return matching sessions with their titles, project names, session IDs, and timestamps. Use when the user wants to find a past conversation or session about a specific topic, tool, or task.
---

# Find Claude Session

Search local Claude session history to find past conversations matching a keyword or topic.

## Input

The user provides one or more search keywords after the slash command, e.g.:
- `/find-claude-session 内网穿透`
- `/find-claude-session frp ngrok`
- `/find-claude-session docker deployment`

If no keywords are provided, ask the user what topic they're looking for.

## Steps

### 1. Keyword search across all session files

Use Grep to search all `.jsonl` files under `C:\Users\Windows11\.claude\projects\`:

- Pattern: the user's keywords (use `|` to combine multiple terms, e.g. `keyword1|keyword2`)
- Glob: `**/*.jsonl`
- Output mode: `files_with_matches`
- This gives you the list of session files that contain the keywords

### 2. Extract ai-title from matching files

For each matching file, use Grep again to extract the `ai-title` field:

- Pattern: `"type":"ai-title"`
- Output mode: `content`
- Limit to first 2 matches per file (titles are usually recorded twice — dedup them)

The `ai-title` entry looks like:
```json
{"type":"ai-title","aiTitle":"搭建内网穿透实现 SSH 远程","sessionId":"..."}
```

### 3. Parse and present results

From each match extract:
- **Project name**: the directory segment after `projects\`, e.g. `e--CODE-SSH-BAIXIAN` → readable as `SSH-BAIXIAN`
- **Session ID**: the `.jsonl` filename without extension, e.g. `6a818a0d-246b-46f6-b9e7-35fb6c5edc21`
- **AI Title**: the `aiTitle` value — this is the best human-readable summary
- **Timestamp**: from `"timestamp":"..."` near the top of the file (use Grep with pattern `"timestamp"` and limit 1)

### 4. Output format

Present results as a table or list:

```
找到 N 个相关会话：

1. **<AI Title>**
   项目: <project-name>
   会话 ID: <session-id>
   时间: <timestamp>
   文件: C:\Users\Windows11\.claude\projects\<path>\<session-id>.jsonl

2. ...
```

If no matches are found, tell the user and suggest alternative keywords.

## Notes

- Prioritize files with `"type":"ai-title"` containing the keywords — these are exact title matches, highest relevance
- The projects directory is always `C:\Users\Windows11\.claude\projects\`
- Subagent workflow files (under `subagents\` subdirectories) are usually not top-level sessions — prefer `.jsonl` files directly under the project directory
- If there are many results, sort by recency (timestamp descending) and show top 10
