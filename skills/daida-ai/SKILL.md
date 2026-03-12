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

**パイプライン**: テーマ → アウトライン → コンテンツ充実化(JSON) → PPTX生成 → トークスクリプト → 音声合成 → 音声埋め込み → スライドショー自動再生設定

## 前提条件

初回実行時、以下でセットアップする:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup.sh
```

## スクリプト実行の共通パターン

すべてのPythonスクリプトは `run.sh` ラッパー経由で実行する（venvの自動解決）:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh <script_name.py> [args...]
```

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
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh generate_outline.py output/outline.md --stdin < output/outline_draft.md
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
    },
    {
      "layout": "title_only",
      "title": "アーキテクチャ図",
      "image": "images/architecture.png",
      "note": "この図はシステム全体の構成を示しています"
    },
    {
      "layout": "blank",
      "image": "images/fullscreen_photo.jpg"
    }
  ]
}
```

**利用可能なレイアウト**: `title_slide`, `section_header`, `title_and_content`, `two_content`, `title_only`, `blank`

**画像の挿入**: `image` フィールドに画像ファイルパスを指定すると、スライドに画像が挿入される。
- パスはスライド仕様JSONファイルからの相対パスで指定する（例: specが `output/slide_spec.json` なら `images/foo.png` → `output/images/foo.png` として解決）
- 画像はコンテンツ領域内に**アスペクト比を維持して**自動フィットし、水平・垂直とも中央配置される
- 画像はテキストプレースホルダの背面に配置される
- 全レイアウトで使用可能。推奨: `title_only`（タイトル+図）、`blank`（フルスクリーン図）
- 対応フォーマット: PNG, JPEG, GIF, BMP, TIFF, **SVG**（自動PNG変換、要cairosvg）

**重要**: `note` フィールドにトークスクリプト（台本）を必ず含めること。Step 3で更新可能だが、ここで初版を生成しておく。

### スクリプト実行

生成したJSONをファイルに保存してからスクリプトに渡す（JSONが大きい場合、echoパイプだと失敗する可能性がある）:
```bash
# まずスライド仕様JSONをファイルに保存（Writeツール使用）
# 次にスクリプトでバリデーション＆保存
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh enrich_outline.py output/slide_spec.json --stdin < output/slide_spec_draft.json
```

---

## Step 1.7: 画像生成（オプション）

スライドに図やイラストを含めたい場合、画像を生成する。

### 方式の選択

以下のフローチャートに従って方式を決定する:

```
1. GEMINI_API_KEY は設定されているか？
   ├─ No → 全て SVG で生成する（後述「SVG生成」セクション）
   └─ Yes → 2へ
2. 画像の内容は？
   ├─ SVG向き（後述リスト参照） → 「SVG生成」セクションへ
   └─ Nano Banana向き（後述リスト参照） → 「Nano Banana」セクションへ
```

#### SVG向き（Claude が直接生成）

以下に該当する画像は **SVG** を使う。APIキー不要・即時生成・編集可能。

- フローチャート・プロセス図・ステップ図
- アーキテクチャ図・システム構成図
- 比較図（Before/After、A vs B）
- 棒グラフ・円グラフ・簡易チャート
- アイコン・ロゴ・シンボル
- タイムライン・ロードマップ
- テーブル・マトリクス図
- テキスト主体の概念図・マインドマップ

#### Nano Banana向き（Gemini API で生成）

以下に該当する画像は **Nano Banana** を使う。`GEMINI_API_KEY` が必要。

- 写真風の背景・風景・人物
- リアルな質感のイラスト・3Dレンダリング風
- 具体的な物体の描写（製品写真風など）
- 手書き風・水彩風・油絵風のアート
- スクリーンショット風のモックアップ

**迷ったらSVG**。SVGは即時生成でき、修正も容易。Nano Bananaは「SVGでは表現できないリアルさ」が必要な場合のみ使う。

### ユーザーに確認する
- 画像が必要なスライドと、それぞれの内容
- Nano Banana 使用時: アスペクト比 (`16:9` / `4:3` / `1:1`)、解像度 (`1K` / `2K` / `4K`)

---

### Nano Banana（Gemini画像生成API）

**前提条件**: `GEMINI_API_KEY` 環境変数

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh generate_image.py \
  --prompt "A futuristic system architecture diagram, clean flat design" \
  --output output/images/slide3_photo.png \
  --aspect-ratio 16:9 \
  --size 1K \
  --model pro
```

