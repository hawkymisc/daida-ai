# TTSプラグイン追加方法ガイド

## アーキテクチャ

```
tts_engine.py       # 抽象基底クラス TTSEngine
├── tts_edge.py     # edge-tts 実装
├── tts_voicevox.py # VOICEVOX API 実装
└── tts_xxx.py      # 新しいプラグイン（あなたが追加）
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
    choices=["edge", "voicevox", "xxx"],
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
