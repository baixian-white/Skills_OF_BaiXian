---
name: mianyunai-image
description: "Use when generating or editing one or many images through an unstable image API relay, especially when requests intermittently return 520, 524, 429, timeouts, empty data, corrupt images, model-route mismatches, or when a long batch must resume without repeating completed work."
---

# MianyunAI Image

## Overview

Use the bundled executor for every image generation or image-plus-prompt edit. It retries transient gateway failures, fully decodes returned PNG/JPEG/WebP data with Pillow, saves atomically, and resumes batch manifests. External outages or insufficient quota cannot be guaranteed away; never report success until a verified image exists.

## Required Workflow

1. Use `scripts/reliable_image.py` for OpenAI-compatible image routes and `scripts/native_gemini_probe.py` only for the tested Gemini native generation route, always with an absolute path.
2. Use `/images/generations` for OpenAI-compatible generation, `/images/edits` for image-plus-prompt editing, and the documented Gemini native route below when required; do not improvise with `/chat/completions`.
3. Default to max-attempts 10 and timeout 300 for unstable relays.
4. For multiple generation or edit tasks, create a JSONL manifest and use batch resume behavior.
5. Treat only a fully decoded image in the requested format as success. HTTP 200, empty messages, and acknowledgements are not images.
6. If the script reports quota, authentication, or model errors, stop and report the exact non-secret reason.
7. Do not crop or resize generated images. Deliver the validated original image at its returned dimensions and report the actual width and height.

## Required Model Selection

At skill invocation, before the final parameter confirmation, ask the user which model to use. Do not select a model silently, infer it from the requested resolution or prompt, or rely on the model stored in `config.json`. If the user already named an exact model in the current request, treat that as their selection, but still restate it in the final confirmation.

Present the relevant synchronous choices with their verified constraints:

| Model | Use and current evidence |
|---|---|
| `gpt-image-2` | OpenAI-compatible generation and edit executor; most thoroughly tested, including the 24-case size matrix |
| `gpt-image-2-4k` | Fixed 4K generation SKU; requires a 4K request size plus `quality=high`; the latest correctly configured test ended in three 524 timeouts |
| `gemini-3-pro-image-preview` | Gemini native generation route; verified 1K output; higher displayed price and slower observed response |
| `gemini-3.1-flash-image-preview` | Gemini native generation route; verified 1K output; lower displayed price and faster observed response |

Do not show `gpt-image-2-async` or `gpt-image-2-4k-async` in the default selection list. Offer them only when the user explicitly asks for asynchronous submission or polling. For image-plus-prompt editing, explain that `gpt-image-2` is the conservative recommendation but its live upload path is not yet verified; ask for the model choice rather than applying that recommendation automatically. Never fall back to a different model after rejection or timeout without a fresh model selection and parameter confirmation.

## Explicit Parameter Confirmation

Before invoking the executor, present one complete parameter summary and wait for an affirmative response. Do not send any image-generation request until the user explicitly confirms, even when the user already supplied every value earlier in the conversation. Apply the same confirmation requirement to image-editing requests.

The confirmation must state:

- Model: the exact model identifier.
- API route and calling mode: OpenAI-compatible generation/editing or Gemini native generation; synchronous or asynchronous.
- Prompt: the exact generation prompt or edit instruction.
- Resolution tier: `1K`, `2K`, `4K`, `auto`, or custom.
- Aspect ratio: `1:1`, `3:2`, `2:3`, `16:9`, `9:16`, `4:3`, `3:4`, `21:9`, or custom.
- API request size: the exact `WIDTHxHEIGHT` derived from the website mapping below.
- `quality`: `auto / low / medium / high / standard`; note when the selected native route does not expose this field.
- `style`: normally `vivid` on this relay unless another observed value is deliberately selected.
- `output_format`: `png / jpeg / webp`, including the default-relay format warning below.
- `moderation`: `auto / low`.
- Quantity: the number of one-image requests or manifest rows.
- Delivery rule: preserve the returned file, do not crop or resize it, and report the actual dimensions.

For editing, also confirm the exact image paths, the order of all input images, whether an optional mask is supplied, the exact mask path, and that local images are uploaded to the configured third-party API. Do not treat permission to inspect a local image as permission to upload it.

Label website dimensions as request values, never as guaranteed output dimensions. When a matching live observation exists, show it separately as `Historical observed actual` with the test date and state that the next response may differ. One explicit confirmation covers unchanged retries and resume runs; any parameter change requires confirmation again.

## Commands

Single image:

