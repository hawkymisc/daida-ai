"""スライド仕様(SlideSpec) → python-pptx Presentationへの変換"""

from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from pptx import Presentation
from pptx.util import Inches, Pt, Emu

from daida_ai.lib.slide_spec import SlideSpec, Slide, TwoColumnContent

# 画像配置の定数 (EMU)
_SLIDE_W = Emu(12191695)
_SLIDE_H = Emu(6858000)
_IMG_MARGIN = Emu(457200)         # 左右マージン
_IMG_TOP = Emu(1600200)           # タイトル下の画像開始位置
_IMG_TOP_BLANK = Emu(457200)     # blankレイアウト時の画像開始位置
_IMG_MAX_W = _SLIDE_W - 2 * _IMG_MARGIN
_IMG_MAX_H = _SLIDE_H - _IMG_TOP - _IMG_MARGIN

# デフォルトテンプレートのレイアウトインデックス
_DEFAULT_LAYOUT_IDX = {
    "title_slide": 0,
    "title_and_content": 1,
    "section_header": 2,
    "two_content": 3,
    "title_only": 5,
    "blank": 6,
}


def _find_layout(prs, layout_name: str):
    """レイアウトをインデックスまたは名前で取得する。"""
    idx = _DEFAULT_LAYOUT_IDX.get(layout_name)
    if idx is not None:
        try:
            return prs.slide_layouts[idx]
        except IndexError:
            pass

    name_map = {
        "title_slide": "Title Slide",
        "title_and_content": "Title and Content",
        "section_header": "Section Header",
        "two_content": "Two Content",
        "title_only": "Title Only",
        "blank": "Blank",
    }
    target_name = name_map.get(layout_name, layout_name)
    for layout in prs.slide_layouts:
        if layout.name == target_name:
            return layout

    return prs.slide_layouts[0]


def _get_placeholders(slide) -> dict:
    """スライドのplaceholdersをidx→placeholder の辞書として返す。"""
    return {ph.placeholder_format.idx: ph for ph in slide.placeholders}


def _set_notes(slide, text: str | None) -> None:
    """スライドにスピーカーノートを設定する。"""
    if text:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = text


def _insert_image(slide, image_path: str, *, is_blank: bool = False) -> None:
    """スライドに画像を挿入する。アスペクト比を維持してコンテンツ領域に収める。

    Raises:
        FileNotFoundError: 画像ファイルが存在しない
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with PILImage.open(str(path)) as img:
        img_w, img_h = img.size

    max_w = int(_IMG_MAX_W)
    top = int(_IMG_TOP_BLANK) if is_blank else int(_IMG_TOP)
    max_h = int(_SLIDE_H) - top - int(_IMG_MARGIN)

    # アスペクト比を維持してフィットさせる
    scale = min(max_w / img_w, max_h / img_h)
    width = Emu(int(img_w * scale))
    height = Emu(int(img_h * scale))

    # 水平中央, 垂直はコンテンツ領域内で中央
    left = Emu((int(_SLIDE_W) - int(width)) // 2)
    top_pos = Emu(top + (max_h - int(height)) // 2)

    slide.shapes.add_picture(str(path), left, top_pos, width, height)


def _add_title_slide(prs, spec: Slide) -> None:
    layout = _find_layout(prs, "title_slide")
    slide = prs.slides.add_slide(layout)
    phs = _get_placeholders(slide)
    if 0 in phs:
        phs[0].text = spec.title
    if spec.subtitle and 1 in phs:
        phs[1].text = spec.subtitle
    if spec.image:
        _insert_image(slide, spec.image)
    _set_notes(slide, spec.note)


def _add_section_header(prs, spec: Slide) -> None:
    layout = _find_layout(prs, "section_header")
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title:
        slide.shapes.title.text = spec.title
    if spec.image:
        _insert_image(slide, spec.image)
    _set_notes(slide, spec.note)


def _add_title_and_content(prs, spec: Slide) -> None:
    layout = _find_layout(prs, "title_and_content")
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title:
        slide.shapes.title.text = spec.title

    phs = _get_placeholders(slide)
    if spec.body and 1 in phs:
        tf = phs[1].text_frame
        tf.clear()
        for i, item in enumerate(spec.body):
            if i == 0:
                tf.paragraphs[0].text = item
            else:
                p = tf.add_paragraph()
                p.text = item

    if spec.image:
        _insert_image(slide, spec.image)
    _set_notes(slide, spec.note)


def _add_two_content(prs, spec: Slide) -> None:
    layout = _find_layout(prs, "two_content")
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title:
        slide.shapes.title.text = spec.title

    phs = _get_placeholders(slide)

    if spec.left and 1 in phs:
        tf = phs[1].text_frame
        tf.clear()
        tf.paragraphs[0].text = spec.left.heading
        tf.paragraphs[0].font.bold = True
        for item in spec.left.body:
            p = tf.add_paragraph()
            p.text = item

    if spec.right and 2 in phs:
        tf = phs[2].text_frame
        tf.clear()
        tf.paragraphs[0].text = spec.right.heading
        tf.paragraphs[0].font.bold = True
        for item in spec.right.body:
            p = tf.add_paragraph()
            p.text = item

    _set_notes(slide, spec.note)


def _add_title_only(prs, spec: Slide) -> None:
    layout = _find_layout(prs, "title_only")
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title:
        slide.shapes.title.text = spec.title
    if spec.image:
        _insert_image(slide, spec.image)
    _set_notes(slide, spec.note)


def _add_blank(prs, spec: Slide) -> None:
    layout = _find_layout(prs, "blank")
    slide = prs.slides.add_slide(layout)
    if spec.image:
        _insert_image(slide, spec.image, is_blank=True)
    _set_notes(slide, spec.note)


_BUILDERS = {
    "title_slide": _add_title_slide,
    "section_header": _add_section_header,
    "title_and_content": _add_title_and_content,
    "two_content": _add_two_content,
    "title_only": _add_title_only,
    "blank": _add_blank,
}


def build_presentation(spec: SlideSpec, template_path: str | None = None):
    """SlideSpecからpython-pptx Presentationを生成する。

    Args:
        spec: スライド仕様
        template_path: カスタムテンプレートPPTXのパス（Noneでデフォルト）

    Returns:
        python-pptx Presentation オブジェクト
    """
    prs = Presentation(template_path)

    for slide_spec in spec.slides:
        builder = _BUILDERS.get(slide_spec.layout)
        if builder:
            builder(prs, slide_spec)

    return prs
