# 中国电建常规工程风

## Identity
- Profile ID: `powerchina-standard`
- Source: adapted from PPT Master layout template `中国电建_常规`.

## Best For
央企工程、能源建设、水务项目、项目汇报

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 白底、POWERCHINA 蓝、深蓝章节页、少量中国红.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#00418D, #002B5C, #0066CC, #C8102E, #F4F6F8, #FFFFFF`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- 微软雅黑/黑体；工程数据端正清晰.
- Prefer concise copy over unreadably small body text.

## Composition System
- 使用工程项目图、阶段流程、资质案例和里程碑；章节页可用深蓝渐变与斜线纹理.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 无授权时不得生成真实企业 Logo；避免消费品牌感、轻浮插画和过度未来化.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
