---
name: upload-skill-to-github
description: Upload a local Claude skill to a GitHub repository. Handles first-time upload and incremental sync. Use when the user wants to publish or sync a skill from their local .claude/skills/ directory to GitHub.
---

# Upload Skill to GitHub

Upload a local Claude skill directory to GitHub, then update the repo's README with the skill description.

## Step 0: Get skill name

The user invokes this as `/upload-skill-to-github <skill-name>`, or they may just say "upload this skill" — in that case ask which skill they want to upload.

Local skill path: `C:\Users\Windows11\.claude\skills\<skill-name>\`

Verify the local skill exists by reading its `SKILL.md`. If not found, tell the user and stop.

## Step 1: Read remote repo structure

Run:
```
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents --jq '.[].name'
```

Show the user the top-level folders in the repo, then ask:
> 请问要上传到哪个文件夹？（直接输入文件夹名，或输入 `.` 表示根目录）

Wait for the user's answer before continuing. Common answer: `.claude`

## Step 2: Check if skill already exists (first-time vs incremental)

Check whether the target path already exists on GitHub:
```
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<skill-name>/SKILL.md 2>&1
```

- If it returns a JSON object with a `sha` field → **incremental sync** (file exists, need SHA to update)
- If it returns a 404 error → **first-time upload**

## Step 3: Upload SKILL.md

Read the local file and base64-encode it, then call the GitHub Contents API.

**First-time upload:**
```bash
unset GITHUB_TOKEN
CONTENT=$(base64 -w 0 "C:\Users\Windows11\.claude\skills\<skill-name>\SKILL.md")
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<skill-name>/SKILL.md \
  --method PUT \
  --field message="add <skill-name> skill" \
  --field content="$CONTENT" \
  --jq '.content.path'
```

**Incremental sync** (include the existing file's SHA):
```bash
unset GITHUB_TOKEN
SHA=$(gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<skill-name>/SKILL.md --jq '.sha')
CONTENT=$(base64 -w 0 "C:\Users\Windows11\.claude\skills\<skill-name>\SKILL.md")
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/<skill-name>/SKILL.md \
  --method PUT \
  --field message="update <skill-name> skill" \
  --field content="$CONTENT" \
  --field sha="$SHA" \
  --jq '.content.path'
```

If the skill directory contains additional files beyond `SKILL.md` (e.g., reference docs, scripts), upload each one the same way.

## Step 4: Update README.md in the target folder

Fetch the current README:
```bash
unset GITHUB_TOKEN
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/README.md
```

- If it exists: decode the `content` field (base64), append the new skill entry, re-upload with the existing `sha`.
- If it doesn't exist: create it from scratch.

README entry format to append:
```markdown
### <skill-name>

<one-line description from the skill's frontmatter `description:` field>

**调用方式：** `/<skill-name> <参数（如有）>`

**说明：** <brief explanation of what the skill does, extracted from the SKILL.md>
```

Upload the updated README:
```bash
unset GITHUB_TOKEN
README_CONTENT=$(echo "<updated content>" | base64 -w 0)
gh api repos/baixian-white/Skills_OF_BaiXian/contents/<target-folder>/README.md \
  --method PUT \
  --field message="update README for <skill-name>" \
  --field content="$README_CONTENT" \
  --field sha="<existing-sha-or-omit-if-new>" \
  --jq '.content.path'
```

## Step 5: Confirm

Tell the user:
- ✅ Uploaded: link to the file on GitHub
- ✅ README updated: link to the README on GitHub
- Whether it was a first-time upload or a sync

## Notes

- Always `unset GITHUB_TOKEN` before every `gh` command — a stale env var will block keyring auth
- Active account must be `baixian-white`; if not, run `gh auth switch --user baixian-white` first
- GitHub cannot store empty folders; at minimum `SKILL.md` must exist
- If base64 encoding produces a warning about `\U` (unicode), it's harmless — the content is still correct