```powershell
python "<SKILL_DIR>\scripts\reliable_image.py" --config "<SKILL_DIR>\config.json" generate --prompt "professional banking AI training illustration, no text" --out ".\bank-ai.png" --size "1280x720" --quality auto --output-format png --moderation auto --max-attempts 10 --timeout 300
```

Gemini native generation, used only after confirming that `/images/generations` rejects the selected Gemini model:

```powershell
python "<SKILL_DIR>\scripts\native_gemini_probe.py" --config "<SKILL_DIR>\config.json" --model "gemini-3.1-flash-image-preview" --prompt "a matte red ceramic cube on a light gray studio background, no text" --out ".\gemini-cube.png" --aspect-ratio "1:1" --image-size "1K" --timeout 300
```

Image plus prompt edit; repeat `--image` to preserve input order and omit `--mask` when no mask is needed:

```powershell
python "<SKILL_DIR>\scripts\reliable_image.py" --config "<SKILL_DIR>\config.json" edit --prompt "change the red cube to cobalt blue; preserve composition; no text" --image ".\source.png" --image ".\reference.jpg" --mask ".\mask.png" --out ".\edited.png" --model "gpt-image-2" --size "1024x1024" --quality low --style vivid --output-format png --moderation auto --max-attempts 10 --timeout 300
```

Batch:

```powershell
python "<SKILL_DIR>\scripts\reliable_image.py" --config "<SKILL_DIR>\config.json" batch --manifest ".\image-tasks.jsonl" --output-dir ".\generated-images" --max-attempts 10 --timeout 300
```

Manifest, one JSON object per line:

```json
{"id":"cover","prompt":"16:9 banking AI training cover, no text","out":"01-cover.png","size":"1280x720","quality":"high","output_format":"png","moderation":"auto"}
{"id":"edit-cube","prompt":"change the red cube to cobalt blue; preserve composition; no text","images":["inputs/source.png","inputs/reference.jpg"],"mask":"inputs/mask.png","out":"02-edited.png","model":"gpt-image-2","size":"1024x1024","quality":"low","output_format":"png","moderation":"auto"}
```

An edit task is selected when a manifest row contains `images` or the singular `image` alias. Input image and mask paths are resolved relative to the manifest file; `out` remains relative to `--output-dir`.

## Configuration

Copy config.example.json to config.json. Never print, log, or commit the API key. Environment variables IMAGE_API_KEY, IMAGE_API_BASE_URL, and IMAGE_API_MODEL are also supported.

Pillow is required for full PNG/JPEG/WebP decoding and transparency evidence. The tested workspace uses Pillow 12.1.1.

## Live API Parameters

Chrome network capture against `image.mianyunai.com` on 2026-07-12 confirmed this relay request surface:

| Capability | Executor field | Observed values |
|---|---|---|
| Requested dimensions | `size` | `auto` or `WIDTHxHEIGHT` |
| Quality | `quality` | `auto / low / medium / high`; legacy `standard` remains accepted by this relay |
| Encoded image format | `output_format` | `png / jpeg / webp` |
| Moderation | `moderation` | `auto / low` |
| Number of outputs | manifest rows | Keep one request per row; the website does not send `n` when quantity is 1 |
| Response transport | fixed by executor | `response_format: b64_json`; the website instead uses `stream: true` SSE |

The website exposes `1K / 2K / 4K` resolution tiers and maps each tier-plus-ratio choice to the API request sizes in the full matrix below. These remain requested sizes, not guaranteed returned dimensions.

The same pricing page listed these image model identifiers on 2026-07-12. This is a dated availability and price snapshot, not proof that every model supports `/images/edits` or the same parameters:

| Model | Displayed price per request |
|---|---:|
| `gpt-image-2` | `$0.06` |
| `gpt-image-2-async` | `$0.06` |
| `gpt-image-2-4k` | `$0.20` |
| `gpt-image-2-4k-async` | `$0.20` |
| `gemini-3-pro-image-preview` | `$0.20` |
| `gemini-3.1-flash-image-preview` | `$0.15` |

## Model-Specific Generation Routes

Live tests on 2026-07-12 established that the pricing-page model list does not imply one shared generation endpoint. The pricing dialog shows a generic `/chat/completions` example even for image models; do not use that example as evidence of the actual image route.

