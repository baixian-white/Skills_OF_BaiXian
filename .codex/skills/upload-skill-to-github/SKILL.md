---
name: upload-skill-to-github
description: "Use when the user asks to upload or sync a local Codex or Claude skill/command to the GitHub repo baixian-white/Skills_OF_BaiXian."
metadata:
  short-description: Upload local skills or commands to GitHub
---

# Upload Skill to GitHub

Upload a local Codex skill, Claude skill, or Claude command to GitHub with incremental sync.

## Step 0: Detect type and locate local file

The user asks to upload `<name>`, or asks without a name. If no name is given, ask which skill/command to upload.

Check in order:
1. **Codex skill**: `C:\Users\Windows11\.codex\skills\<name>\SKILL.md` -> type = `codex-skill`
2. **Agents skill**: `C:\Users\Windows11\.agents\skills\<name>\SKILL.md` -> type = `agents-skill`
3. **Claude command**: `C:\Users\Windows11\.claude\commands\<name>.md` -> type = `claude-command`
4. **Claude skill**: `C:\Users\Windows11\.claude\skills\<name>\SKILL.md` -> type = `claude-skill`
5. Neither found -> tell the user and stop.

---

## Destination Layout

Use this repository: `baixian-white/Skills_OF_BaiXian`.

- Codex skill: `.codex/skills/<name>/...`
- Agents skill: `.agents/skills/<name>/...`
- Claude command: `.claude/commands/<name>.md`
- Claude skill: ask user for target folder, with `.claude/skills` as the normal answer.

Upload every non-cache file in a skill directory. Skip `__pycache__`, `.pyc`, `.git`, and obvious build/cache folders.

## If type = claude-command

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
- Uploaded/updated: link to file on GitHub
- Whether first-time or incremental sync

---

## If type = codex-skill or agents-skill

### Step X1: Check if remote skill exists

```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/.codex/skills/<name>/SKILL.md 2>&1
```

For `agents-skill`, replace `.codex/skills` with `.agents/skills`.

- JSON with `sha` -> incremental sync
- 404 -> first-time upload

### Step X2: Upload the whole skill directory

For each file under the local skill directory, upload to the matching remote path. Use GitHub contents API with `sha` when updating existing files.

PowerShell-friendly content encoding:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("<local-file>"))
```

Bash-friendly content encoding:

```bash
base64 -w 0 "<local-file>"
```

For PowerShell uploads of larger files, avoid putting base64 content directly in command-line arguments because Windows command length limits can break `gh.exe`. Write a temporary UTF-8 no-BOM JSON body and call:

```powershell
gh api "repos/baixian-white/Skills_OF_BaiXian/contents/<remote-file>" --method PUT --input <payload.json>
```

Delete the temporary payload after the request.

### Step X3: Update README.md in the skill collection folder

For `codex-skill`, update `.codex/skills/README.md`.

For `agents-skill`, update `.agents/skills/README.md`.

Fetch current README:

```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/.codex/skills/README.md
```

- Exists: decode `content` (base64), add or update the entry for `<name>`, re-upload with existing `sha`.
- Not exists: create from scratch and include all currently visible skills in that collection when practical.

README entry format:

```markdown
### <name>

<one-line description from SKILL.md frontmatter `description:` field>

**Invocation:** `$<name>`

**Path:** `.codex/skills/<name>/`
```

For `agents-skill`, use `.agents/skills/<name>/` as the path. If the skill has special safety constraints, add a short `**Safety:**` line. Do not include local secret files, webhook values, vault data, or private machine paths.

### Step X4: Confirm

- Uploaded/updated skill directory link
- Number of files uploaded
- README updated link
- Whether first-time or incremental sync

---

## If type = claude-skill

### Step S1: Read remote repo structure

```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents --jq '.[].name'
```

Show top-level folders, then ask:
> 请问要上传到哪个文件夹？（直接输入文件夹名，或输入 `.` 表示根目录）

Wait for answer. Common answer after this migration: `.claude/skills`

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
- Uploaded: link to file on GitHub
- README updated: link to README on GitHub
- Whether first-time or incremental sync

---

## Notes

- Always `unset GITHUB_TOKEN` before every `gh` command when using Git Bash or WSL; a stale env var can block keyring auth
- Active account must be `baixian-white`; if not: `gh auth switch --user baixian-white`
- GitHub cannot store empty folders; at minimum one file must exist in the path
- If base64 produces a `\U` unicode warning, it's harmless — content is correct
- Do not upload local webhook/token config files unless the user explicitly confirms. For `feishu-monitor`, do not upload `notify_config.json` by default.
