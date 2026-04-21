# TTSプラグイン追加方法ガイド

## アーキテクチャ

```
tts_engine.py           # 抽象基底クラス TTSEngine
├── tts_edge.py         # edge-tts 実装
├── tts_voicevox.py     # VOICEVOX API 実装
├── tts_elevenlabs.py   # ElevenLabs API 実装（Voice Clone対応）
├── tts_openai.py       # OpenAI TTS API 実装（互換サーバ対応）
└── tts_xxx.py          # 新しいプラグイン（あなたが追加）
```

## 新しいTTSプラグインの追加手順

### 1. 実装クラスを作成

`daida_ai/lib/tts_xxx.py`:

```python
from daida_ai.lib.tts_engine import TTSEngine
from pathlib import Path

class XxxTTSEngine(TTSEngine):
    async def synthesize(
        self, text: str, output_path: Path, voice: str | None = None
    ) -> Path:
        # 音声合成ロジック
        # output_pathにファイルを書き出す
        return output_path

    def available_voices(self) -> list[str]:
        return ["voice1", "voice2"]
```

### 2. ファクトリ関数に登録

`daida_ai/lib/tts_engine.py` の `get_engine()` に分岐を追加:

```python
elif name == "xxx":
    from daida_ai.lib.tts_xxx import XxxTTSEngine
    return XxxTTSEngine()
```

### 3. テストを作成

`tests/test_tts_xxx.py`:
- `synthesize()` が正常にファイルを生成するか
- `available_voices()` が非空リストを返すか
- エラーハンドリング（APIダウン等）

### 4. CLIスクリプトの更新

`synthesize_audio.py` の `--engine` choices に追加:

```python
parser.add_argument(
    "--engine",
    choices=["edge", "voicevox", "elevenlabs", "openai", "xxx"],
    ...
)
```

## 現在のプラグイン

### edge-tts (デフォルト)
- **依存**: `edge-tts` パッケージ
- **特徴**: 無料、インターネット接続が必要、高品質な日本語音声
- **デフォルト音声**: `ja-JP-NanamiNeural`

### VOICEVOX
- **依存**: `httpx` パッケージ、VOICEVOX Engine (localhost:50021)
- **特徴**: ローカル実行、キャラクター音声、感情パラメータ対応
- **デフォルト音声**: Speaker ID 1 (ずんだもん)

### ElevenLabs
- **依存**: `httpx` パッケージ
- **環境変数**: `ELEVENLABS_API_KEY`（必須）、`ELEVENLABS_API_BASE`（任意）
- **特徴**: 高品質クラウドTTS。`--voice` に自身のVoice Cloneの`voice_id`を指定して利用可能
- **デフォルト音声**: Rachel (`21m00Tcm4TlvDq8ikWAM`)
- **デフォルトモデル**: `eleven_multilingual_v2`

### OpenAI
- **依存**: `httpx` パッケージ
- **環境変数**: `OPENAI_API_KEY`（必須）、`OPENAI_API_BASE`（互換サーバ用、任意）、`OPENAI_TTS_MODEL`（任意）
- **特徴**: OpenAI公式は `alloy` 等のプリセット音声のみ。OpenAI互換サーバ利用時は `--voice` にカスタム音声名を指定可能
- **デフォルト音声**: `alloy`
- **デフォルトモデル**: `tts-1`

---

## APIキー / 環境変数の設定方法（ユーザー向け）

クラウドTTSエンジン（ElevenLabs / OpenAI）は環境変数経由でAPIキーを受け取る。
CLI引数やコード内にキーを直書きしてはいけない。

### 認識する環境変数一覧

| 変数 | 用途 | 必須 |
|------|------|------|
| `ELEVENLABS_API_KEY` | ElevenLabs APIキー | ElevenLabs利用時 |
| `ELEVENLABS_API_BASE` | APIベースURL上書き（プロキシ等） | 任意 |
| `OPENAI_API_KEY` | OpenAI APIキー | OpenAI利用時 |
| `OPENAI_API_BASE` | APIベースURL上書き（互換サーバ接続時） | 任意 |
| `OPENAI_TTS_MODEL` | モデル名上書き（例: `tts-1-hd`） | 任意 |

### 設定手順（いずれか1つ）

#### A. 今回のシェルセッションのみ

```bash
export ELEVENLABS_API_KEY="sk_..."
export OPENAI_API_KEY="sk-..."
```

ターミナルを閉じると失われる。1回限りの動作確認向け。

#### B. 永続化（推奨）

`~/.bashrc` / `~/.zshrc` に追記:

```bash
echo 'export ELEVENLABS_API_KEY="sk_..."' >> ~/.bashrc
source ~/.bashrc
```

#### C. `.env` ファイル

プロジェクトディレクトリに `.env` を作成:

```
ELEVENLABS_API_KEY=sk_...
OPENAI_API_KEY=sk-...
```

実行前に読み込む（`.gitignore` に `.env` を追加することが前提）:

```bash
set -a && source .env && set +a
```

### APIキー発行手順

- **ElevenLabs**: https://elevenlabs.io/app/settings/api-keys → 「Create API Key」
- **OpenAI**: https://platform.openai.com/api-keys → 「Create new secret key」

### 動作確認

```bash
# 値ではなく「設定されているか」だけ確認する（値を画面/ログに出さない）
test -n "${ELEVENLABS_API_KEY:-}" && echo "ELEVENLABS_API_KEY: set"
test -n "${OPENAI_API_KEY:-}" && echo "OPENAI_API_KEY: set"
```

### Voice Cloneのvoice_idを調べる（ElevenLabs）

1. https://elevenlabs.io/app/voice-lab を開く
2. 対象のVoice Cloneを選択
3. 表示された voice_id をコピー（例: `21m00Tcm4TlvDq8ikWAM`）
4. `--voice <voice_id>` で指定

### セキュリティ上の注意

- APIキーを**チャット履歴やコミットに残さない**。Claude Codeとのやり取りでは
  環境変数名（`ELEVENLABS_API_KEY` など）だけを指示し、値は送信しない。
- `.env` を使う場合は `.gitignore` に必ず追加。
- キー漏洩の疑いがある場合は各プロバイダの管理画面から即時 revoke する。
