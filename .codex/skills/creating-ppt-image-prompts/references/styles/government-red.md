# 政务红权威风

## Identity
- Profile ID: `government-red`
- Source: adapted from PPT Master layout template `government_red`.

## Best For
政府报告、党建专题、政策宣贯、权威型工作汇报

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 白底内容页、政务红与深蓝双主色、庄重大气.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#8B0000, #003366, #F5F7FA, #FFFFFF, #1A1A1A`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- 微软雅黑/黑体；大标题端正有力.
- Prefer concise copy over unreadably small body text.

## Composition System
- 顶部可使用细红蓝引导线；章节页使用深蓝底和大型章节号，红色用于政策重点、行动节点和关键结论.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 避免节庆化大红背景铺满内容页、金色堆砌、未经提供的党政标识.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
