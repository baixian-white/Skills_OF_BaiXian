# 医学专业蓝绿风

## Identity
- Profile ID: `medical-university`
- Source: adapted from PPT Master layout template `medical_university`.

## Best For
医学汇报、病例讨论、医院培训、科研报告

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 白底、医学蓝、生命绿、浅蓝信息区.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#0066B3, #004080, #E6F3FA, #00A86B, #F5F7FA, #FFFFFF`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- 微软雅黑；医学术语和数据需高可读.
- Prefer concise copy over unreadably small body text.

## Composition System
- 使用病例路径、诊疗流程、指标卡、研究分组和风险提示；章节页使用深医学蓝满版.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 避免用装饰替代医学证据、夸大疗效、虚构病例数据、使用刺激性医疗图像.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
