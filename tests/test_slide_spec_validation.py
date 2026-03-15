"""TDD: slide_spec バリデーション強化テスト

レイアウト-フィールド整合性、テキスト長チェック、
その他の未実装バリデーションを検証する。
"""

import warnings

import pytest

from daida_ai.lib.slide_spec import (
    validate_slide_spec,
    MAX_TITLE_LENGTH,
    MAX_SUBTITLE_LENGTH,
    MAX_BODY_ITEM_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_HEADING_LENGTH,
)


def _spec(slides, **meta_overrides):
    """テスト用の最小限スライド仕様を作成するヘルパー"""
    meta = {"title": "テスト", "subtitle": "", "event": ""}
    meta.update(meta_overrides)
    return {"metadata": meta, "slides": slides}


def _slide(layout, **kwargs):
    """テスト用スライドを作成するヘルパー"""
    s = {"layout": layout}
    s.update(kwargs)
    return s


# ---------------------------------------------------------------------------
# 1. レイアウト-フィールド整合性
# ---------------------------------------------------------------------------
class Testレイアウトフィールド整合性:
    """各レイアウトに必須/不要なフィールドの検証"""

    def test_two_contentにleftがないとValueError(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            right={"heading": "右", "body": ["a"]},
            note="ノート",
        )])
        with pytest.raises(ValueError, match="left.*required"):
            validate_slide_spec(spec)

    def test_two_contentにrightがないとValueError(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "左", "body": ["a"]},
            note="ノート",
        )])
        with pytest.raises(ValueError, match="right.*required"):
            validate_slide_spec(spec)

    def test_two_contentにleftとright両方あれば通る(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "左", "body": ["a"]},
            right={"heading": "右", "body": ["b"]},
            note="ノート",
        )])
        result = validate_slide_spec(spec)
        assert result.slides[0].left is not None

    def test_title_and_contentにbodyがないとValueError(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト", note="ノート",
        )])
        with pytest.raises(ValueError, match="body.*required"):
            validate_slide_spec(spec)

    def test_title_and_contentにbodyがあれば通る(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト",
            body=["項目1"], note="ノート",
        )])
        result = validate_slide_spec(spec)
        assert result.slides[0].body == ["項目1"]

    def test_title_slideにbodyを指定するとValueError(self):
        spec = _spec([_slide(
            "title_slide", title="テスト", body=["不要"],
        )])
        with pytest.raises(ValueError, match="body.*not supported"):
            validate_slide_spec(spec)

    def test_title_slideにleftを指定するとValueError(self):
        spec = _spec([_slide(
            "title_slide", title="テスト",
            left={"heading": "左", "body": ["a"]},
        )])
        with pytest.raises(ValueError, match="left.*not supported"):
            validate_slide_spec(spec)

    def test_blankにbodyを指定するとValueError(self):
        spec = _spec([_slide("blank", body=["不要"])])
        with pytest.raises(ValueError, match="body.*not supported"):
            validate_slide_spec(spec)

    def test_section_headerにleftを指定するとValueError(self):
        spec = _spec([_slide(
            "section_header", title="セクション",
            left={"heading": "左", "body": ["a"]},
        )])
        with pytest.raises(ValueError, match="left.*not supported"):
            validate_slide_spec(spec)

    def test_title_onlyにbodyを指定するとValueError(self):
        spec = _spec([_slide(
            "title_only", title="テスト", note="ノート",
            body=["不要"],
        )])
        with pytest.raises(ValueError, match="body.*not supported"):
            validate_slide_spec(spec)


# ---------------------------------------------------------------------------
# 2. 2カラム heading 長チェック
# ---------------------------------------------------------------------------
class Test2カラムheading長:
    """TwoColumnContent.heading の文字数上限"""

    def test_heading上限以内なら通る(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "あ" * MAX_HEADING_LENGTH, "body": ["a"]},
            right={"heading": "い", "body": ["b"]},
            note="ノート",
        )])
        result = validate_slide_spec(spec)
        assert len(result.slides[0].left.heading) == MAX_HEADING_LENGTH

    def test_heading上限超過でValueError(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "あ" * (MAX_HEADING_LENGTH + 1), "body": ["a"]},
            right={"heading": "い", "body": ["b"]},
            note="ノート",
        )])
        with pytest.raises(ValueError, match="heading.*exceeds"):
            validate_slide_spec(spec)


