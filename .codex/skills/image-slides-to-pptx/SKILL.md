---
name: image-slides-to-pptx
description: "Use when numbered PNG or JPEG files must be combined into a PowerPoint deck, especially for full-slide image decks, editable title overlays, reusable theme profiles, section decorations, page numbers, 16:9 output, or PPTX integrity and image-mapping verification."
---

# Image Slides to PPTX

## Overview

Convert consecutively numbered slide images into a standard 16:9 `.pptx` without requiring PowerPoint, WPS, LibreOffice, `python-pptx`, or `@oai/artifact-tool`. Preserve image bytes exactly and validate the generated OOXML package.

## Required Workflow

1. Confirm the input directory contains one unique numbered image per slide: `01.png`, `02.png`, ... or equivalent numeric names.
2. Decide the overlay style:
   - `plain`: full-slide images only; no title file required.
   - `title`: add one editable title textbox per slide.
   - `decorated`: add editable titles plus cover, section, accent-line, chapter, and page-number decorations.
3. For `title` or `decorated`, prepare a title Markdown file using `references/title-format.md`.
4. Select a generic `--theme-profile`; optionally supply `--theme theme.json` for reusable overrides. Read `references/theme-format.md`.
5. Run `scripts/build_image_deck.py` with explicit output and JSON report paths.
6. Treat success only when the command exits zero and the report shows `zip_valid`, `xml_valid`, and `all_images_match` as `true`.

## Commands

Plain image deck:

```powershell
python "<SKILL_DIR>\scripts\build_image_deck.py" `
  --images-dir ".\images" `
  --style plain `
  --output ".\deck.pptx" `
  --report ".\deck-report.json"
```

Decorated editable-title deck:

```powershell
python "<SKILL_DIR>\scripts\build_image_deck.py" `
  --images-dir ".\images" `
  --titles ".\titles.md" `
  --style decorated `
  --theme-profile tech-blue `
  --output ".\deck-decorated.pptx" `
  --report ".\deck-decorated-report.json"
```

Custom reusable theme:

```powershell
python "<SKILL_DIR>\scripts\build_image_deck.py" `
  --images-dir ".\images" `
  --titles ".\titles.md" `
  --style decorated `
  --theme-profile consulting-navy `
  --theme ".\theme.json" `
  --output ".\deck-custom.pptx" `
  --report ".\deck-custom-report.json"
```

Run `python "<SKILL_DIR>\scripts\build_image_deck.py" --help` for the full CLI.

## Input Rules

- Accept `.png`, `.jpg`, and `.jpeg`.
- Use continuous numeric filenames starting at 1. Zero padding is optional.
- Reject duplicate numbers and missing sequence numbers instead of silently reordering or skipping slides.
- Require title count and title page numbers to match the image sequence.
- Preserve each source image as a full-slide stretched background on a 16:9 canvas.

## Theme Rules

- Built-in profiles are generic visual directions: `tech-blue`, `financial-red`, `consulting-navy`, `government-blue`, and `minimal-gray`.
- Profiles control editable overlay typography, colors, labels, title alignment, page numbers, and section labels. They do not alter source images.
- Use JSON overrides for organization or project branding; do not hard-code a one-off presentation into this skill.
- Keep one theme stable within a deck. Do not randomize title decoration slide by slide.
- Profiles never imply authorization to use logos, trademarks, official slogans, or branded assets.

## Output Guarantees

The JSON report includes slide count, media count, title count, overlay style, theme profile, canvas, package size, ZIP validity, XML validity, and SHA-256 equality between source and embedded images.

## Common Mistakes

- Do not mix old generations, contact sheets, and final page images in the same input directory.
- Do not claim success from file creation alone; inspect the JSON report.
- Do not use `decorated` without a title file.
- Do not rename images lexicographically without numeric validation; `1, 10, 2` is not a valid slide order.
- Do not add titles over images that lack a reserved title area unless the user accepts possible overlap.
- Do not create a new built-in profile for a single presentation; use `--theme` overrides instead.

