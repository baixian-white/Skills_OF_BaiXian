---
name: env-config-vault
description: "Use when starting or configuring a cloned project that needs environment variables, .env files, API keys, base URLs, database credentials, tokens, secrets, or reusable local service configuration across repositories."
---

# Env Config Vault

## Overview

Use this skill to avoid rediscovering the same local environment settings across projects. Keep reusable config in the local vault, scan a repo for required environment variables, match saved entries, and write project-local `.env` files without printing secret values.

This skill is explicit-invocation only. Use it when the user names `$env-config-vault` or directly asks to use the env config vault; do not rely on implicit loading for generic project setup.

The vault lives under `~/.codex/env-config-vault/` by default. Values are protected with the current Windows user DPAPI when available.

## Default Workflow

1. Inspect the new repo for env requirements:
   `python ~/.codex/skills/env-config-vault/scripts/env_vault.py scan <project>`
2. Match required names against saved entries:
   `python ~/.codex/skills/env-config-vault/scripts/env_vault.py match <project>`
3. If values are already in the vault, ask before writing a real `.env`:
   `python ~/.codex/skills/env-config-vault/scripts/env_vault.py write-env <project> --out <project>/.env --yes`
4. If values exist in a trusted local `.env`, import them only after explicit user confirmation:
   `python ~/.codex/skills/env-config-vault/scripts/env_vault.py import-dotenv <file> --service <name> --project <project> --yes`
5. If values are not on disk, ask the user for the missing values or tell them exactly which variables are missing. Do not invent placeholder credentials.

## Safety Rules

- Do not auto-import secrets from a repo, config file, chat history, shell history, or system config without explicit user confirmation.
- Do not print raw secrets unless the user explicitly asks to reveal a specific entry.
- Prefer `write-env` over `get --reveal`; it writes decrypted values to the target file without echoing them.
- Before writing real secrets, check that the output file is ignored by git. The script refuses unignored secret `.env` writes unless `--allow-unignored` is deliberately passed.
- Do not commit the vault directory, `.env`, database passwords, API keys, or webhook URLs.
- If local ACLs block writes to the secret-bearing vault directory, request one explicit write approval for that operation. Do not broaden vault directory permissions unless the user explicitly approves that security tradeoff.

## Common Commands

```powershell
# Create or inspect the vault file.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py init

# Scan a repo for env variable names.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py scan H:\H-CODE\some-project

# Add one value. Use --prompt in a real terminal when possible.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py add --name OPENAI_API_KEY --service openai --kind api_key --prompt

# Import an existing trusted dotenv file after user confirmation.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py import-dotenv H:\H-CODE\some-project\.env --service project-name --project H:\H-CODE\some-project --yes

# List masked entries.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py list

# Match a repo's required variables to saved entries.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py match H:\H-CODE\some-project

# Write a real .env from exact, unambiguous matches.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py write-env H:\H-CODE\some-project --out H:\H-CODE\some-project\.env --yes

# Write a placeholder example file.
python C:\Users\Windows11\.codex\skills\env-config-vault\scripts\env_vault.py write-env H:\H-CODE\some-project --out H:\H-CODE\some-project\.env.example --mode example --overwrite
```

## Matching Guidance

Exact variable-name matches are safest. When several saved entries match the same variable, use `--service`, add aliases, or ask the user which entry should be used.

Read `references/security-model.md` before changing storage behavior, adding auto-import behavior, or exposing decrypted values.
