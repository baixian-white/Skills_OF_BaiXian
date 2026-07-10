---
name: reliable-batch-image-generation
description: "Use when generating one or many images through an unstable OpenAI-compatible gpt-image endpoint, especially when requests intermittently return 520, 524, 429, timeouts, empty data, corrupt PNGs, or when a long batch must resume without regenerating completed images."
---

# Reliable Batch Image Generation

## Overview

Use the bundled executor for every image request. It retries transient gateway failures, validates the returned PNG, saves atomically, and resumes batch manifests. External outages or insufficient quota cannot be guaranteed away; never report success until a verified image exists.

## Required Workflow

1. Use scripts/reliable_image.py with an absolute path.
2. Use /images/generations through the configured base URL; do not improvise with /chat/completions.
3. Default to max-attempts 10 and timeout 300 for unstable relays.
4. For multiple images, create a JSONL manifest and use batch resume behavior.
5. Treat only a validated PNG as success. HTTP 200, empty messages, and acknowledgements are not images.
6. If the script reports quota, authentication, or model errors, stop and report the exact non-secret reason.

## Commands

Single image:

```powershell
python "<SKILL_DIR>\scripts\reliable_image.py" --config "<SKILL_DIR>\config.json" generate --prompt "professional banking AI training illustration, no text" --out ".\bank-ai.png" --max-attempts 10 --timeout 300
```

Batch:

```powershell
python "<SKILL_DIR>\scripts\reliable_image.py" --config "<SKILL_DIR>\config.json" batch --manifest ".\image-tasks.jsonl" --output-dir ".\generated-images" --max-attempts 10 --timeout 300
```

Manifest, one JSON object per line:

```json
{"id":"cover","prompt":"16:9 banking AI training cover, no text","out":"01-cover.png","size":"1536x1024"}
{"id":"risk","prompt":"bank employee verifying a suspicious call, no text","out":"02-risk.png"}
```

## Configuration

Copy config.example.json to config.json. Never print, log, or commit the API key. Environment variables IMAGE_API_KEY, IMAGE_API_BASE_URL, and IMAGE_API_MODEL are also supported.

## Retry Rules

| Result | Action |
|---|---|
| 408, 429, 5xx, 520-524, network timeout | Retry with backoff |
| Missing or invalid Base64, invalid PNG | Retry |
| Valid PNG | Atomically save and mark success |
| Insufficient quota, invalid key, model not found | Stop immediately |
| Existing valid output during batch rerun | Skip |

## Output Evidence

- Single generation prints verified dimensions, byte count, path, and attempts.
- Batch generation writes image-generation-ledger.jsonl and image-generation-summary.json.
- Re-running the same batch skips valid completed PNGs and continues unfinished tasks.

## Common Mistakes

- Increasing client timeout does not extend a Cloudflare 524 gateway threshold; retries are the recovery mechanism.
- Do not use model spelling gpt-iamge-2; the correct default is gpt-image-2.
- Do not delete successful images before retrying a failed batch.
- Do not claim guaranteed success when quota or the upstream service is unavailable.
