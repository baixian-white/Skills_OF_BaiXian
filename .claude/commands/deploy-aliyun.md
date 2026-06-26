Deploy to Aliyun: sync gitignored config files + remote git pull + post-deploy commands.
The user handles git commit/push themselves before invoking this skill.

## MCP tools available
Use the `ssh-manager` MCP server for all remote operations. Server name: `ALIYUN`.
- Execute commands: `mcp__ssh-manager__execute_command` with `server: "ALIYUN"`
- Upload/sync files: `mcp__ssh-manager__upload_file` or `mcp__ssh-manager__sync_files` with `server: "ALIYUN"`
- Check server health: `mcp__ssh-manager__get_system_info` with `server: "ALIYUN"`

Fall back to raw `ssh aliyun-root "..."` only if MCP tools are unavailable.

## Arguments: $ARGUMENTS
- Optional path token: local project directory (default: cwd)
- Optional remote path: only if user explicitly provides it; otherwise auto-discover (see Step 0)

## Workflow

### Step 0-A — Read deployment document
Check for `DEPLOY.md` in the local project directory:
```
Test-Path <local_dir>/DEPLOY.md
```
- **Found**: Read the file. Use its contents to pre-fill known values (remote path, deploy method, service identifier, post-deploy commands) and skip the corresponding discovery sub-steps. Set `$FIRST_DEPLOY = false`.
- **Not found**: Set `$FIRST_DEPLOY = true`. Proceed through all steps normally — info will be gathered and written at Step 6.

### Step 0.5 — Verify unverified runtime notes (runs once per note, skip if none)
Scan `## Runtime Notes` at the bottom of this file for lines tagged `[UNVERIFIED]`.
If none found, skip this step entirely.

For each `[UNVERIFIED]` note, run its `verify:` command via SSH. Then:
- Issue **confirmed** → change `[UNVERIFIED]` to `[VERIFIED]` in this skill file
- Issue **not reproduced** → delete the note from this skill file entirely

This ensures notes are validated once and never re-tested on future runs.

### Step 0 — auto-discover remote project directory
Get the local repo's git remote URL:
```
git -C <local_dir> remote get-url origin
```
Extract the repo name (last path segment, strip `.git`).

Then search the server for matching git repos:
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="find /root /var/www /home /opt /srv -maxdepth 5 -name '.git' -type d 2>/dev/null | sed 's|/.git$||' | xargs -I{} sh -c 'echo {}; git -C {} remote get-url origin 2>/dev/null'"
```

Match results against the local repo name or remote URL:
- **One match**: tell the user "Found project at `<path>`. Proceeding." and use that path
- **Multiple matches**: list them and ask user to pick
- **No match**: ask user if they want to specify the path manually, or if the project hasn't been cloned yet (offer to clone it)

### Pre-flight check 1 — SSH connectivity
Run: `mcp__ssh-manager__execute_command` with `server: "ALIYUN"`, `command: "echo OK"`

- **Returns "OK"**: proceed
- **Fails**: fall back to `ssh -o ConnectTimeout=10 -o BatchMode=yes aliyun-root "echo OK"` to diagnose.
  - Key missing → show contents of `C:\Users\Windows11\.ssh\id_ed25519_aliyun_root.pub`, guide user to add it to server
  - Unreachable → check network, stop and wait

### Pre-flight check 2 — rsync/sync availability
`mcp__ssh-manager__sync_files` is the primary file sync tool (MCP built-in, no local rsync needed).
If MCP unavailable, check `where.exe rsync`; if missing, offer:
1. `winget install --id GnuWin32.Rsync`
2. Fallback to scp

---

### Step 1 — audit environment-specific config
Find local gitignored config files:
```
git ls-files --others --ignored --exclude-standard
```
Filter: size < 1MB, not node_modules/dist/build/cache, matches `.env*`, `*config*.local*`, `*secret*`, `*.pem`, `*.key`, `local_settings.*`.

For each file, read local contents. Fetch server version via MCP:
```
mcp__ssh-manager__execute_command  server="ALIYUN"  command="cat <remote_dir>/<file> 2>/dev/null || echo __NOT_FOUND__"
```

Present a table to the user:
- **New keys** (local only) → need to add
- **Changed values** (differ between local and server) → may need to update  
- **Server-only keys** → informational, don't touch

Mask secret values as `***`. Ask user which to add/update. Wait for confirmation.

### Step 2 — sync confirmed config files
Use MCP to upload each confirmed file:
```
mcp__ssh-manager__upload_file  server="ALIYUN"  local_path=<file>  remote_path=<remote_dir>/<relative_path>
```
For updating specific keys in an existing file, use MCP execute + sed:
```
mcp__ssh-manager__execute_command  server="ALIYUN"  command="sed -i 's/^KEY=.*/KEY=newvalue/' <remote_file>"
```

### Step 3 — remote git pull
```
mcp__ssh-manager__execute_command  server="ALIYUN"  command="cd <remote_dir> && git pull"
```

### Step 4 — post-deploy commands
Run whatever the conversation specifies (restart service, install deps, migrations, etc.).
Use `mcp__ssh-manager__execute_command` for each command.
If not specified, ask the user.

### Step 5 — verify deployment & return URL

**Check service is actually running:**
Detect the process manager from conversation context or by probing:
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="systemctl is-active <service> 2>/dev/null || pm2 list 2>/dev/null || docker ps 2>/dev/null"
```

