# python-pptx レイアウト・プレースホルダー解説

## デフォルトテンプレートのレイアウト

| idx | レイアウト名 | 用途 | slide_spec layout名 |
|-----|-------------|------|---------------------|
| 0 | Title Slide | 表紙 | `title_slide` |
| 1 | Title and Content | タイトル+箇条書き | `title_and_content` |
| 2 | Section Header | セクション区切り | `section_header` |
| 3 | Two Content | 2カラム | `two_content` |
| 5 | Title Only | タイトルのみ | `title_only` |
| 6 | Blank | 白紙 | `blank` |

## プレースホルダーのidx規約

### Title Slide (layout idx 0)
- `idx 0`: タイトル
- `idx 1`: サブタイトル

### Title and Content (layout idx 1)
- `idx 0`: タイトル
- `idx 1`: コンテンツ（箇条書き本文）

### Section Header (layout idx 2)
- `idx 0`: タイトル
- `idx 1`: 説明テキスト（あれば）

### Two Content (layout idx 3)
- `idx 0`: タイトル
- `idx 1`: 左カラム
- `idx 2`: 右カラム

### Title Only (layout idx 5)
- `idx 0`: タイトル

### Blank (layout idx 6)
- プレースホルダーなし

## カスタムテンプレートでの注意

- カスタムテンプレート(.pptx)を使用する場合、レイアウト名で検索するフォールバック機構がある
- テンプレートのスライドマスターで上記のレイアウト名と一致させること
- プレースホルダーのidxはテンプレートに依存するため、カスタムテンプレートではidxを確認すること

## slide_builder.py のレイアウト検索ロジック

1. `_DEFAULT_LAYOUT_IDX` の固定インデックスで試行
2. 失敗した場合、レイアウト名（英語）でスライドマスターを検索
3. 最終フォールバック: スライドマスターの最初のレイアウト
