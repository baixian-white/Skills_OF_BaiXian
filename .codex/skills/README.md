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

### creating-ppt-image-prompts

Use when a user provides a PPT outline, report, manuscript, slide list, or presentation content and needs a slide-by-slide image-generation prompt deck, including section pages, consistent style profiles, title/no-title modes, Chinese text controls, layout groups, and batch-generation-ready Markdown.

**Invocation:** `$creating-ppt-image-prompts`

**Path:** `.codex/skills/creating-ppt-image-prompts/`

**Safety:** Preserve generated original images; do not translate, resize, crop, stretch, pad, or extend them. Re-generate noncompliant pages instead.

### image-slides-to-pptx

Use when numbered PNG or JPEG files must be combined into a PowerPoint deck, especially for full-slide image decks, editable title overlays, reusable theme profiles, section decorations, page numbers, 16:9 output, or PPTX integrity and image-mapping verification.

**Invocation:** `$image-slides-to-pptx`

**Path:** `.codex/skills/image-slides-to-pptx/`
