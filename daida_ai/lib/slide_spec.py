"""スライド仕様JSONのデータモデルとバリデーション"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

VALID_TEMPLATES = {"tech", "casual", "formal"}
VALID_LAYOUTS = {
    "title_slide",
    "section_header",
    "title_and_content",
    "two_content",
    "title_only",
    "blank",
}


@dataclass
class TwoColumnContent:
    """2カラムレイアウトの片側コンテンツ"""

    heading: str
    body: list[str] = field(default_factory=list)


@dataclass
class SlideMetadata:
    """プレゼン全体のメタデータ"""

    title: str
    subtitle: str
    event: str
    template: str = "tech"

    def __post_init__(self):
        if self.template not in VALID_TEMPLATES:
            raise ValueError(
                f"template must be one of {VALID_TEMPLATES}, got '{self.template}'"
            )


@dataclass
class Slide:
    """1スライドの仕様"""

    layout: str
    title: str = ""
    subtitle: str | None = None
    body: list[str] | None = None
    left: TwoColumnContent | None = None
    right: TwoColumnContent | None = None
    note: str | None = None
    image: str | None = None

    def __post_init__(self):
        if self.layout not in VALID_LAYOUTS:
            raise ValueError(
                f"layout must be one of {VALID_LAYOUTS}, got '{self.layout}'"
            )


@dataclass
class SlideSpec:
    """スライド仕様全体"""

    metadata: SlideMetadata
    slides: list[Slide] = field(default_factory=list)


def _parse_two_column(data: dict | None) -> TwoColumnContent | None:
    if data is None:
        return None
    return TwoColumnContent(
        heading=data.get("heading", ""),
        body=data.get("body", []),
    )


def _parse_slide(data: dict) -> Slide:
    if "layout" not in data:
        raise ValueError("slide requires 'layout' field")
    image = data.get("image")
    if image is not None and not isinstance(image, str):
        raise ValueError(f"image must be a string or null, got {type(image).__name__}")
    return Slide(
        layout=data["layout"],
        title=data.get("title", ""),
        subtitle=data.get("subtitle"),
        body=data.get("body"),
        left=_parse_two_column(data.get("left")),
        right=_parse_two_column(data.get("right")),
        note=data.get("note"),
        image=image,
    )


def validate_slide_spec(data: dict) -> SlideSpec:
    """辞書をバリデーションしてSlideSpecに変換する。

    Raises:
        ValueError: 必須フィールド欠損や無効な値
    """
    if "metadata" not in data:
        raise ValueError("metadata is required")
    if "slides" not in data:
        raise ValueError("slides is required")

    meta_raw = data["metadata"]
    if "title" not in meta_raw:
        raise ValueError("metadata requires 'title' field")
    metadata = SlideMetadata(
        title=meta_raw["title"],
        subtitle=meta_raw.get("subtitle", ""),
        event=meta_raw.get("event", ""),
        template=meta_raw.get("template", "tech"),
    )

    slides = [_parse_slide(s) for s in data["slides"]]

    return SlideSpec(metadata=metadata, slides=slides)


def save_slide_spec(spec: SlideSpec, path: Path) -> None:
    """SlideSpecをJSONファイルに保存する。"""
    data = {
        "metadata": asdict(spec.metadata),
        "slides": [asdict(s) for s in spec.slides],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_slide_spec(path: Path) -> SlideSpec:
    """JSONファイルからSlideSpecを読み込む。

    Raises:
        FileNotFoundError: ファイルが存在しない
        ValueError: JSON解析またはバリデーションに失敗
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    return validate_slide_spec(data)
