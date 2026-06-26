---
name: upload-skill-to-github
description: Upload a local Claude skill or command to GitHub. Auto-detects whether the target is a command (.claude/commands/) or a skill (.claude/skills/) and routes accordingly. Handles first-time upload and incremental sync.
---

# Upload Skill to GitHub

Upload a local Claude command or skill to GitHub with incremental sync.

## Step 0: Detect type and locate local file

The user invokes this as `/upload-skill-to-github <name>`, or without a name — in that case ask which skill/command to upload.

Check in order:
1. **Command**: `C:\Users\Windows11\.claude\commands\<name>.md` — if exists, type = `command`
2. **Skill**: `C:\Users\Windows11\.claude\skills\<name>\SKILL.md` — if exists, type = `skill`
3. Neither found → tell the user and stop.

---

## If type = command

### Step C1: Check if remote file exists

```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/.claude/commands/<name>.md 2>&1
```

- JSON with `sha` → **incremental sync**
- 404 → **first-time upload**

### Step C2: Upload the command file

**First-time:**
```bash
unset GITHUB_TOKEN
CONTENT=$(base64 -w 0 "C:/Users/Windows11/.claude/commands/<name>.md")
gh api repos/baixian-white/Skills_OF_BaiXian/contents/.claude/commands/<name>.md \
  --method PUT \
  --field message="add <name> command" \
  --field content="$CONTENT" \
  --jq '.content.path'
```

**Incremental:**
```bash
unset GITHUB_TOKEN
SHA=$(gh api repos/baixian-white/Skills_OF_BaiXian/contents/.claude/commands/<name>.md --jq '.sha')
CONTENT=$(base64 -w 0 "C:/Users/Windows11/.claude/commands/<name>.md")
gh api repos/baixian-white/Skills_OF_BaiXian/contents/.claude/commands/<name>.md \
  --method PUT \
  --field message="update <name> command" \
  --field content="$CONTENT" \
  --field sha="$SHA" \
  --jq '.content.path'
```

### Step C3: Confirm
- ✅ Uploaded/updated: link to file on GitHub
- Whether first-time or incremental sync

---

## If type = skill

### Step S1: Read remote repo structure

```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents --jq '.[].name'
```

Show top-level folders, then ask:
> 请问要上传到哪个文件夹？（直接输入文件夹名，或输入 `.` 表示根目录）

Wait for answer. Common answer: `.claude`

### Step S2: Check if skill already exists

```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<name>/SKILL.md 2>&1
```

- JSON with `sha` → **incremental sync**
- 404 → **first-time upload**

### Step S3: Upload SKILL.md

**First-time:**
```bash
unset GITHUB_TOKEN
CONTENT=$(base64 -w 0 "C:/Users/Windows11/.claude/skills/<name>/SKILL.md")
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<name>/SKILL.md \
  --method PUT \
  --field message="add <name> skill" \
  --field content="$CONTENT" \
  --jq '.content.path'
```

**Incremental:**
```bash
unset GITHUB_TOKEN
SHA=$(gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<name>/SKILL.md --jq '.sha')
CONTENT=$(base64 -w 0 "C:/Users/Windows11/.claude/skills/<name>/SKILL.md")
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<name>/SKILL.md \
  --method PUT \
  --field message="update <name> skill" \
  --field content="$CONTENT" \
  --field sha="$SHA" \
  --jq '.content.path'
```

If the skill directory contains additional files beyond `SKILL.md`, upload each one the same way.

### Step S4: Update README.md in the target folder

Fetch current README:
```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/README.md
```

- Exists: decode `content` (base64), append entry, re-upload with existing `sha`
- Not exists: create from scratch

README entry format:
```markdown
### <name>

<one-line description from SKILL.md frontmatter `description:` field>

**调用方式：** `/<name> <参数（如有）>`

**说明：** <brief explanation extracted from SKILL.md>
```

### Step S5: Confirm
- ✅ Uploaded: link to file on GitHub
- ✅ README updated: link to README on GitHub
- Whether first-time or incremental sync

---

## Notes

- Always `unset GITHUB_TOKEN` before every `gh` command — a stale env var blocks keyring auth
- Active account must be `baixian-white`; if not: `gh auth switch --user baixian-white`
- GitHub cannot store empty folders; at minimum one file must exist in the path
- If base64 produces a `\U` unicode warning, it's harmless — content is correct
