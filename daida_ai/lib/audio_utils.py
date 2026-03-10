"""音声フォーマット変換ユーティリティ"""

from __future__ import annotations

from pathlib import Path
from pydub import AudioSegment


def wav_to_mp3(input_path: Path, output_path: Path, bitrate: str = "192k") -> Path:
    """WAVファイルをMP3に変換する。

    Args:
        input_path: 入力WAVファイルパス
        output_path: 出力MP3ファイルパス
        bitrate: MP3ビットレート（デフォルト192k）

    Returns:
        出力MP3ファイルパス
    """
    audio = AudioSegment.from_wav(str(input_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(output_path), format="mp3", bitrate=bitrate)
    return output_path


def ensure_mp3(input_path: Path) -> Path:
    """入力ファイルがWAVの場合MP3に変換し、MP3はそのまま返す。

    ファイルのヘッダを確認して判定する。
    変換時は同じディレクトリに.mp3拡張子で保存し、元のWAVは削除する。

    Args:
        input_path: 入力音声ファイルパス

    Returns:
        MP3ファイルパス
    """
    header = input_path.read_bytes()[:4]

    # WAV: RIFF header
    if header[:4] == b"RIFF":
        mp3_path = input_path.with_suffix(".mp3")
        wav_to_mp3(input_path, mp3_path)
        input_path.unlink()
        return mp3_path

    # MP3: sync word 0xFF 0xFB/0xF3/0xF2 or ID3 tag
    if header[:2] == b"\xff\xfb" or header[:3] == b"ID3":
        return input_path

    # 不明なフォーマットはそのまま返す
    return input_path
