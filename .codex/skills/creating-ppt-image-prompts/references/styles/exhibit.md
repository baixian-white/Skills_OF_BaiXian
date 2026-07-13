# Exhibit 结论先行

## Identity
- Profile ID: `exhibit`
- Source: adapted from PPT Master layout template `exhibit`.

## Best For
董事会汇报、战略报告、数据分析、管理层决策

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 深色封面与章节、白色内容页、金色与紫蓝强调.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#0D1117, #1F2937, #6366F1, #D4AF37, #FFFFFF, #111827`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- Arial/Helvetica；标题短促，图表标注清晰.
- Prefer concise copy over unreadably small body text.

## Composition System
- 内容页顶部设置明确的 takeaway 结论带，主体优先使用图表、矩阵和证据链；暗色页面可用低透明网格.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 避免把结论藏在页底、装饰压过数据、使用无依据的机密标签.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
