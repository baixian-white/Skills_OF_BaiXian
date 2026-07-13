# Title Markdown Format

Use either a four-column Markdown table or a numbered list.

## Recommended Table

```markdown
| Final page | Source label | Page type | Page title |
|---:|---|---|---|
| 1 | Page 1 | cover | Main presentation title |
| 2 | Section 1 | section | First section title |
| 3 | Page 2 | content | First content slide title |
```

The parser also accepts Chinese labels such as `封面`, `章节过渡页`, and `内容页`. A row is treated as a section page when its type or source label contains `section`, `chapter`, `part`, `章节`, or `过渡`.

## Simple Numbered List

```markdown
1. First slide title
2. Second slide title
3. Third slide title
```

Numbered-list entries are treated as ordinary content pages. Use the table when cover or section styling is needed.
