# Env Config Vault Security Model

## Storage

- Default vault path: `~/.codex/env-config-vault/vault.json`
- Override path with `CODEX_ENV_VAULT_FILE`.
- Secret values are encrypted with Windows DPAPI current-user scope when running on Windows.
- Metadata remains plaintext: variable name, service, kind, tags, aliases, timestamps, masked hint, and project paths.

## Entry Shape

```json
{
  "id": "openai-openai-api-key-a1b2c3d4",
  "name": "OPENAI_API_KEY",
  "service": "openai",
  "kind": "api_key",
  "scope": "global",
  "project": null,
  "aliases": ["OPENAI_KEY"],
  "tags": ["llm"],
  "sensitive": true,
  "masked_value": "sk-...abcd",
  "protected_value": {
    "provider": "windows-dpapi-current-user",
    "ciphertext": "..."
  }
}
```

## Allowed Automation

- Scanning a repo for variable names is safe by default.
- Listing and matching vault entries is safe because only masked values are shown.
- Writing a `.env` is allowed only after user confirmation or a direct user request.
- Importing from an existing `.env` requires explicit confirmation with `--yes`.
- One-time elevated writes are acceptable when local ACLs protect the vault directory.

## Disallowed Automation

- Never silently harvest credentials from a project.
- Never copy provider API keys from global config files into the vault unless the user explicitly asks.
- Never print decrypted values in normal match/list/scan output.
- Never write real secrets to a file that appears tracked or unignored unless the user deliberately overrides with `--allow-unignored`.
- Never loosen permissions on the secret-bearing vault directory merely for convenience.
