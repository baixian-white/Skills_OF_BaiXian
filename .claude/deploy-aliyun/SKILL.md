---
name: deploy-aliyun
description: Deploy local code to the Aliyun server (121.196.203.3). Syncs gitignored config/secret files, runs remote git pull, executes post-deploy commands, then verifies the deployment and returns the URL. Uses mcp-ssh-manager for all remote operations.
---

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
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="systemctl is-active <service> 2>/dev/null || pm2 list 2>/dev/null || docker ps 2>/dev/null"
```

**Detect listening port:**
```
mcp__ssh-manager__execute_command  server="ALIYUN"
  command="ss -tlnp | grep LISTEN | grep -v '127.0.0.1'"
```

**Check if a domain is configured:**
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
- HTTP status code (200 = healthy)
- If not running or curl fails → show last 20 lines of logs:
  ```
  mcp__ssh-manager__execute_command  server="ALIYUN"
    command="journalctl -u <service> -n 20 --no-pager 2>/dev/null || pm2 logs --lines 20 2>/dev/null"
  ```
