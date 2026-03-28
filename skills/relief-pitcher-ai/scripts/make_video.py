#!/usr/bin/env python3
"""Step7: 動画生成

PPTXと音声ファイルからMP4動画を生成する。
各スライドを画像化し、音声の実尺に合わせて動画クリップを作成・結合する。
生成後にMP4バリデーションを自動実行する。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.video_builder import build_video, probe_video, validate_video


def main():
    parser = argparse.ArgumentParser(
        description="PPTXと音声ファイルからMP4動画を生成する"
    )
    parser.add_argument("input", type=Path, help="入力PPTXファイルパス")
    parser.add_argument("audio_dir", type=Path, help="音声ファイルディレクトリ")
    parser.add_argument("output", type=Path, help="出力MP4ファイルパス")
    parser.add_argument(
        "--silent-duration",
        type=float,
        default=3.0,
        help="音声なしスライドの表示秒数（デフォルト3.0）",
    )
    parser.add_argument(
        "--audio-padding",
        type=float,
        default=1.5,
        help="音声ありスライドの末尾パディング秒数（デフォルト1.5）",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="フレームレート（デフォルト30）",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="生成後のバリデーションをスキップする",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    if not args.audio_dir.is_dir():
        print(f"Error: {args.audio_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # --- 動画生成 ---
    build_result = build_video(
        args.input,
        args.audio_dir,
        args.output,
        silent_duration=args.silent_duration,
        audio_padding=args.audio_padding,
        fps=args.fps,
    )
    print(f"Video created: {build_result.video_path}")
    print(f"  Slides: {build_result.slide_count} ({build_result.audio_count} with audio)")
    print(f"  Expected duration: {build_result.expected_duration:.1f}s")

    if args.skip_validation:
        return

    # --- 自動バリデーション ---
    print("\n--- MP4 Validation ---")

    try:
        info = probe_video(build_result.video_path)
        print(f"  Duration : {info.duration:.1f}s")
        print(f"  Size     : {info.file_size / 1024 / 1024:.1f}MB")
        print(f"  Video    : {info.width}x{info.height} {info.video_codec}")
        if info.audio_codec:
            print(f"  Audio    : {info.audio_codec} {info.audio_sample_rate}Hz")
        else:
            print("  Audio    : none")
        print(f"  Streams  : {info.nb_streams}")
    except Exception as e:
        print(f"  Probe failed: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_video(
        build_result.video_path,
        expected_duration=build_result.expected_duration,
    )

    if errors:
        print(f"\n  [FAIL] {len(errors)} validation error(s):")
        for err in errors:
            print(f"    - {err}")
        sys.exit(1)
    else:
        print("\n  [PASS] All validation checks passed")


if __name__ == "__main__":
    main()