| Model | Tested route and parameters | Verified result |
|---|---|---|
| `gpt-image-2` | `/images/generations`; full matrix below | 24/24 generation requests succeeded |
| `gpt-image-2-4k` | `/images/generations`; 1:1 requires `size=2880x2880` and `quality=high` | Relay identified a `fixed 4K SKU`; the correctly configured request received three 524 gateway timeouts, so no image or actual dimensions were verified |
| `gemini-3-pro-image-preview` | `/v1beta/models/{model}:generateContent`; `ResponseModalities=["IMAGE"]`, `imageSize=1K`, `aspectRatio=1:1` | Returned a fully decoded 1024x1024 PNG, 1,314,944 bytes |
| `gemini-3.1-flash-image-preview` | `/v1beta/models/{model}:generateContent`; `ResponseModalities=["IMAGE"]`, `imageSize=1K`, `aspectRatio=1:1` | Returned a fully decoded 1024x1024 PNG, 1,320,148 bytes |

The two Gemini models rejected OpenAI-compatible `/images/generations` with `not supported model for image generation, only imagen models are supported`. Use `native_gemini_probe.py` for these model identifiers instead. The helper follows the pricing page's native endpoint, reads the key from the existing config without printing it, extracts `inlineData`, fully decodes the image with Pillow, saves atomically, and reports the actual format and dimensions. It does not currently provide JSONL batch or edit support.

For `gpt-image-2-4k`, the relay rejected `size=1024x1024` as a 1K request and separately rejected `quality=low` as requesting 1K. Treat `size` and `quality` as coupled SKU selectors for this model. A 524 after these validation errors are resolved is still a transient gateway failure, not evidence that a 4K image was generated.

## Image + Prompt Editing

The `edit` command sends `multipart/form-data` to `/images/edits`. Each repeated `--image` is uploaded in order as `image[]`; an optional mask is uploaded as `mask`. The executor fully decodes every local input before any request and rejects a mask whose dimensions differ from the first input image. It accepts either `b64_json` or URL response transport, validates the returned encoding and pixels, then atomically saves the original returned file without cropping or resizing.

This is an actual file upload. Local images are uploaded to the configured third-party API, so confirm the exact image paths and upload consent immediately before the request. Never upload additional nearby files, inferred references, or an optional mask that was not named in the confirmation.

Recommend `gpt-image-2` conservatively when the user asks for guidance, but do not select it silently. No model has yet been live-tested on `/images/edits`. A model appearing on the pricing page or succeeding on a generation route does not establish image-edit support. Report an endpoint or model rejection exactly and do not silently fall back to another model.

On 2026-07-12, the default relay accepted `output_format: webp` with `response_format: b64_json`, but a live request that requested WebP returned PNG bytes. A follow-up `URL + WebP` request also returned PNG bytes: a 1254x1254 RGB image. The mismatch therefore affects both tested response transports. This is a deterministic provider-format mismatch, not transient image corruption: do not retry. Stop after the first response, report the requested and returned formats, and do not save PNG bytes under a `.webp` name.

## Size and Aspect-Ratio Behavior

Treat `size` as a requested aspect ratio and output tier, not a guaranteed PNG pixel size. Always use the verified dimensions printed by the script as the source of truth. The delivery artifact is the validated original PNG returned by the provider; do not crop, resize, stretch, pad, or otherwise rewrite it to imitate the requested dimensions. Clearly report both the requested size and the actual returned width and height.

The default `mianyunai.com` relay with `gpt-image-2` was comprehensively live-tested on 2026-07-12 using `quality=low`, `output_format=png`, `moderation=auto`, and one image per case. All 24/24 tier-ratio combinations succeeded. In 21/24 cases, the returned dimensions differed from the website request size.

| Resolution tier | Aspect ratio | API request size | Historical observed actual | Ratio error |
|---|---:|---:|---:|---:|
| 1K | 1:1 | 1024x1024 | 1254x1254 | 0.000% |
| 1K | 3:2 | 1536x1024 | 1536x1024 | 0.000% |
| 1K | 2:3 | 1024x1536 | 1024x1536 | 0.000% |
| 1K | 16:9 | 1280x720 | 1672x941 | 0.053% |
| 1K | 9:16 | 720x1280 | 941x1672 | 0.053% |
| 1K | 4:3 | 1024x768 | 1448x1086 | 0.000% |
| 1K | 3:4 | 768x1024 | 1086x1448 | 0.000% |
| 1K | 21:9 | 1280x544 | 1923x818 | 0.751% |
| 2K | 1:1 | 2048x2048 | 1254x1254 | 0.000% |
| 2K | 3:2 | 2160x1440 | 1536x1024 | 0.000% |
| 2K | 2:3 | 1440x2160 | 1023x1537 | 0.163% |
| 2K | 16:9 | 2560x1440 | 1672x941 | 0.053% |
| 2K | 9:16 | 1440x2560 | 1440x2560 | 0.000% |
| 2K | 4:3 | 2048x1536 | 1448x1086 | 0.000% |
| 2K | 3:4 | 1536x2048 | 1086x1448 | 0.000% |
| 2K | 21:9 | 2560x1088 | 1923x818 | 0.751% |
| 4K | 1:1 | 2880x2880 | 1254x1254 | 0.000% |
| 4K | 3:2 | 3456x2304 | 1536x1024 | 0.000% |
| 4K | 2:3 | 2304x3456 | 1023x1537 | 0.163% |
| 4K | 16:9 | 3840x2160 | 1672x941 | 0.053% |
| 4K | 9:16 | 2160x3840 | 941x1672 | 0.053% |
| 4K | 4:3 | 3200x2400 | 1448x1086 | 0.000% |
| 4K | 3:4 | 2400x3200 | 1086x1448 | 0.000% |
| 4K | 21:9 | 3840x1600 | 1942x809 | 2.878% |

