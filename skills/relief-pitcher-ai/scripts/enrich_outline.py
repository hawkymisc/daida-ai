#!/usr/bin/env python3
"""Step1.5: スライド仕様JSONの保存とバリデーション

LLM（Claude）がアウトラインを充実化して生成したJSONを受け取り、
バリデーション後にファイルに保存する。
"""

import argparse
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from daida_ai.lib.slide_spec import validate_slide_spec, save_slide_spec

# 持ち時間 → バリデーションパラメータの目安
# 1スライドあたり15秒〜30秒を想定（表紙・セクション含む）
_SLIDES_PER_MINUTE = 4  # 1分あたり最大4枚


def _duration_to_limits(duration_min: int) -> dict:
    """持ち時間（分）からバリデーション上限を算出する。"""
    return {
        "max_slides": max(duration_min * _SLIDES_PER_MINUTE, 5),
        "max_talk_duration_sec": float(duration_min * 60),
    }


def main():
    parser = argparse.ArgumentParser(
        description="スライド仕様JSONをバリデーションして保存する"
    )
    parser.add_argument("output", type=Path, help="出力ファイルパス (.json)")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="標準入力からJSONを読み込む",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="入力ファイルからJSONを読み込む",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="持ち時間（分）。バリデーション上限を自動算出する（デフォルト: 5）",
    )
    args = parser.parse_args()

    if args.stdin:
        raw = sys.stdin.read()
    elif args.input:
        raw = args.input.read_text(encoding="utf-8")
    else:
        print("Error: --stdin or --input required", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    limits = _duration_to_limits(args.duration)
    try:
        spec = validate_slide_spec(data, **limits)
    except ValueError as e:
        print(f"Error: Validation failed: {e}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_slide_spec(spec, args.output)
    print(
        f"Slide spec saved: {args.output} ({len(spec.slides)} slides, "
        f"duration={args.duration}min, max_slides={limits['max_slides']})"
    )


if __name__ == "__main__":
    main()
