---
name: daida-ai
description: >
  LT（ライトニングトーク）のプレゼン資料を自動生成するスキル。
  テーマからアウトライン作成、PowerPoint/ODPスライド生成、
  トークスクリプト（台本）の記入、音声合成、音声埋め込みまで一括対応。
  使用場面: (1) 登壇テーマからプレゼンを一括作成したい,
  (2) 既存アウトラインからスライドを作りたい,
  (3) スライドにトークスクリプトを追加したい,
  (4) スクリプトから音声を合成してスライドに埋め込みたい。
  トリガー: LT, ライトニングトーク, プレゼン作成, スライド作成,
  代打, 登壇, presentation, slides, talk script, 音声合成。
---

# 代打AI — LTプレゼン自動生成スキル

## 概要

テーマ入力から完成プレゼンまでの一連のパイプラインを実行する。

**パイプライン**: テーマ → アウトライン → コンテンツ充実化(JSON) → PPTX生成 → トークスクリプト → 音声合成 → 音声埋め込み

## 前提条件

初回実行時、以下でセットアップする:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh
```

## 共通パス

スクリプト実行時は以下のPythonパスを使用する（プラグインキャッシュ環境でも動作するよう絶対パスを使う）:

```
PYTHON=${CLAUDE_SKILL_DIR}/../../.venv/bin/python
```

以降のコマンド例では上記を `$PYTHON` として記載する。

## ワークフロー選択

ユーザーに以下を確認する:
1. **フル実行**: テーマからすべて自動生成
2. **ステップ指定**: 特定のステップから開始（既存ファイルを利用）

出力ディレクトリはユーザーに確認する（デフォルト: `./output/`）

---

## Step 1: アウトライン生成

### あなた（Claude）がやること

ユーザーから以下を聞き取る:
- **テーマ**: 何について話すか
- **対象者**: 誰に向けたLTか
- **持ち時間**: 何分か（デフォルト5分）
- **イベント名**: 任意

以下の構造でMarkdownアウトラインを生成する:

```markdown
# プレゼンタイトル

## 導入
- ポイント1
- ポイント2

## 本題1: セクション名
- ポイント
- ポイント

## 本題2: セクション名
- ポイント
- ポイント

## まとめ
- ポイント
```

**原則**:
- LT（5分）: セクション3〜4個、各2〜3項目
- 通常発表（15分）: セクション5〜7個
- 1スライド30秒〜1分が目安

### スクリプト実行

生成したMarkdownをファイルに保存してからスクリプトに渡す:
```bash
# まずアウトラインMarkdownをファイルに保存（Writeツール使用）
# 次にスクリプトで所定のパスに保存
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/generate_outline.py output/outline.md --stdin < output/outline_draft.md
```

---

## Step 1.5: コンテンツ充実化

### あなた（Claude）がやること

Step 1で生成したアウトラインを読み、以下の指針でスライド仕様JSONを生成する:

**充実化の指針**:
- **具体的な数値・データ**を追加（「速い」→「10倍高速」）
- **対比・比較**がある場合は `two_content` レイアウトを選択
- **1スライド1メッセージ**の原則を守る
- **箇条書きは3〜5項目**に絞る
- コード例がある場合は `title_only` + コードブロックをnoteに記載
- 最初のスライドは必ず `title_slide`
- セクション区切りには `section_header`

**ユーザーに確認する**:
- テンプレート: `tech`（デフォルト） / `casual` / `formal`

### JSON形式

```json
{
  "metadata": {
    "title": "プレゼンタイトル",
    "subtitle": "登壇者名",
    "event": "イベント名",
    "template": "tech"
  },
  "slides": [
    {
      "layout": "title_slide",
      "title": "プレゼンタイトル",
      "subtitle": "2026/03/10 @ イベント名 - 登壇者名"
    },
    {
      "layout": "section_header",
      "title": "セクション名"
    },
    {
      "layout": "title_and_content",
      "title": "スライドタイトル",
      "body": ["ポイント1", "ポイント2", "ポイント3"],
      "note": "トークスクリプト（台本）"
    },
    {
      "layout": "two_content",
      "title": "比較タイトル",
      "left": {"heading": "左見出し", "body": ["項目1", "項目2"]},
      "right": {"heading": "右見出し", "body": ["項目1", "項目2"]},
      "note": "トークスクリプト"
    },
    {
      "layout": "title_only",
      "title": "図・コード用スライド",
      "note": "このスライドの説明"
    }
  ]
}
```

**利用可能なレイアウト**: `title_slide`, `section_header`, `title_and_content`, `two_content`, `title_only`, `blank`

**重要**: `note` フィールドにトークスクリプト（台本）を必ず含めること。Step 3で更新可能だが、ここで初版を生成しておく。

### スクリプト実行

生成したJSONをファイルに保存してからスクリプトに渡す（JSONが大きい場合、echoパイプだと失敗する可能性がある）:
```bash
# まずスライド仕様JSONをファイルに保存（Writeツール使用）
# 次にスクリプトでバリデーション＆保存
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/enrich_outline.py output/slide_spec.json --stdin < output/slide_spec_draft.json
```

---

## Step 2: スライド作成

### スクリプト実行

```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/create_slides.py output/slide_spec.json output/presentation.pptx
```

カスタムテンプレートを使う場合:
```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/create_slides.py output/slide_spec.json output/presentation.pptx --template path/to/template.pptx
```

生成後、ユーザーにPPTXの確認を依頼する。

---

## Step 3: トークスクリプト更新（オプション）

Step 1.5でnoteが既に含まれている場合、このステップはスキップ可能。
ユーザーが文体変更やスクリプト再生成を希望する場合に実行する。

### あなた（Claude）がやること

1. 現在のノートを読み出す:
```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/write_talk_script.py output/presentation.pptx --read
```

2. `references/talk-styles.md` を参照し、ユーザーの希望する文体で全スライドのスクリプトを再生成する
   - 文体: `casual`（デフォルト） / `keynote` / `formal` / `humorous`

3. JSON配列として保存し、PPTXに書き込む:
```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/write_talk_script.py output/presentation.pptx --notes-json output/notes.json --output output/presentation.pptx
```

---

## Step 4: 音声合成

### ユーザーに確認する
- TTSエンジン: `edge`（デフォルト） / `voicevox`
- 音声: デフォルトは `ja-JP-NanamiNeural`（edge）、`1`=ずんだもん（voicevox）

### スクリプト実行

```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/synthesize_audio.py output/presentation.pptx output/audio/ --engine edge
```

VOICEVOX使用時（事前にVOICEVOX Engineの起動が必要）:
```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/synthesize_audio.py output/presentation.pptx output/audio/ --engine voicevox
```

---

## Step 5: 音声埋め込み

### スクリプト実行

```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/embed_audio.py output/presentation.pptx output/audio/ output/presentation_with_audio.pptx
```

---

## フォーマット変換（オプション）

ODP形式が必要な場合:
```bash
$PYTHON ${CLAUDE_SKILL_DIR}/scripts/convert_format.py output/presentation.pptx --outdir output/
```

**前提**: LibreOfficeがインストールされていること。

---

## リファレンス

- `references/pptx-guide.md`: レイアウト・プレースホルダーの詳細
- `references/talk-styles.md`: トークスクリプトの文体定義
- `references/tts-plugins.md`: TTSプラグインの追加方法