**Detect listening port:**
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="ss -tlnp | grep -E 'LISTEN' | grep -v '127.0.0.1'"
```

**Check if a domain is configured** (nginx/caddy/apache vhost):
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="grep -r 'server_name\|ServerName' /etc/nginx/sites-enabled /etc/nginx/conf.d /etc/apache2/sites-enabled 2>/dev/null | grep -v '#'"
```

**Hit the URL to confirm it responds:**
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="curl -s -o /dev/null -w '%{http_code}' <url> --max-time 10"
```

**Return to user:**
- ✅ Service status (running / not running)
- 🌐 URL: domain if found, otherwise `http://121.196.203.3:<port>`
- HTTP status code from the curl check (200 = healthy)
- If service is not running or curl fails → show the last 20 lines of logs and suggest a fix:
  ```
  mcp__ssh-manager__execute_command  server="ALIYUN"
    command="journalctl -u <service> -n 20 --no-pager 2>/dev/null || pm2 logs --lines 20 2>/dev/null"
  ```

### Step 6 — Update and sync DEPLOY.md

**If `$FIRST_DEPLOY = true`:**
Generate `DEPLOY.md` from the template at the bottom of this file, filling in all info collected during this run. Write to `<local_dir>/DEPLOY.md`.

**If `$FIRST_DEPLOY = false`:**
Append a new row to `## Deployment History` in the existing `DEPLOY.md`:
```
| <YYYY-MM-DD> | <git rev-parse --short HEAD> | <git config user.name> | <brief notes or "routine deploy"> |
```
Keep at most 20 rows; drop the oldest if exceeded.

**Both cases — sync to server:**
```
mcp__ssh-manager__upload_file  server="ALIYUN"  local_path=<local_dir>/DEPLOY.md  remote_path=<remote_dir>/DEPLOY.md
```

### On any error — classify and record

When any step fails or produces unexpected behavior, before retrying:

1. **Diagnose** the root cause from error output.
2. **Classify**:
   - **Server-level** — affects any project on this server (HIDS blocking, OS quirks, container runtime behavior, network). Add a new `[UNVERIFIED]` line to `## Runtime Notes` in **this skill file** with a `verify:` command. It will be auto-validated on the next run via Step 0.5.
   - **Project-level** — specific to this codebase (startup crash, bad env var, migration failure, config mismatch). Add a row to `## Known Issues` in **DEPLOY.md**. Step 6 will sync it to the server.
3. **Resolve** and continue deployment.

---

## Runtime Notes
<!-- Updated by /skill-retro. Most recent first. -->

### 2026-06-25 — trustailab-reimbursement (121.196.203.3)
- [VERIFIED] **SSH drops compound commands** (`;` `&&` `|`) → AliYunDun HIDS agent detects shell metacharacters as command injection and kills the session. Wrap all multi-step logic in `bash -c '...'` as a single SSH call | verify: `ssh aliyun-root "echo a && echo b"` fails; `ssh aliyun-root "bash -c 'echo a && echo b'"` succeeds
- [VERIFIED] **Server uses Podman not Docker** (121.196.203.3, v4.9.4-rhel) → `docker` is an alias for podman on this specific instance. Always detect first: `docker info 2>&1 | grep -i podman`. If podman: use `podman` commands directly; `podman-compose up -d` does NOT auto-replace running containers — use `podman kill + rm + run` manually
- [VERIFIED] **podman container name conflict on re-deploy** → container `trustailab-reimbursement_app_1` stays running; use `podman restart <name>` for incremental deploy (kill+rm only needed for full rebuild)
- [VERIFIED] **pip slow (no mirror)** → Dockerfile line 4 has no `-i` mirror; add `-i https://mirrors.aliyun.com/pypi/simple/` to speed up image rebuilds
- [VERIFIED] **podman restart SIGTERM timeout** → container ignores SIGTERM, SIGKILL after 10s; add `stop_signal: SIGKILL` or `stop_grace_period: 1s` to docker-compose.yml | verify: `ssh aliyun-root "bash -c 'podman restart trustailab-reimbursement_app_1'"` and check for SIGTERM warning

---

## DEPLOY.md Template
Use this template on first deploy. Fill all fields from info gathered during this run.

```markdown
# Deployment Record — <project-name>

## Project
- **Repo**: <git remote URL>
- **Local path**: <local dir>
- **Remote path**: <server path>
- **Server**: <IP>

## Runtime Environment
- **OS**: <uname -r>
- **Deploy method**: <podman-compose / docker-compose / systemd / pm2 / bare-process / static>
- **Service identifier**: <container name / unit name / pm2 app name>
- **Config file**: <compose / service / ecosystem file path>

## Ports & URLs
- **Port**: <internal port>
- **URL**: <public URL>
- **Reverse proxy config**: <path, or N/A>

## Config Files
| File | Last synced | Keys (no values) |
|------|-------------|-----------------|

## Post-Deploy Commands
1. <command>

## Known Issues
| Date | Description | Resolution |
|------|-------------|------------|

## Deployment History
| Date | Commit | Deployer | Notes |
|------|--------|----------|-------|
| <date> | <hash> | <name> | Initial deploy |
```
