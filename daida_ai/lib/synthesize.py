"""音声合成パイプライン

スピーカーノートのリストからTTSエンジンで音声ファイルを生成する。
空ノートはスキップし、slide_NNN.mp3 形式で出力する。
"""

from __future__ import annotations

from pathlib import Path

from daida_ai.lib.tts_engine import TTSEngine, get_engine


async def synthesize_notes(
    notes: list[str],
    output_dir: Path,
    *,
    engine: TTSEngine | None = None,
    engine_name: str | None = None,
    voice: str | None = None,
) -> list[Path | None]:
    """ノートリストから音声ファイルを生成する。

    Args:
        notes: スライドごとのスピーカーノート
        output_dir: 音声ファイル出力ディレクトリ
        engine: TTSエンジンインスタンス（engine_nameと排他）
        engine_name: エンジン名（"edge" / "voicevox"）
        voice: 音声名（Noneでエンジンのデフォルト）

    Returns:
        スライドごとの音声ファイルパス（空ノートはNone）

    Raises:
        ValueError: engineもengine_nameも指定されない場合
    """
    if engine is None and engine_name is None:
        raise ValueError("engine or engine_name must be specified")

    if engine is None:
        engine = get_engine(engine_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[Path | None] = []

    for i, note in enumerate(notes):
        if not note.strip():
            results.append(None)
            continue
        output_path = output_dir / f"slide_{i:03d}.mp3"
        await engine.synthesize(note, output_path, voice=voice)
        results.append(output_path)

    return results
