# Baseline Failures and Regression Scenarios

These failures came from a real outline-to-image-deck workflow and define the minimum regression suite.

## Scenario 1: Missing Section Dividers

Input contains seven agenda sections, but the prompt deck creates only cover, agenda, content, and closing pages.

Expected skill behavior: audit every agenda section and add or explicitly waive each section-divider page.

## Scenario 2: Visible Empty Title Frame

User chooses `titleless-body`. A prompt says “reserve a title box,” and the image model draws an empty rounded rectangle at the top.

Expected skill behavior: use uninterrupted title whitespace language and explicit no-frame negatives. Body copy remains rendered.

## Scenario 3: Post-Generation Translation

Sibling pages have different body start positions. An agent proposes moving one image downward and filling the top with white.

Expected skill behavior: reject translation, resizing, cropping, padding, or canvas extension. Revise the prompt and re-generate the noncompliant page.

## Scenario 4: Requested Size Assumed Exact

A request uses `1280x720`, while the provider returns `1672x941`.

Expected skill behavior: preserve and report the verified original dimensions; do not rewrite the PNG to imitate the requested dimensions.

## Scenario 5: Body Removed with Title

In titleless mode, the image prompt removes the page title and also removes module headings or diagram labels.

Expected skill behavior: remove only page-level title/header elements. Preserve body, module headings, data, conclusions, and diagram labels.
