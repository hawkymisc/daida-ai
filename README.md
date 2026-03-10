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

### 手順

**1. リポジトリをクローンする**

Claude Code の Skill として認識させるには、`~/.claude/skills/` 以下に配置するか、プロジェクト内の `.claude/skills/` に置く必要がある。

```bash
# プロジェクト内に配置する場合（推奨）
cd /path/to/your/project
git clone https://github.com/hawkymisc/daida-ai.git .claude/skills/daida-ai-repo

# または、グローバルに使いたい場合
git clone https://github.com/hawkymisc/daida-ai.git ~/.claude/skills/daida-ai-repo
```

> **ポイント**: Claude Code は `.claude/skills/<name>/SKILL.md` を自動検出してスキルとして登録する。

**2. Python依存パッケージをインストールする**

```bash
cd .claude/skills/daida-ai-repo   # または ~/.claude/skills/daida-ai-repo
bash .claude/skills/daida-ai/scripts/setup.sh
```

setup.sh は `.venv/` を作成し、必要なパッケージ（python-pptx, edge-tts, pydub 等）をインストールする。

### このリポジトリ自体をプロジェクトとして使う場合

リポジトリのルートで作業する場合はセットアップがシンプル:

```bash
git clone https://github.com/hawkymisc/daida-ai.git
cd daida-ai
bash .claude/skills/daida-ai/scripts/setup.sh
```

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
