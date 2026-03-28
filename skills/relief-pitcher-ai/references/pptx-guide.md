# python-pptx Layout & Placeholder Guide

## Default Template Layouts

| idx | Layout Name | Purpose | slide_spec layout name |
|-----|-------------|---------|------------------------|
| 0 | Title Slide | Cover slide | `title_slide` |
| 1 | Title and Content | Title + bullet points | `title_and_content` |
| 2 | Section Header | Section divider | `section_header` |
| 3 | Two Content | Two columns | `two_content` |
| 5 | Title Only | Title only | `title_only` |
| 6 | Blank | Blank slide | `blank` |

## Placeholder idx Conventions

### Title Slide (layout idx 0)
- `idx 0`: Title
- `idx 1`: Subtitle

### Title and Content (layout idx 1)
- `idx 0`: Title
- `idx 1`: Content (bullet point body)

### Section Header (layout idx 2)
- `idx 0`: Title
- `idx 1`: Description text (if present)

### Two Content (layout idx 3)
- `idx 0`: Title
- `idx 1`: Left column
- `idx 2`: Right column

### Title Only (layout idx 5)
- `idx 0`: Title

### Blank (layout idx 6)
- No placeholders

## Notes for Custom Templates

- When using a custom template (.pptx), a fallback mechanism searches by layout name
- Match the layout names above in the template's slide master
- Placeholder idx values depend on the template, so verify idx values when using a custom template

## Layout Lookup Logic in slide_builder.py

1. Try the fixed index from `_DEFAULT_LAYOUT_IDX`
2. If that fails, search the slide master by layout name (English)
3. Final fallback: use the first layout in the slide master
