# Theme Profiles and JSON Overrides

Theme settings apply only to editable PowerPoint overlays. Source images remain byte-for-byte unchanged.

## Built-in Profiles

| Profile | Direction | Typical use |
|---|---|---|
| `tech-blue` | Blue, teal, and gold technology-business style | Technology, training, product, and enterprise presentations |
| `financial-red` | Restrained red and dark-red financial style | Finance, business, and sales presentations |
| `consulting-navy` | Navy executive-consulting style | Strategy, analysis, and management reporting |
| `government-blue` | Stable formal blue style | Public-sector, institutional, and formal reporting |
| `minimal-gray` | Neutral gray minimalist style | General professional presentations |

These names describe visual directions only. They do not authorize logos, trademarks, slogans, or official brand assets.

## JSON Format

Every field is optional. Values override the selected built-in profile.

```json
{
  "font": "Microsoft YaHei",
  "primary_color": "123B6D",
  "accent_color": "19A7A0",
  "highlight_color": "D4A64A",
  "muted_color": "8493A5",
  "section_number_color": "D9E2EC",
  "cover_eyebrow": "PRESENTATION",
  "part_label": "PART",
  "title_position": "top-left",
  "show_page_number": true,
  "show_section_label": true
}
```

## Field Rules

- Colors accept six hexadecimal digits with or without `#`.
- `title_position` accepts `top-left` or `top-center`.
- `show_page_number` and `show_section_label` are booleans.
- `cover_eyebrow` and `part_label` may be Chinese or English.
- Unknown keys are rejected to catch spelling mistakes.
- Keep JSON reusable across decks; presentation-specific titles stay in the title Markdown file.

