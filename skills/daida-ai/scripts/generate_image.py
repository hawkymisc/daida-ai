#!/usr/bin/env python3
"""Nano Banana (Pro) image generation via Gemini API.

Usage:
    python generate_image.py --prompt "A cat on the moon" [OPTIONS]

Options:
    --prompt       Text prompt for image generation (required)
    --model        Model ID (default: gemini-3-pro-image-preview)
    --output       Output file path (default: output.png)
    --aspect-ratio Aspect ratio (default: 1:1)
    --size         Image size: 512, 1K, 2K, 4K (default: 1K)

Environment:
    GEMINI_API_KEY  Required. Your Google AI API key.
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error


API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

MODELS = {
    "pro": "gemini-3-pro-image-preview",
    "flash": "gemini-3.1-flash-image-preview",
    "legacy": "gemini-2.5-flash-image",
}

VALID_ASPECT_RATIOS = [
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1",
    "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9",
]

VALID_SIZES = ["512", "1K", "2K", "4K"]

DEFAULT_TIMEOUT = 60


class ImageGenerationError(Exception):
    """画像生成処理中のエラー"""


def generate_image(
    prompt: str,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    output_path: str = "output.png",
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Gemini APIで画像を生成し、ファイルに保存する。

    Args:
        prompt: 画像生成プロンプト
        model: Geminiモデル名
        aspect_ratio: アスペクト比
        image_size: 画像サイズ
        output_path: 出力ファイルパス
        timeout: APIリクエストタイムアウト（秒）

    Returns:
        保存した画像ファイルのパス

    Raises:
        ImageGenerationError: API呼び出しや画像抽出に失敗した場合
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ImageGenerationError("GEMINI_API_KEY environment variable is not set.")

    url = f"{API_BASE}/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise ImageGenerationError(f"API error {e.code}: {body}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ImageGenerationError(f"Network error: {e}") from e

    # Extract image from response
    candidates = result.get("candidates", [])
    if not candidates:
        raise ImageGenerationError(
            f"No candidates in response: {json.dumps(result, indent=2)}"
        )

    text_parts = []
    image_saved = False

    for candidate in candidates:
        if image_saved:
            break
        for part in candidate.get("content", {}).get("parts", []):
            if "inlineData" in part:
                mime_type = part["inlineData"].get("mimeType", "image/png")
                ext = mime_type.split("/")[-1] if "/" in mime_type else "png"
                # Adjust output extension if needed
                if not output_path.endswith(f".{ext}"):
                    base, _ = os.path.splitext(output_path)
                    output_path = f"{base}.{ext}"

                img_data = base64.b64decode(part["inlineData"]["data"])
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_data)
                image_saved = True
                print(f"Image saved: {output_path} ({len(img_data)} bytes)")
            elif "text" in part:
                text_parts.append(part["text"])

    if text_parts:
        print(f"Model text: {' '.join(text_parts)}")

    if not image_saved:
        raise ImageGenerationError(
            f"No image data found in response: "
            f"{json.dumps(result, indent=2, ensure_ascii=False)}"
        )

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Nano Banana image generation")
    parser.add_argument("--prompt", required=True, help="Image generation prompt")
    parser.add_argument(
        "--model",
        default="gemini-3-pro-image-preview",
        help=f"Model ID or alias: {', '.join(MODELS.keys())} (default: pro)",
    )
    parser.add_argument("--output", default="output.png", help="Output file path")
    parser.add_argument(
        "--aspect-ratio",
        default="1:1",
        choices=VALID_ASPECT_RATIOS,
        help="Aspect ratio (default: 1:1)",
    )
    parser.add_argument(
        "--size",
        default="1K",
        choices=VALID_SIZES,
        help="Image size (default: 1K)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"API request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    # Resolve model alias
    model = MODELS.get(args.model, args.model)

    try:
        generate_image(
            prompt=args.prompt,
            model=model,
            aspect_ratio=args.aspect_ratio,
            image_size=args.size,
            output_path=args.output,
            timeout=args.timeout,
        )
    except ImageGenerationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
