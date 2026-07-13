# 政务蓝科技风

## Identity
- Profile ID: `government-blue`
- Source: adapted from PPT Master layout template `government_blue`.

## Best For
数字政府、智慧城市、公共治理、政务工作汇报

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 蓝色渐变、明亮科技感、庄重专业.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#003366, #00B4D8, #E6F4FF, #FFFFFF, #1A1A1A`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- 微软雅黑/黑体；标题庄重，正文规整.
- Prefer concise copy over unreadably small body text.

## Composition System
- 封面与章节页可使用深蓝渐变和轻量网格；内容页以浅色背景、政策路径、治理架构和成果模块为主.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 避免娱乐化插画、强霓虹、过度互联网产品感和未经提供的政府徽标.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
