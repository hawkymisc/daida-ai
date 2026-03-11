"""共通fixtures: サンプルアウトライン、一時ディレクトリ、モックPPTX"""

import pytest
from pathlib import Path
import tempfile
from PIL import Image


@pytest.fixture
def sample_outline_md() -> str:
    """基本的なLTアウトラインのMarkdown"""
    return """\
# Claude Codeで変わる開発体験

## 導入: なぜClaude Codeなのか
- AIペアプログラミングの進化
- 従来のコード補完との違い
- 開発速度の劇的な向上

## 本題1: 基本機能
- ファイル操作とコード生成
- テスト駆動開発の自動化
- Git操作の統合

## 本題2: 実践テクニック
- CLAUDE.mdによるプロジェクト設定
- スキルの活用
- MCP連携

## まとめ
- 今日のポイント3つ
- 始め方ガイド
"""


@pytest.fixture
def minimal_outline_md() -> str:
    """最小限のアウトライン（タイトルのみ）"""
    return "# タイトルだけのプレゼン\n"


@pytest.fixture
def nested_outline_md() -> str:
    """ネストされた箇条書きを含むアウトライン"""
    return """\
# 深いネストのあるプレゼン

## セクション1
- 項目A
  - サブ項目A-1
  - サブ項目A-2
- 項目B

## セクション2
- 項目C
"""


@pytest.fixture
def tmp_output_dir():
    """一時出力ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image(tmp_output_dir) -> Path:
    """テスト用の小さなPNG画像（320x240）"""
    path = tmp_output_dir / "test_image.png"
    img = Image.new("RGB", (320, 240), color=(70, 130, 180))
    img.save(str(path))
    return path


@pytest.fixture
def wide_image(tmp_output_dir) -> Path:
    """テスト用のワイド画像（800x200）"""
    path = tmp_output_dir / "wide_image.png"
    img = Image.new("RGB", (800, 200), color=(200, 100, 50))
    img.save(str(path))
    return path


@pytest.fixture
def tall_image(tmp_output_dir) -> Path:
    """テスト用の縦長画像（200x600）"""
    path = tmp_output_dir / "tall_image.png"
    img = Image.new("RGB", (200, 600), color=(50, 200, 100))
    img.save(str(path))
    return path
