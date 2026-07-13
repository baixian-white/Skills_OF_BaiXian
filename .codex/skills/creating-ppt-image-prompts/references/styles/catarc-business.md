# 中汽研高端商务风

## Identity
- Profile ID: `catarc-business`
- Source: adapted from PPT Master layout template `中汽研_商务`.

## Best For
认证展示、汽车产业报告、高端商务提案

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 白色内容页、深蓝科技切面、冷灰卡片、精细渐变.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#0052A4, #0B2E59, #F0F2F5, #1F2937, #FFFFFF`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- 微软雅黑/PingFang SC/Segoe UI；现代商务.
- Prefer concise copy over unreadably small body text.

## Composition System
- 封面使用大留白与深色科技切面；内容页用规整卡片、对比结构和放射关系.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 无授权时不得生成真实 Logo 或认证标志；避免炫光过强和汽车广告化.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
