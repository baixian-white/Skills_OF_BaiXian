# Prompt Deck Output Schema

## Required Front Matter Content

The generated Markdown begins with:

- deck title
- topic and audience
- target aspect ratio
- text mode: `full-text` or `titleless-body`
- style profile
- style profile file and source (`bundled-profile`, `user-reference`, or documented hybrid)
- expected slide count
- section-divider audit
- global typography, margins, and text-accuracy rules

## Required Per-Slide Structure

```markdown
## 第 1 页 · 页面名称

**【生成提示词】**
> One complete prompt that can be sent directly to an image model.

**【本页文字】**
- 标题：...
- 正文：...
- 数据：...

**【页面类型】**
- cover

**【版式分组】**
- cover
```

## Prompt Order

Write prompt clauses in this order:

1. canvas ratio and page type
2. selected visual profile
3. text mode
4. safe whitespace and margins
5. primary composition
6. exact visible copy
7. diagram/chart topology and reading direction
8. typography hierarchy
9. color semantics
10. layout-group constraints
11. accuracy requirements
12. explicit negative constraints

## Titleless Body Mode Block

Every titleless content page must state all of the following:

- Do not render the page title, section title, English page title, header, page number, or title placeholder.
- Reserve a continuous background-only top whitespace zone.
- The whitespace is not a visible frame or title bar.
- Do not draw borders, rules, rounded rectangles, color strips, corner markers, shadows, gradients, textures, or decorations in it.
- Render all body copy, data, module headings, and diagram labels.

## Section Audit

For every agenda item, declare whether a section-divider page exists and where it appears. If the user rejects section pages, record that explicit choice.

## Layout Groups

Give related slides the same stable group name, for example:

- `representative-work`
- `research-content`
- `section-divider`
- `expected-outcomes`

Repeat shared hierarchy constraints in each prompt because image requests are stateless.

## Style Profile Resolution

- Read `style-index.md`, then the complete selected file under `styles/`.
- The `视觉风格` value must match a bundled profile ID unless the deck declares `风格来源：user-reference` or documents a hybrid.
- Brand profiles never authorize generation of missing logos, slogans, endorsements, buildings, or official assets.
