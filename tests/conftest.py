"""共通fixtures: サンプルアウトライン、一時ディレクトリ、モックPPTX、MP3テストデータ"""

import pytest
from pathlib import Path
import tempfile
from PIL import Image


# ---------------------------------------------------------------------------
# MP3テストデータ構築ヘルパー
# ---------------------------------------------------------------------------

def build_mp3_frame(
    *,
    mpeg1: bool = True,
    bitrate_idx: int = 0b1001,
    audio_size: int = 16000,
) -> bytes:
    """テスト用MP3フレームヘッダ + ダミー音声データを構築する。

    Args:
        mpeg1: True=MPEG1(0xFB), False=MPEG2(0xF3)
        bitrate_idx: ビットレートインデックス（4bit）。MPEG1: 0b1001=128kbps, MPEG2: 0b1000=64kbps
        audio_size: フレームヘッダ以降の音声データサイズ（バイト）

    Returns:
        MP3フレームヘッダ + ゼロ埋めデータ

    期待デュレーション計算:
        duration_ms = (audio_size + 4) * 8 / (bitrate_kbps * 1000) * 1000
        ※ +4 はフレームヘッダ4バイト分（_estimate_mp3_duration_msは offset以降の全バイトを使う）
    """
    # byte0: 0xFF（sync）
    # byte1: MPEG1 Layer3 = 0xFB (11111011), MPEG2 Layer3 = 0xF3 (11110011)
    byte1 = 0xFB if mpeg1 else 0xF3
    # byte2: ビットレートインデックス(上位4bit) + サンプリングレート(00) + パディング(0) + チャネル(0)
    byte2 = (bitrate_idx << 4) & 0xF0
    # byte3: 0x00
    header = bytes([0xFF, byte1, byte2, 0x00])
    return header + b"\x00" * audio_size


def build_id3_header(tag_size: int = 0) -> bytes:
    """ID3v2ヘッダを構築する。

    Args:
        tag_size: ID3タグのデータサイズ（ヘッダ10バイトを含まない）

    Returns:
        10バイトのID3ヘッダ + ゼロ埋めタグデータ
    """
    # ID3v2.3, フラグ=0, サイズはsyncsafe integer
    s = tag_size
    size_bytes = bytes([
        (s >> 21) & 0x7F,
        (s >> 14) & 0x7F,
        (s >> 7) & 0x7F,
        s & 0x7F,
    ])
    return b"ID3" + bytes([0x03, 0x00, 0x00]) + size_bytes + b"\x00" * tag_size


# MPEG1 Layer3 128kbps のダミーMP3バイト列（テスト全体で共有）
# 0xFF 0xFB = sync + MPEG1/Layer3, 0x90 = bitrate_idx=0b1001(128kbps), 0x00 = padding
DUMMY_MP3_BYTES = build_mp3_frame(mpeg1=True, bitrate_idx=0b1001, audio_size=100)
DUMMY_MP3_BYTES_SHORT = build_mp3_frame(mpeg1=True, bitrate_idx=0b1001, audio_size=50)


@pytest.fixture
def dummy_mp3() -> bytes:
    """テスト用ダミーMP3バイト列（MPEG1 128kbps, 104bytes）"""
    return DUMMY_MP3_BYTES


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


@pytest.fixture
def sample_svg(tmp_output_dir) -> Path:
    """テスト用のSVGファイル（320x240）"""
    path = tmp_output_dir / "test_diagram.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240">'
        '<rect width="320" height="240" fill="#1E293B"/>'
        '<circle cx="160" cy="120" r="60" fill="#38BDF8"/>'
        "</svg>"
    )
    return path


# ---------------------------------------------------------------------------
# MP3 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mp3_mpeg1_128kbps() -> tuple[bytes, int]:
    """MPEG1 128kbps, 16000bytes音声データ。

    Returns:
        (mp3_data, expected_duration_ms)
        duration = (16000 + 4) * 8 / (128 * 1000) * 1000 = 1000.25 → 1000ms
    """
    data = build_mp3_frame(mpeg1=True, bitrate_idx=0b1001, audio_size=16000)
    expected_ms = int((len(data)) * 8 / (128 * 1000) * 1000)
    return data, expected_ms


@pytest.fixture
def mp3_mpeg2_64kbps() -> tuple[bytes, int]:
    """MPEG2 64kbps, 8000bytes音声データ。

    Returns:
        (mp3_data, expected_duration_ms)
        duration = (8000 + 4) * 8 / (64 * 1000) * 1000 = 1000.5 → 1000ms
    """
    data = build_mp3_frame(mpeg1=False, bitrate_idx=0b1000, audio_size=8000)
    expected_ms = int((len(data)) * 8 / (64 * 1000) * 1000)
    return data, expected_ms


@pytest.fixture
def mp3_with_id3_tag() -> tuple[bytes, int]:
    """ID3タグ付きMPEG1 128kbps。

    Returns:
        (mp3_data, expected_duration_ms)
        ID3タグ(10+100bytes)の後にMP3フレーム。デュレーションはフレーム部分のみで計算。
    """
    id3 = build_id3_header(tag_size=100)
    frame = build_mp3_frame(mpeg1=True, bitrate_idx=0b1001, audio_size=16000)
    data = id3 + frame
    audio_bytes = len(frame)  # ID3スキップ後のバイト数
    expected_ms = int(audio_bytes * 8 / (128 * 1000) * 1000)
    return data, expected_ms


@pytest.fixture
def mp3_no_frame_header() -> bytes:
    """MP3フレームヘッダが存在しないデータ。0を返すべき。"""
    return b"\x00" * 200
