# TTS 読み辞書 仕様書

## 背景

PR #65 で TTS スクリプトのエクスポート/インポート機能を追加したが、
毎回同じ単語の読みを手動修正するのは非効率。
頻出の誤読パターンを辞書として定義し、エクスポート時に自動適用する。

## 要件

1. TSV 形式の辞書ファイルで「置換前→置換後」の対応を定義する
2. `export_tts_script` 時に辞書を適用し、置換済みスクリプトを出力する
3. プロジェクト同梱のデフォルト辞書を提供する
4. ユーザーが辞書を追加・上書きできる

## 辞書ファイル形式

TSV（タブ区切り）。1行1エントリ。`#` で始まる行はコメント。

```tsv
# 読み辞書: 置換前<TAB>置換後
生成	せいせい
Claude	クロード
LLM	エルエルエム
```

### フォーマット仕様

- エンコーディング: UTF-8
- 区切り文字: タブ（`\t`）
- 各行: `置換前\t置換後`
- コメント行: `#` で始まる行（先頭スペース不可）
- 空行: 無視
- 置換は単純な文字列置換（正規表現ではない）
- 辞書内の順序で適用（先に定義されたエントリが優先）

## API 設計

### `pronunciation_dict.load_dict(dict_path) -> list[tuple[str, str]]`

- `dict_path: Path` — 辞書ファイルパス
- 戻り値: `[(置換前, 置換後), ...]` のリスト（定義順）
- エラー: `FileNotFoundError`（ファイル不在）、`ValueError`（不正フォーマット）

### `pronunciation_dict.apply_dict(text, entries) -> str`

- `text: str` — 置換対象テキスト
- `entries: list[tuple[str, str]]` — 辞書エントリ
- 戻り値: 置換済みテキスト

### `talk_script.export_tts_script(notes, output_path, dict_entries=None) -> Path`

- 既存関数に `dict_entries` 引数を追加（省略時は辞書適用なし）

## CLI

### `export_tts_script.py` に `--dict` オプション追加

```bash
# デフォルト辞書を使用
python export_tts_script.py output/presentation.pptx output/tts_script.txt \
  --dict skills/daida-ai/assets/pronunciation_dict.tsv

# 辞書なし（従来通り）
python export_tts_script.py output/presentation.pptx output/tts_script.txt
```

## デフォルト辞書

`skills/daida-ai/assets/pronunciation_dict.tsv` に配置。
よくある誤読パターンを収録。ユーザーがコピーして編集可能。
