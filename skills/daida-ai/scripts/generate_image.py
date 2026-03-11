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


def generate_image(
    prompt: str,
    model: str = "gemini-3-pro-image-preview",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    output_path: str = "output.png",
) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    url = f"{API_BASE}/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
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
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"API error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)

    # Extract image from response
    candidates = result.get("candidates", [])
    if not candidates:
        print("Error: No candidates in response.", file=sys.stderr)
        print(json.dumps(result, indent=2), file=sys.stderr)
        sys.exit(1)

    text_parts = []
    image_saved = False

    for part in candidates[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            mime_type = part["inlineData"].get("mimeType", "image/png")
            ext = mime_type.split("/")[-1] if "/" in mime_type else "png"
            # Adjust output extension if needed
            if not output_path.endswith(f".{ext}"):
                base, _ = os.path.splitext(output_path)
                output_path = f"{base}.{ext}"

            img_data = base64.b64decode(part["inlineData"]["data"])
            with open(output_path, "wb") as f:
                f.write(img_data)
            image_saved = True
            print(f"Image saved: {output_path} ({len(img_data)} bytes)")
        elif "text" in part:
            text_parts.append(part["text"])

    if text_parts:
        print(f"Model text: {' '.join(text_parts)}")

    if not image_saved:
        print("Warning: No image data found in response.", file=sys.stderr)
        print(json.dumps(result, indent=2, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

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
    args = parser.parse_args()

    # Resolve model alias
    model = MODELS.get(args.model, args.model)

    generate_image(
        prompt=args.prompt,
        model=model,
        aspect_ratio=args.aspect_ratio,
        image_size=args.size,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
