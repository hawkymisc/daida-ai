# 代打AI

LT登壇を代打してくれる Claude Code Plugin.

## 機能概要

1. 登壇テーマを入力したら、発表のアウトラインをMarkdownで出力・保存する
2. 当該Markdownに基づき、スライド資料を作成する
   - スライド資料はPowerPointで作成する
   - 事前に定義されたスライドテンプレートのデザインに従い作成する
   - スライドは白紙からではなく、スライドレイアウトを選択して作成する
   - スライドタイトルやテキスト本文はアウトライン表示で確認できるように設定する
3. スライド資料のnote欄にトークスクリプト(台本)を記入する
   - スクリプトは、カジュアル、キーノートなど複数のスタイルで文体を選べる
4. トークスクリプトを読み上げた音声を合成する
5. 上記音声合成をスライドに埋め込む

## 対応フォーマット

pptx および odp(Open Document Presentation)

## インストール

### 前提条件

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) がインストール済み
- Python 3.11以上

### Step 1: マーケットプレイスを追加

Claude Code 内で以下を実行:

```
/plugin marketplace add hawkymisc/daida-ai
```

### Step 2: プラグインをインストール

```
/plugin install daida-ai@hawkymisc-daida-ai
```

### Step 3: セットアップ

初回使用時、`/daida-ai:daida-ai` を実行するとセットアップスクリプトの実行を求められます。
Claude の指示に従い、以下のコマンドを承認してください:

```bash
bash <plugin-dir>/skills/daida-ai/scripts/setup.sh
```

これにより Python 仮想環境の作成と依存パッケージのインストールが行われます。

## 使い方

Claude Code で以下のように呼び出します:

```
/daida-ai:daida-ai
```

または、自然言語で依頼できます:

- 「LTの資料を作って」
- 「プレゼンを作成して」
- 「代打で登壇資料を作って」

### ワークフロー

対話形式で以下を聞かれます:

1. **テーマ**: 何について話すか
2. **対象者**: 誰に向けたLTか
3. **持ち時間**: 何分か（デフォルト5分）
4. **テンプレート**: `tech` / `casual` / `formal`
5. **TTSエンジン**: `edge`（デフォルト） / `voicevox`

全自動で、アウトライン → スライド → トークスクリプト → 音声合成 → 音声埋め込み まで実行されます。

## 音声合成エンジン

| エンジン | 特徴 | 備考 |
|----------|------|------|
| edge-tts | Microsoft Edge TTS。インストール不要 | デフォルト |
| VOICEVOX | ずんだもん等のキャラクター音声 | [VOICEVOX Engine](https://voicevox.hiroshiba.jp/) の起動が必要 |

## 注意事項

### LibreOffice Impress での再生について

自動ページ送り（スライドショー中に音声終了後に自動で次のスライドに進む機能）は **PowerPoint（Windows / macOS）でのみ動作** します。

**LibreOffice Impress では自動ページ送りが動作しません**。これは LibreOffice が PPTX 内のタイミング設定（`advTm`）を正しく処理しない既知の制限によるものです（[Bug 101527](https://bugs.documentfoundation.org/show_bug.cgi?id=101527)）。

LibreOffice で再生する場合は、以下のいずれかで対応してください:
- **手動**でスライドを送る（クリックまたは矢印キー）
- LibreOffice 上で「スライド切り替え」パネルから各スライドの自動切り替え時間を手動設定する

## ライセンス

MIT