# ---------------------------------------------------------------------------
# 3. ノート文字数上限
# ---------------------------------------------------------------------------
class Testノート長:
    """note フィールドの文字数上限"""

    def test_ノート上限以内なら通る(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト",
            body=["項目"], note="あ" * MAX_NOTE_LENGTH,
        )])
        # 長いノートは発話時間制限を超えるため緩和
        result = validate_slide_spec(spec, max_talk_duration_sec=9999)
        assert len(result.slides[0].note) == MAX_NOTE_LENGTH

    def test_ノート上限超過でValueError(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト",
            body=["項目"], note="あ" * (MAX_NOTE_LENGTH + 1),
        )])
        with pytest.raises(ValueError, match="note.*exceeds"):
            validate_slide_spec(spec)


# ---------------------------------------------------------------------------
# 4. 2カラム body 項目文字数チェック
# ---------------------------------------------------------------------------
class Test2カラムbody項目長:
    """left.body / right.body 各項目の文字数上限"""

    def test_2カラムbody項目が上限以内なら通る(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "左", "body": ["あ" * MAX_BODY_ITEM_LENGTH]},
            right={"heading": "右", "body": ["い"]},
            note="ノート",
        )])
        result = validate_slide_spec(spec)
        assert len(result.slides[0].left.body[0]) == MAX_BODY_ITEM_LENGTH

    def test_2カラムbody項目が上限超過でValueError(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "左", "body": ["あ" * (MAX_BODY_ITEM_LENGTH + 1)]},
            right={"heading": "右", "body": ["い"]},
            note="ノート",
        )])
        with pytest.raises(ValueError, match="body.*exceeds"):
            validate_slide_spec(spec)

    def test_right側のbody項目超過もValueError(self):
        spec = _spec([_slide(
            "two_content", title="テスト",
            left={"heading": "左", "body": ["a"]},
            right={"heading": "右", "body": ["い" * (MAX_BODY_ITEM_LENGTH + 1)]},
            note="ノート",
        )])
        with pytest.raises(ValueError, match="body.*exceeds"):
            validate_slide_spec(spec)


# ---------------------------------------------------------------------------
# 5. メタデータ subtitle/event 長チェック
# ---------------------------------------------------------------------------
class Testメタデータ長:
    """metadata.subtitle / metadata.event の文字数上限"""

    def test_メタデータsubtitle上限超過でValueError(self):
        spec = _spec(
            [_slide("title_slide", title="テスト")],
            subtitle="あ" * (MAX_SUBTITLE_LENGTH + 1),
        )
        with pytest.raises(ValueError, match="metadata.subtitle.*exceeds"):
            validate_slide_spec(spec)

    def test_メタデータevent上限超過でValueError(self):
        spec = _spec(
            [_slide("title_slide", title="テスト")],
            event="あ" * (MAX_SUBTITLE_LENGTH + 1),
        )
        with pytest.raises(ValueError, match="metadata.event.*exceeds"):
            validate_slide_spec(spec)


# ---------------------------------------------------------------------------
# 6. image 空文字列チェック
# ---------------------------------------------------------------------------
class Testimage空文字列:
    """image フィールドが空文字列の場合"""

    def test_imageが空文字列でValueError(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト",
            body=["項目"], note="ノート", image="",
        )])
        with pytest.raises(ValueError, match="image.*empty"):
            validate_slide_spec(spec)

    def test_imageがNoneなら通る(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト",
            body=["項目"], note="ノート", image=None,
        )])
        result = validate_slide_spec(spec)
        assert result.slides[0].image is None

    def test_imageが有効な文字列なら通る(self):
        spec = _spec([_slide(
            "title_and_content", title="テスト",
            body=["項目"], note="ノート", image="diagram.png",
        )])
        result = validate_slide_spec(spec)
        assert result.slides[0].image == "diagram.png"


# ---------------------------------------------------------------------------
# 7. 先頭スライドのレイアウト推奨チェック（warning）
# ---------------------------------------------------------------------------
class Test先頭スライドレイアウト:
    """先頭スライドが title_slide でない場合に warning"""

    def test_先頭がtitle_slideならwarningなし(self):
        spec = _spec([
            _slide("title_slide", title="タイトル"),
            _slide("title_and_content", title="内容", body=["a"], note="ノート"),
        ])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validate_slide_spec(spec)
            layout_warnings = [
                x for x in w if "title_slide" in str(x.message)
            ]
            assert len(layout_warnings) == 0

    def test_先頭がtitle_slideでないとwarning(self):
        spec = _spec([
            _slide("title_and_content", title="いきなり内容", body=["a"], note="ノート"),
        ])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validate_slide_spec(spec)
            layout_warnings = [
                x for x in w if "title_slide" in str(x.message)
            ]
            assert len(layout_warnings) == 1
