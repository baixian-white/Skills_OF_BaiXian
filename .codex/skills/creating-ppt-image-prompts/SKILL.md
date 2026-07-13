---
name: creating-ppt-image-prompts
description: "Use when a user provides a PPT outline, report, manuscript, slide list, or presentation content and needs a slide-by-slide image-generation prompt deck, including section pages, consistent style profiles, title/no-title modes, Chinese text controls, layout groups, and batch-generation-ready Markdown."
---

# Creating PPT Image Prompts

## Overview

Turn a presentation outline into a complete, validated Markdown prompt deck for image models. Build the slide narrative first, classify page types and layout groups, then write prompts that preserve content while keeping a selected visual style consistent.

## Required Workflow

1. Read the complete source outline or manuscript before writing prompts.
2. Define the communication job, audience, and narrative sequence.
3. Audit the page architecture. Include cover, agenda, necessary section dividers, content pages, and closing page. Do not silently omit section pages.
4. Choose one text mode:
   - `full-text`: image model renders page title and body.
   - `titleless-body`: image model renders body and diagram labels; PowerPoint adds the page title later.
5. Choose a style profile. Read `references/style-index.md`, then read the selected file under `references/styles/`. If the user provides a visual reference, that reference overrides bundled profiles. Brand profiles are visual direction only and never imply official authorization.
6. Classify every page and assign a `layout_group` to sibling pages that must share hierarchy and composition.
7. Write each prompt using the prompt order in `references/output-schema.md`.
8. Keep a separate `【本页文字】` block for exact copy, names, units, dates, data, and later title insertion.
9. Run `scripts/validate_prompt_deck.py <markdown>` and fix every structural error before delivery.
10. If images are later generated, preserve the original validated PNG. Re-generate a bad page; do not geometrically repair it.

## Hard Rules

### Protect Source Content

- Preserve names, organizations, dates, numbers, percentages, paper titles, and diagram labels exactly.
- Never invent evidence, awards, publications, metrics, or outcomes.
- Reduce wording only when necessary for readability; record the exact visible copy in `【本页文字】`.
- Require manual text proofreading after generation because image models cannot guarantee perfect Chinese rendering.

### Preserve Original Images

Generated images must not be geometrically transformed:

- Do not translate or move image content.
- Do not resize, crop, stretch, rotate, pad, extend the canvas, or overwrite originals.
- Treat the provider's verified width and height as authoritative; requested size is only a target ratio/tier.
- If layout, title clearance, or sibling alignment is wrong, revise the prompt and re-generate that page.
- Store successful originals separately from selected final images.

### Titleless Body Mode

Use the term **title whitespace**, never **title box**. The reserved top area must look like uninterrupted page background.

Explicitly forbid visible title containers: empty frames, title bars, rounded rectangles, borders, strokes, color strips, corner markers, rules, shadows, gradients, textures, decorations, and placeholder text.

Do not ask the image model to create a precise PowerPoint text box. Record the intended PowerPoint title position separately in the document metadata or `【本页文字】`.

### Layout Groups

Sibling pages must share rules for hierarchy, safe margins, body start zone, module-title scale, color semantics, and conclusion placement. Examples: representative-work pages, research-content pages, yearly-plan pages, and all section dividers.

Pixel coordinates are guidance, not a guarantee. Never claim that prompts alone ensure exact cross-request coordinates.

## Page-Type Routing

Read `references/page-types.md` before authoring. At minimum distinguish:

- cover
- agenda
- section-divider
- profile or credentials
- metrics overview
- evidence or representative work
- background or scenario
- core diagram
- method or research content
- roadmap or architecture
- innovation
- schedule or Gantt
- outcomes
- support or assurance
- closing

Do not default every slide to a card grid. Choose the composition that communicates the page's single narrative job.

## Output Contract

Read `references/output-schema.md`. The final Markdown must include:

- deck metadata and global rules
- chosen text mode and style profile
- section-divider audit
- one numbered section per slide
- `【生成提示词】`
- `【本页文字】`
- `【页面类型】`
- `【版式分组】`

Copy `assets/prompt-deck-template.md` when a starting scaffold is useful.

## Style Profiles

Read `references/style-index.md` for the complete categorized profile list. The library includes academic, consulting, government, technology, medical, creative, engineering, automotive, financial, and institution-specific directions adapted from PPT Master templates.

- Read exactly one selected profile unless the user explicitly requests a hybrid.
- For a hybrid, state which rules come from each profile and resolve conflicts in deck metadata.
- Treat brand and institution profiles as visual directions. Never invent logos, endorsements, slogans, buildings, or official authorization.
- Add future styles as separate files under `references/styles/`; do not expand SKILL.md with variant-specific details.

## Validation

Run:

```powershell
python scripts/validate_prompt_deck.py path\to\prompt-deck.md
```

The validator checks page numbering, required blocks, page counts, registered style profiles, titleless negative constraints, and section-divider declarations. It does not validate visual quality or factual correctness; inspect those manually.

## Common Failures

| Failure | Required response |
|---|---|
| Missing section pages | Audit sections and add divider pages before finalizing prompts |
| Visible empty title frame | Replace “title box” language with uninterrupted title whitespace and explicit negative constraints |
| Inconsistent sibling pages | Assign a shared `layout_group` and repeat the group's hierarchy rules |
| Exact pixel alignment assumed | State that coordinates are guidance; re-generate noncompliant pages |
| Body text omitted in titleless mode | Remove only the page title; retain body, data, and diagram labels |
| Requested pixels differ from returned PNG | Report actual verified dimensions and preserve the original |
| Bad image fixed by movement/cropping | Reject the image and re-generate it |
| Dense dashboard aesthetic everywhere | Re-route by page type and use one primary composition |
