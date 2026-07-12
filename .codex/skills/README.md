# Codex Skills

This directory contains reusable Codex skills synced from the local `.codex/skills` tree.

## Skills

### deploy-aliyun

Deploy a local project to the configured Aliyun server, sync gitignored config, pull remote code, run post-deploy commands, verify service health, or update `DEPLOY.md`.

**Invocation:** `$deploy-aliyun`

**Path:** `.codex/skills/deploy-aliyun/`

### env-config-vault

Manage reusable local environment configuration for cloned projects, including `.env` variables, API keys, base URLs, database credentials, tokens, and service settings.

**Invocation:** `$env-config-vault`

**Path:** `.codex/skills/env-config-vault/`

**Safety:** This skill is explicit-invocation only and must not upload or sync local vault data such as `~/.codex/env-config-vault/vault.json`.

### upload-skill-to-github

Upload or sync a local Codex or Claude skill/command to the GitHub repo `baixian-white/Skills_OF_BaiXian`.

**Invocation:** `$upload-skill-to-github`

**Path:** `.codex/skills/upload-skill-to-github/`

**Maintenance:** For Codex skills, also update this `.codex/skills/README.md` index during sync.

### mianyunai-image

Use when generating or editing one or many images through an unstable image API relay, especially when requests intermittently return 520, 524, 429, timeouts, empty data, corrupt images, model-route mismatches, or when a long batch must resume without repeating completed work.

**Invocation:** `$mianyunai-image`

**Path:** `.codex/skills/mianyunai-image/`
