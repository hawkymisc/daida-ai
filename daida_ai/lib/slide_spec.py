"""スライド仕様JSONのデータモデルとバリデーション"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

MAX_SLIDES = 20
MIN_SLIDES = 1
MAX_BODY_ITEMS = 8
MIN_BODY_ITEMS = 1
MAX_TALK_DURATION_SEC = 300
CHARS_PER_SECOND = 5.0
NOTE_EXEMPT_LAYOUTS = {"title_slide", "section_header"}
TITLE_EXEMPT_LAYOUTS = {"blank"}

MAX_TITLE_LENGTH = 100
MAX_SUBTITLE_LENGTH = 200
MAX_BODY_ITEM_LENGTH = 200

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


def validate_slide_spec(
    data: dict,
    *,
    max_slides: int = MAX_SLIDES,
    max_talk_duration_sec: float = MAX_TALK_DURATION_SEC,
) -> SlideSpec:
    """辞書をバリデーションしてSlideSpecに変換する。

    Args:
        data: スライド仕様の辞書
        max_slides: スライド枚数の上限（登壇形式に応じて変更）
        max_talk_duration_sec: 推定発話時間の上限（秒）

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

    # --- A1 ガードレール ---
    # スライド枚数チェック
    if len(slides) < MIN_SLIDES:
        raise ValueError(
            f"slides must have at least {MIN_SLIDES} slide, got {len(slides)}"
        )
    if len(slides) > max_slides:
        raise ValueError(
            f"slides must have at most {max_slides} slides, got {len(slides)}"
        )

    # 各スライドのバリデーション
    for i, slide in enumerate(slides):
        # タイトル非空チェック（blankレイアウトは免除）
        if slide.layout not in TITLE_EXEMPT_LAYOUTS:
            if not slide.title or not slide.title.strip():
                raise ValueError(
                    f"slide[{i}] requires a non-empty title"
                )

        # テキスト長チェック
        if slide.title and len(slide.title) > MAX_TITLE_LENGTH:
            raise ValueError(
                f"slide[{i}] title exceeds {MAX_TITLE_LENGTH} chars "
                f"(got {len(slide.title)})"
            )
        if slide.subtitle and len(slide.subtitle) > MAX_SUBTITLE_LENGTH:
            raise ValueError(
                f"slide[{i}] subtitle exceeds {MAX_SUBTITLE_LENGTH} chars "
                f"(got {len(slide.subtitle)})"
            )

        # ノート必須チェック（title_slide, section_header以外）
        if slide.layout not in NOTE_EXEMPT_LAYOUTS:
            if not slide.note or not slide.note.strip():
                raise ValueError(
                    f"slide[{i}] (layout={slide.layout}) requires a non-empty note"
                )

        # 情報密度チェック（bodyがある場合のみ）
        if slide.body is not None:
            if len(slide.body) < MIN_BODY_ITEMS:
                raise ValueError(
                    f"slide[{i}] body must have at least {MIN_BODY_ITEMS} item, "
                    f"got {len(slide.body)}"
                )
            if len(slide.body) > MAX_BODY_ITEMS:
                raise ValueError(
                    f"slide[{i}] body must have at most {MAX_BODY_ITEMS} items, "
                    f"got {len(slide.body)}"
                )
            for j, item in enumerate(slide.body):
                if len(item) > MAX_BODY_ITEM_LENGTH:
                    raise ValueError(
                        f"slide[{i}] body[{j}] exceeds {MAX_BODY_ITEM_LENGTH} chars "
                        f"(got {len(item)})"
                    )

        # 2カラムレイアウトのbody検証
        for col_name, col in [("left", slide.left), ("right", slide.right)]:
            if col is not None and col.body:
                if len(col.body) > MAX_BODY_ITEMS:
                    raise ValueError(
                        f"slide[{i}] {col_name}.body must have at most "
                        f"{MAX_BODY_ITEMS} items, got {len(col.body)}"
                    )

    # 推定発話時間チェック
    total_chars = sum(
        len(s.note.strip()) for s in slides if s.note
    )
    estimated_duration_sec = total_chars / CHARS_PER_SECOND
    if estimated_duration_sec > max_talk_duration_sec:
        raise ValueError(
            f"estimated talk duration {estimated_duration_sec:.1f}s exceeds "
            f"maximum {max_talk_duration_sec}s"
        )

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