| Alias | Model ID | 用途 |
|---|---|---|
| `pro` | `gemini-3-pro-image-preview` | 高品質、複雑なプロンプト、テキスト描画 |
| `flash` | `gemini-3.1-flash-image-preview` | 高速生成、大量生成 |
| `legacy` | `gemini-2.5-flash-image` | 旧モデル |

生成後、Read ツールで画像をユーザーに見せ、必要に応じてプロンプトを調整する。

---

### SVG生成（API不要）

あなた（Claude）がSVGコードを直接生成する。
**SVGファイルはスライド仕様JSONの `image` フィールドにそのまま指定できる**（ビルド時に自動でPNGに変換される）。

**前提条件**: `cairosvg` がインストールされていること（`setup.sh` 実行済みなら自動インストール済み）。未インストールの場合:
```bash
pip install cairosvg
```

#### 手順

1. **Write ツール**で SVG ファイルを `output/images/` に作成する
2. スライド仕様JSONの `image` フィールドに **SVG パス** を直接指定する
3. Step 2 の `create_slides.py` 実行時に自動でPNG変換→挿入される

手動変換は不要。ただし事前にプレビューしたい場合:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh svg_to_png.py input.svg output.png
```

#### SVGサイズ

| 用途 | viewBox | 説明 |
|---|---|---|
| スライド全面 | `0 0 1920 1080` | 16:9、blank レイアウト向き |
| コンテンツ領域 | `0 0 1200 900` | 4:3、title_only レイアウト向き |
| アイコン・ロゴ | `0 0 400 400` | 1:1 |

#### テンプレート別カラースキーム

| テンプレート | 背景 | アクセント1 | アクセント2 | テキスト |
|---|---|---|---|---|
| tech | `#1E293B` | `#38BDF8` | `#818CF8` | `#E2E8F0` |
| casual | `#FFF8F0` | `#FF6B35` | `#06D6A0` | `#2D3748` |
| formal | `#FFFFFF` | `#1B2D45` | `#C49B66` | `#1B2D45` |

**注意**: フォントは必ず `font-family="sans-serif"` を指定する（環境依存を避けるため）。

#### SVGパターン集

**フローチャート（3ステップ）**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#818CF8"/>
    </marker>
  </defs>
  <!-- Step 1 -->
  <rect x="160" y="420" width="400" height="160" rx="16" fill="#38BDF8"/>
  <text x="360" y="510" text-anchor="middle" fill="#1E293B"
        font-size="28" font-family="sans-serif" font-weight="bold">Step 1</text>
  <!-- Arrow 1→2 -->
  <line x1="560" y1="500" x2="720" y2="500" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- Step 2 -->
  <rect x="760" y="420" width="400" height="160" rx="16" fill="#38BDF8"/>
  <text x="960" y="510" text-anchor="middle" fill="#1E293B"
        font-size="28" font-family="sans-serif" font-weight="bold">Step 2</text>
  <!-- Arrow 2→3 -->
  <line x1="1160" y1="500" x2="1320" y2="500" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- Step 3 -->
  <rect x="1360" y="420" width="400" height="160" rx="16" fill="#38BDF8"/>
  <text x="1560" y="510" text-anchor="middle" fill="#1E293B"
        font-size="28" font-family="sans-serif" font-weight="bold">Step 3</text>
</svg>
```

**比較図（Before / After）**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
  <!-- Before -->
  <rect x="80" y="120" width="840" height="840" rx="20" fill="#334155" stroke="#475569" stroke-width="2"/>
  <text x="500" y="200" text-anchor="middle" fill="#EF4444"
        font-size="36" font-family="sans-serif" font-weight="bold">Before</text>
  <text x="500" y="400" text-anchor="middle" fill="#94A3B8"
        font-size="24" font-family="sans-serif">手動で3時間</text>
  <text x="500" y="460" text-anchor="middle" fill="#94A3B8"
        font-size="24" font-family="sans-serif">ミスが多い</text>
  <text x="500" y="520" text-anchor="middle" fill="#94A3B8"
        font-size="24" font-family="sans-serif">属人化</text>
  <!-- After -->
  <rect x="1000" y="120" width="840" height="840" rx="20" fill="#334155" stroke="#38BDF8" stroke-width="2"/>
  <text x="1420" y="200" text-anchor="middle" fill="#38BDF8"
        font-size="36" font-family="sans-serif" font-weight="bold">After</text>
  <text x="1420" y="400" text-anchor="middle" fill="#E2E8F0"
        font-size="24" font-family="sans-serif">自動で5分</text>
  <text x="1420" y="460" text-anchor="middle" fill="#E2E8F0"
        font-size="24" font-family="sans-serif">品質が安定</text>
  <text x="1420" y="520" text-anchor="middle" fill="#E2E8F0"
        font-size="24" font-family="sans-serif">誰でも実行可能</text>
</svg>
```