These are historical observed actual values, not permanent API guarantees. The relay often returned the same dimensions for multiple tiers; notably all three 16:9 tiers returned 1672x941 in this run. The 2K 16:9 case needed three attempts after transient gateway failures. Re-test after changing the base URL, model, quality, or relay implementation. The tested relay supports `b64_json`, URL, and streaming responses; the bundled executor deliberately uses `b64_json` so validation and atomic saving do not depend on a second download URL or SSE parser.

## Transparency Evidence

Two live tests on 2026-07-12 established separate native-API and website behaviors:

| Path | Request or processing | Verified result |
|---|---|---|
| Direct relay API | Sent `background=transparent`, PNG, low quality, 1024x1024 | Returned 1254x1254 RGB PNG with 0 transparent pixels; the relay accepted but ignored native transparency |
| Website transparent toggle | Uses prompt injection for a green/magenta chroma background, then website post-processing | Final original was a 1672x941 RGBA PNG with Alpha 0-255 and 1,302,865 transparent pixels |
| Website gallery preview | Derived from the same processed original | 720x405 WebP thumbnail with transparency; it is not the delivery original |

The current website bundle enables this toggle only for PNG and forces PNG output. It appends instructions selecting pure green `#00FF00`, or pure magenta `#FF00FF` when the subject contains green tones. After generation, it detects the dominant key color from border pixels, removes border-connected key-color regions, cleans edge spill, and exports a PNG. `transparent_output` is internal UI state and is not part of the default API request mapping; the effective prompt plus browser Canvas post-processing performs the work.

The website workflow therefore produces real transparency, but the relay API alone does not. The bundled executor does not yet reproduce the website's chroma-removal post-processing, so do not add or advertise a native `--background transparent` option based only on the accepted request.

Do not report transparency from appearance, an RGBA mode, or a checkbox alone. A transparent-background test succeeds only when the saved PNG decodes successfully and contains transparent pixels (`transparent_pixels > 0`, equivalently `alpha_min < 255`). Do not report transparency when Alpha is fully opaque, even if the image has a white, green, or magenta background.

## Retry Rules

| Result | Action |
|---|---|
| 408, 429, 5xx, 520-524, network timeout | Retry with backoff |
| Missing or invalid Base64, truncated or undecodable image | Retry |
| Requested format differs from the decoded returned format | Stop immediately; do not retry |
| Fully decoded requested format | Atomically save and mark success |
| Insufficient quota, invalid key, model not found | Stop immediately |
| Existing valid output during batch rerun | Skip |

## Output Evidence

- Single generation prints requested size, verified actual dimensions, format, alpha evidence, byte count, path, and attempts.
- Batch generation writes image-generation-ledger.jsonl and image-generation-summary.json.
- Re-running the same batch skips valid completed images in the requested format and continues unfinished tasks.
- Deliver the saved original image without post-processing and state its actual verified dimensions, even when they differ from the requested `size`.

## Common Mistakes

- Increasing client timeout does not extend a Cloudflare 524 gateway threshold; retries are the recovery mechanism.
- Do not use model spelling gpt-iamge-2; the correct default is gpt-image-2.
- Do not assume `--size 1280x720` produces a 1280x720 PNG; this relay currently returns an approximately 16:9 1672x941 PNG.
- Do not confuse `output_format` (PNG/JPEG/WebP encoding) with `response_format` (Base64 or URL transport).
- Do not report transparency unless the delivered PNG contains verified transparent pixels.
- Do not crop or resize generated images to conceal a provider-side size mismatch. Return the original PNG and honestly report the requested and actual dimensions.
- Do not delete successful images before retrying a failed batch.
- Do not claim guaranteed success when quota or the upstream service is unavailable.
