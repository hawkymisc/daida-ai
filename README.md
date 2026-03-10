# 代打AI

LT登壇を代打してくれる Claude Code Agent Skill。

テーマを伝えるだけで、アウトライン → スライド → トークスクリプト → 音声ナレーション付きPPTXまで自動生成する。

## 機能概要

1. テーマからMarkdownアウトラインを生成する
2. アウトラインをスライド仕様JSON（レイアウト・内容・台本）に充実化する
3. JSONからPPTXスライドを生成する（tech / casual / formal テンプレート対応）
4. スピーカーノート（台本）を文体指定で再生成できる
5. トークスクリプトを音声合成してPPTXに埋め込む（edge-tts / VOICEVOX 対応）

## 対応フォーマット

- PPTX（PowerPoint / LibreOffice Impress）
- ODP（LibreOffice インストール時のみ）

## サンプル

`samples/presentation.pptx` — 代打AI自身を使って生成した15分LT資料（20スライド）

---

## インストール

### 前提条件

- Python 3.11 以上
- [Claude Code](https://claude.ai/code) がインストール済みであること
- （音声合成に VOICEVOX を使う場合）[VOICEVOX Engine](https://voicevox.hiroshiba.jp/) が `http://localhost:50021` で起動していること

### 方法A: このリポジトリをそのまま使う（最もシンプル）

```bash
git clone https://github.com/hawkymisc/daida-ai.git
cd daida-ai
bash .claude/skills/daida-ai/scripts/setup.sh
```

`daida-ai/` を Claude Code のプロジェクトルートとして開けば、`.claude/skills/daida-ai/SKILL.md` が自動検出されてスキルが有効になる。

### 方法B: 既存プロジェクトに組み込む

スクリプトは `daida_ai` Python パッケージに依存するため、**リポジトリ本体ごとクローン**してから Python パッケージをインストールし、スキルディレクトリを登録する必要がある。

```bash
# 1. リポジトリを永続的な場所にクローン
git clone https://github.com/hawkymisc/daida-ai.git ~/.local/share/daida-ai

# 2. daida_ai パッケージをプロジェクトの venv にインストール
#    （先にプロジェクトの venv を activate しておく）
pip install "~/.local/share/daida-ai[voicevox]"

# 3. スキルディレクトリをプロジェクトに登録
mkdir -p /path/to/your/project/.claude/skills
cp -r ~/.local/share/daida-ai/.claude/skills/daida-ai \
    /path/to/your/project/.claude/skills/
```

> **ポイント**: `setup.sh` は `pyproject.toml` のある場所を `PROJECT_ROOT` として自動検出するため、方法Aでない場合は `pip install` で直接インストールする。

---

## 使い方

セットアップ後、プロジェクトのディレクトリで Claude Code を起動して:

```
/daida-ai テーマを入力してください
```

または自然言語で:

```
LT資料を作りたい。テーマは「Rustの所有権をRubyistに説明する」、5分、社内勉強会向け
```

Claudeが対話的にヒアリングしながらステップを進める。

### ステップの流れ

```
Step 1   : アウトライン生成（Claude がMarkdown生成）
Step 1.5 : コンテンツ充実化（Claude がスライド仕様JSONを生成）
Step 2   : PPTX生成（python-pptxでスライドファイルを出力）
Step 3   : トークスクリプト更新（任意・文体指定可）
Step 4   : 音声合成（edge-tts または VOICEVOX）
Step 5   : 音声埋め込み（PPTXにMP3を埋め込む）
```

出力はデフォルトで `./output/` に保存される。

---

## 開発

```bash
# テスト実行
source .venv/bin/activate
pytest tests/

# テンプレートPPTX再生成
python .claude/skills/daida-ai/scripts/create_templates.py
```