**アーキテクチャ図（3層）**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080">
  <rect width="1920" height="1080" fill="#1E293B"/>
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0,10 3.5,0 7" fill="#818CF8"/>
    </marker>
  </defs>
  <!-- Frontend -->
  <rect x="660" y="80" width="600" height="140" rx="16" fill="#38BDF8"/>
  <text x="960" y="160" text-anchor="middle" fill="#1E293B"
        font-size="32" font-family="sans-serif" font-weight="bold">Frontend</text>
  <!-- Arrow -->
  <line x1="960" y1="220" x2="960" y2="360" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- API -->
  <rect x="660" y="380" width="600" height="140" rx="16" fill="#818CF8"/>
  <text x="960" y="460" text-anchor="middle" fill="#FFFFFF"
        font-size="32" font-family="sans-serif" font-weight="bold">API Server</text>
  <!-- Arrow -->
  <line x1="960" y1="520" x2="960" y2="660" stroke="#818CF8" stroke-width="4" marker-end="url(#arr)"/>
  <!-- Database -->
  <rect x="660" y="680" width="600" height="140" rx="16" fill="#334155" stroke="#38BDF8" stroke-width="2"/>
  <text x="960" y="760" text-anchor="middle" fill="#38BDF8"
        font-size="32" font-family="sans-serif" font-weight="bold">Database</text>
</svg>
```

---

### ワークフロー

1. Step 1.5 のスライド仕様JSONで `image` フィールドに出力パスを指定する
   - Nano Banana: `.png` パスを指定
   - SVG: `.svg` パスを指定（自動変換される）
2. 本ステップで画像を生成
3. Step 2 でスライド生成時に自動的に画像が挿入される

---

## Step 2: スライド作成

### スクリプト実行

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh create_slides.py output/slide_spec.json output/presentation.pptx
```

カスタムテンプレートを使う場合:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh create_slides.py output/slide_spec.json output/presentation.pptx --template path/to/template.pptx
```

生成後、ユーザーにPPTXの確認を依頼する。

---

## Step 3: トークスクリプト更新（オプション）

Step 1.5でnoteが既に含まれている場合、このステップはスキップ可能。
ユーザーが文体変更やスクリプト再生成を希望する場合に実行する。

### あなた（Claude）がやること

1. 現在のノートを読み出す:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh write_talk_script.py output/presentation.pptx --read
```

2. `references/talk-styles.md` を参照し、ユーザーの希望する文体で全スライドのスクリプトを再生成する
   - 文体: `casual`（デフォルト） / `keynote` / `formal` / `humorous`

3. JSON配列として保存し、PPTXに書き込む:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh write_talk_script.py output/presentation.pptx --notes-json output/notes.json --output output/presentation.pptx
```

---

## Step 4: 音声合成

### ユーザーに確認する
- TTSエンジン: `edge`（デフォルト） / `voicevox`
- 音声: デフォルトは `ja-JP-NanamiNeural`（edge）、`1`=ずんだもん（voicevox）

### スクリプト実行

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine edge
```

VOICEVOX使用時（事前にVOICEVOX Engineの起動が必要）:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh synthesize_audio.py output/presentation.pptx output/audio/ --engine voicevox
```

---

## Step 5: 音声埋め込み

### スクリプト実行

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh embed_audio.py output/presentation.pptx output/audio/ output/presentation_with_audio.pptx
```

---

## Step 6: スライドショー自動再生設定

音声埋め込み済みPPTXに、自動ページ送りと音声自動再生を設定する。
これにより、スライドショーを開始するだけで最後まで完全自動で再生される。

- 音声付きスライド: 音声再生完了 + バッファ（デフォルト1秒）で自動ページ送り
- 音声なしスライド（表紙・中表紙等）: 固定時間（デフォルト3秒）で自動ページ送り

### スクリプト実行

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh make_slideshow.py output/presentation_with_audio.pptx output/presentation_final.pptx
```

表示時間を調整する場合:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh make_slideshow.py output/presentation_with_audio.pptx output/presentation_final.pptx --silent-duration 5000 --audio-buffer 2000
```

---

## フォーマット変換（オプション）

ODP形式が必要な場合:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/run.sh convert_format.py output/presentation.pptx --outdir output/
```

**前提**: LibreOfficeがインストールされていること。

---

## リファレンス

- `references/pptx-guide.md`: レイアウト・プレースホルダーの詳細
- `references/talk-styles.md`: トークスクリプトの文体定義
- `references/tts-plugins.md`: TTSプラグインの追加方法
