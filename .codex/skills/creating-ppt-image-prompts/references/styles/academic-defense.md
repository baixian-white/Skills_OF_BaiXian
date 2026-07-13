# 通用学术答辩

## Identity
- Profile ID: `academic-defense`
- Source: adapted from PPT Master layout template `academic_defense`.

## Best For
学术答辩、科研汇报、项目申报、开题报告

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 白底、深蓝标题系统、严谨清晰、少量红色强调.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#003366, #E8F4FC, #F5F7FA, #CC0000, #FFFFFF`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- 微软雅黑或现代中文黑体；标题稳重，正文高对比.
- Prefer concise copy over unreadably small body text.

## Composition System
- 封面简洁；内容页使用深蓝页眉、浅蓝结论条与规整信息模块；章节页使用深蓝满版和大型半透明章节号.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 避免营销感、花哨渐变、过度装饰、全篇密集卡片.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
