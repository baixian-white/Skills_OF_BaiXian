# Anthropic AI 技术风

## Identity
- Profile ID: `anthropic`
- Source: adapted from PPT Master layout template `anthropic`.

## Best For
AI、LLM、开发者分享、产品发布和技术洞察

## Canvas and Mood
- Default to 16:9 landscape unless the user requests another ratio.
- 深空灰封面与章节页、白色内容页、克制的橙蓝绿强调.
- Preserve generous safe margins and strong text contrast.

## Palette Direction
- Recommended palette: `#1A1A2E, #16213E, #F8FAFC, #FFFFFF, #F59E0B, #3B82F6, #10B981`.
- Colors are directions, not guaranteed exact output values. Keep semantic colors stable across sibling pages.

## Typography Direction
- Arial/Segoe UI 配合中文黑体；标题简洁现代.
- Prefer concise copy over unreadably small body text.

## Composition System
- 暗色页面使用神经网络连接线和节点；浅色内容页采用干净的三栏或流程布局，用颜色表达推荐、过程和强调.
- Select composition by page type; do not force every page into a card grid. Repeat shared rules inside every prompt in the same `layout_group`.

## Section Divider
Use one reusable system with stable chapter number, title, optional English subtitle, one-line bridge, and restrained topic imagery.

## Titleless Mode
Reserve uninterrupted background-only title whitespace. It is not a visible frame or title bar. Do not render the page title, header, page number, placeholder, border, rule, rounded rectangle, color strip, corner marker, shadow, gradient, texture, or decoration there. Render all body copy, module headings, data, and diagram labels below it.

## Negative Constraints
- 避免仿制真实产品 UI、过度霓虹、复杂玻璃效果、密集控制面板.
- Do not invent facts, metrics, awards, endorsements, logos, or branded assets.
- Re-generate a noncompliant image instead of moving, cropping, resizing, padding, or extending it.
