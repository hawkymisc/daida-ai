# TTS Script Export/Import 仕様書

## 背景

音声合成（TTS）において、テキストの読みが正しくない場合がある。

- 「生成」→「せいしげる」（人名と誤認）
- 「Claude」→「クローダ」（英語の読み誤り）
- 「スライドショー」→ 正しく発音されない

ユーザーが音声合成前にスクリプト（読み上げテキスト）を確認・修正できる仕組みが必要。

## 要件

1. PPTXのスピーカーノートを外部テキストファイルに**エクスポート**する
2. ユーザーがテキストエディタで**読みを修正**する（例: 「生成」→「せいせい」）
3. 修正済みスクリプトファイルを指定して**音声合成**を実行する

## ファイル形式

区切り線ベースのプレーンテキスト形式。複数行ノートに対応し、テキストエディタで直感的に編集可能。

```
--- Slide 000 ---
こんにちは、今日はせいせいAIについてお話しします。

--- Slide 001 ---
クロードは素晴らしいAIです。
複数行のノートにも対応しています。

--- Slide 002 ---

```

### フォーマット仕様

- 区切り線: `--- Slide NNN ---`（NNNは3桁ゼロ埋め、0始まり）
- 区切り線の直後の改行から次の区切り線の直前の改行までがノートテキスト
- 空ノートスライドも区切り線は出力する（空行のまま）
- ファイル末尾の改行は許容
- エンコーディング: UTF-8

## API設計

### `talk_script.export_tts_script(notes, output_path) -> Path`

- `notes: list[str]` — スライドごとのノートテキスト
- `output_path: Path` — 出力ファイルパス
- 戻り値: 出力ファイルパス

### `talk_script.load_tts_script(script_path) -> list[str]`

- `script_path: Path` — スクリプトファイルパス
- 戻り値: スライドごとのノートテキストリスト
- エラー: `FileNotFoundError`（ファイル不在）、`ValueError`（不正フォーマット）

## CLIスクリプト

### `export_tts_script.py`（新規）

```bash
python export_tts_script.py output/presentation.pptx output/tts_script.txt
```

### `synthesize_audio.py`（既存 + `--script` オプション）

```bash
# 従来通り（PPTXノートから直接合成）
python synthesize_audio.py output/presentation.pptx output/audio/ --engine edge

# スクリプトファイルから合成（--script指定時はPPTXのノートを無視）
python synthesize_audio.py output/presentation.pptx output/audio/ --engine edge --script output/tts_script.txt
```

## ワークフロー（SKILL.md Step 4）

1. **エクスポート**: スピーカーノートをスクリプトファイルに出力
2. **ユーザー確認**: スクリプトファイルの内容を表示し、修正が必要か確認
3. **（任意）修正**: ユーザーが読みを修正
4. **音声合成**: `--script` 付きで合成実行（修正がなければ従来通り）
