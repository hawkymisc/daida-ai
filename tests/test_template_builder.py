"""TDD: template_builder.py — テンプレートデザイン生成テスト

tech/casual/formal テンプレートが正しい背景色・カラースキーム・フォントを持つか検証する。
"""

import pytest
import zipfile
from pathlib import Path
from lxml import etree

from daida_ai.lib.template_builder import (
    build_template,
    DECORATION_CONFIGS,
    TEMPLATE_DESIGNS,
    _PH_ADJUSTMENTS,
    _SLIDE_W,
)

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_nsmap = {"a": _A_NS, "p": _P_NS}


def _read_theme_xml(pptx_path: Path) -> etree._Element:
    with zipfile.ZipFile(str(pptx_path)) as zf:
        return etree.fromstring(zf.read("ppt/theme/theme1.xml"))


def _read_master_xml(pptx_path: Path) -> etree._Element:
    with zipfile.ZipFile(str(pptx_path)) as zf:
        return etree.fromstring(zf.read("ppt/slideMasters/slideMaster1.xml"))


def _get_color_scheme_value(theme_root, slot_name: str) -> str:
    """カラースキームのスロット値をRGB文字列で返す"""
    clr_scheme = theme_root.find(".//a:clrScheme", _nsmap)
    slot = clr_scheme.find(f"a:{slot_name}", _nsmap)
    srgb = slot.find("a:srgbClr", _nsmap)
    if srgb is not None:
        return srgb.get("val").upper()
    sys_clr = slot.find("a:sysClr", _nsmap)
    if sys_clr is not None:
        return sys_clr.get("lastClr", "").upper()
    return ""


class Testデザイン定義:
    """TEMPLATE_DESIGNSの定義が正しい"""

    def test_3テンプレートが定義されている(self):
        assert set(TEMPLATE_DESIGNS.keys()) == {"tech", "casual", "formal"}

    def test_各テンプレートに必須キーがある(self):
        required = {"bg_color", "dk1", "lt1", "accent1", "accent2",
                    "major_font_latin", "minor_font_latin"}
        for name, design in TEMPLATE_DESIGNS.items():
            for key in required:
                assert key in design, f"{name} missing {key}"


class Testテンプレート生成:
    """build_template()でPPTXファイルが正しく生成される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def generated_template(self, request, tmp_output_dir: Path) -> tuple[str, Path]:
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        return name, output

    def test_ファイルが生成される(self, generated_template):
        _, path = generated_template
        assert path.exists()
        assert path.stat().st_size > 0

    def test_有効なPPTXファイルである(self, generated_template):
        from pptx import Presentation
        _, path = generated_template
        prs = Presentation(str(path))
        assert len(prs.slide_masters) >= 1

    def test_レイアウトが保持される(self, generated_template):
        from pptx import Presentation
        _, path = generated_template
        prs = Presentation(str(path))
        layouts = prs.slide_masters[0].slide_layouts
        layout_names = [l.name for l in layouts]
        assert "Title Slide" in layout_names
        assert "Title and Content" in layout_names
        assert "Section Header" in layout_names
        assert "Two Content" in layout_names


def _read_xml(pptx_path: Path, xml_path: str) -> etree._Element:
    with zipfile.ZipFile(str(pptx_path)) as zf:
        return etree.fromstring(zf.read(xml_path))


def _find_ph_xfrm(root, ph_type, ph_idx):
    """ph type+idx からxfrm要素を取得"""
    for sp in root.findall(".//p:cSld/p:spTree/p:sp", _nsmap):
        nvPr = sp.find("p:nvSpPr/p:nvPr", _nsmap)
        ph = nvPr.find("p:ph", _nsmap) if nvPr is not None else None
        if ph is None:
            continue
        if ph.get("type", "body") == ph_type and ph.get("idx") == ph_idx:
            return sp.find("p:spPr/a:xfrm", _nsmap)
    return None


def _get_decoration_shapes(master_root):
    """プレースホルダでないシェイプ一覧を返す"""
    spTree = master_root.find(".//p:cSld/p:spTree", _nsmap)
    result = []
    for sp in spTree.findall("p:sp", _nsmap):
        nvPr = sp.find("p:nvSpPr/p:nvPr", _nsmap)
        ph = nvPr.find("p:ph", _nsmap) if nvPr is not None else None
        if ph is None:
            result.append(sp)
    return result


class Test背景色:
    """各テンプレートの背景色がbgRef方式で正しく設定される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def template_master(self, request, tmp_output_dir):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        return name, _read_master_xml(output), output

    def test_bgRef方式で背景が設定される(self, template_master):
        name, master, _ = template_master
        bgRef = master.find(".//p:cSld/p:bg/p:bgRef", _nsmap)
        assert bgRef is not None, f"{name}: should use bgRef, not bgPr"
        assert bgRef.get("idx") == "1001"

    def test_bgRefはbg1スキームカラーを参照する(self, template_master):
        _, master, _ = template_master
        bgRef = master.find(".//p:cSld/p:bg/p:bgRef", _nsmap)
        schemeClr = bgRef.find("a:schemeClr", _nsmap)
        assert schemeClr is not None
        assert schemeClr.get("val") == "bg1"

    def test_lt1が背景色と一致する(self, template_master):
        """bgRef→bg1→lt1 の間接参照が正しい色に解決されることを確認"""
        name, _, output = template_master
        theme = _read_theme_xml(output)
        lt1_val = _get_color_scheme_value(theme, "lt1")
        expected = TEMPLATE_DESIGNS[name]["bg_color"].upper()
        assert lt1_val == expected


class Testカラースキーム:
    """テーマのカラースキームが正しく設定される"""

    _COLOR_SLOTS = [
        "dk1", "lt1", "dk2", "lt2",
        "accent1", "accent2", "accent3", "accent4",
        "accent5", "accent6", "hlink", "folHlink",
    ]

    @pytest.fixture(params=["tech", "casual", "formal"])
    def template_theme(self, request, tmp_output_dir: Path):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        theme = _read_theme_xml(output)
        return name, theme

    def test_全カラースロットがデザイン通り設定される(self, template_theme):
        name, theme = template_theme
        design = TEMPLATE_DESIGNS[name]
        for slot in self._COLOR_SLOTS:
            actual = _get_color_scheme_value(theme, slot)
            expected = design[slot].upper()
            assert actual == expected, \
                f"{name}.{slot}: expected {expected}, got {actual}"

    def test_カラースキーム名が設定される(self, template_theme):
        name, theme = template_theme
        clr_scheme = theme.find(".//a:clrScheme", _nsmap)
        expected = TEMPLATE_DESIGNS[name]["color_scheme_name"]
        assert clr_scheme.get("name") == expected


class Testフォント:
    """テーマのフォントスキームが正しく設定される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def template_theme(self, request, tmp_output_dir: Path):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        theme = _read_theme_xml(output)
        return name, theme

    def test_majorFont_latinが設定される(self, template_theme):
        name, theme = template_theme
        latin = theme.find(".//a:fontScheme/a:majorFont/a:latin", _nsmap)
        expected = TEMPLATE_DESIGNS[name]["major_font_latin"]
        assert latin.get("typeface") == expected

    def test_minorFont_latinが設定される(self, template_theme):
        name, theme = template_theme
        latin = theme.find(".//a:fontScheme/a:minorFont/a:latin", _nsmap)
        expected = TEMPLATE_DESIGNS[name]["minor_font_latin"]
        assert latin.get("typeface") == expected

    def test_majorFont_jpanが設定される(self, template_theme):
        name, theme = template_theme
        jpan = theme.find(
            ".//a:fontScheme/a:majorFont/a:font[@script='Jpan']", _nsmap
        )
        expected = TEMPLATE_DESIGNS[name]["major_font_jpan"]
        assert jpan.get("typeface") == expected

    def test_minorFont_jpanが設定される(self, template_theme):
        name, theme = template_theme
        jpan = theme.find(
            ".//a:fontScheme/a:minorFont/a:font[@script='Jpan']", _nsmap
        )
        expected = TEMPLATE_DESIGNS[name]["minor_font_jpan"]
        assert jpan.get("typeface") == expected

    def test_テーマ名が設定される(self, template_theme):
        name, theme = template_theme
        expected = TEMPLATE_DESIGNS[name]["theme_name"]
        assert theme.get("name") == expected


class Test差別化:
    """3テンプレートが互いに異なることを検証"""

    def test_背景色が全て異なる(self):
        bg_colors = {d["bg_color"] for d in TEMPLATE_DESIGNS.values()}
        assert len(bg_colors) == 3

    def test_accent1が全て異なる(self):
        accents = {d["accent1"] for d in TEMPLATE_DESIGNS.values()}
        assert len(accents) == 3

    def test_不正なテンプレート名はValueError(self):
        with pytest.raises(ValueError, match="Unknown template"):
            build_template("invalid", Path("/tmp/test.pptx"))


class Testプレースホルダマージン:
    """プレースホルダが16:9スライドで左右均等に配置される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def generated(self, request, tmp_output_dir):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        return name, output

    def test_マスターtitle_bodyが左右均等(self, generated):
        _, output = generated
        master = _read_master_xml(output)
        for ph_type, ph_idx in [("title", None), ("body", "1")]:
            xfrm = _find_ph_xfrm(master, ph_type, ph_idx)
            x = int(xfrm.find("a:off", _nsmap).get("x"))
            cx = int(xfrm.find("a:ext", _nsmap).get("cx"))
            right = _SLIDE_W - x - cx
            assert abs(x - right) <= 1, f"ph={ph_type}: left={x} right={right}"

    def test_全調整対象が正しいサイズ(self, generated):
        """_PH_ADJUSTMENTS の全エントリに対し、設定値が反映されていることを確認"""
        _, output = generated
        for xml_path, adjustments in _PH_ADJUSTMENTS.items():
            root = _read_xml(output, xml_path)
            for (ph_type, ph_idx), adj in adjustments.items():
                xfrm = _find_ph_xfrm(root, ph_type, ph_idx)
                if xfrm is None:
                    continue
                if "cx" in adj:
                    actual_cx = int(xfrm.find("a:ext", _nsmap).get("cx"))
                    assert actual_cx == adj["cx"], \
                        f"{xml_path} ph={ph_type}/{ph_idx}: cx={actual_cx} != {adj['cx']}"
                if "x" in adj:
                    actual_x = int(xfrm.find("a:off", _nsmap).get("x"))
                    assert actual_x == adj["x"], \
                        f"{xml_path} ph={ph_type}/{ph_idx}: x={actual_x} != {adj['x']}"

    def test_Layout4の2列が均等幅(self, generated):
        _, output = generated
        root = _read_xml(output, "ppt/slideLayouts/slideLayout4.xml")
        xfrm_l = _find_ph_xfrm(root, "body", "1")
        xfrm_r = _find_ph_xfrm(root, "body", "2")
        cx_l = int(xfrm_l.find("a:ext", _nsmap).get("cx"))
        cx_r = int(xfrm_r.find("a:ext", _nsmap).get("cx"))
        assert cx_l == cx_r, f"columns should be equal: {cx_l} vs {cx_r}"
        x_r = int(xfrm_r.find("a:off", _nsmap).get("x"))
        right_margin = _SLIDE_W - x_r - cx_r
        x_l = int(xfrm_l.find("a:off", _nsmap).get("x"))
        assert abs(x_l - right_margin) <= 1

    def test_継承レイアウトはxfrmなし(self, generated):
        """Layout 2,6,7,10 は master から継承しxfrm を持たない"""
        _, output = generated
        for idx in [2, 6, 7, 10]:
            xml_path = f"ppt/slideLayouts/slideLayout{idx}.xml"
            root = _read_xml(output, xml_path)
            for sp in root.findall(".//p:cSld/p:spTree/p:sp", _nsmap):
                ph = sp.find("p:nvSpPr/p:nvPr/p:ph", _nsmap)
                if ph is not None:
                    xfrm = sp.find("p:spPr/a:xfrm", _nsmap)
                    assert xfrm is None, \
                        f"{xml_path}: should inherit xfrm from master"


class Test装飾シェイプ:
    """テンプレートの装飾シェイプが正しく追加される"""

    @pytest.fixture(params=["tech", "casual", "formal"])
    def template_data(self, request, tmp_output_dir):
        name = request.param
        output = tmp_output_dir / f"{name}.pptx"
        build_template(name, output)
        master = _read_master_xml(output)
        return name, master

    def test_装飾数がDECORATION_CONFIGSと一致する(self, template_data):
        name, master = template_data
        decos = _get_decoration_shapes(master)
        expected = len(DECORATION_CONFIGS[name])
        assert len(decos) == expected, f"{name}: expected {expected} decorations"

    def test_装飾シェイプのIDが既存と衝突しない(self, template_data):
        name, master = template_data
        all_ids = []
        for sp in master.findall(".//p:cSld/p:spTree/p:sp", _nsmap):
            cNvPr = sp.find("p:nvSpPr/p:cNvPr", _nsmap)
            if cNvPr is not None:
                all_ids.append(int(cNvPr.get("id")))
        assert len(all_ids) == len(set(all_ids)), f"{name}: duplicate shape IDs"

    def test_装飾シェイプはschemeClrで塗られる(self, template_data):
        name, master = template_data
        decos = _get_decoration_shapes(master)
        for sp in decos:
            schemeClr = sp.find(".//a:solidFill/a:schemeClr", _nsmap)
            assert schemeClr is not None, "decoration should use schemeClr"

    def test_装飾シェイプはプレースホルダでない(self, template_data):
        name, master = template_data
        decos = _get_decoration_shapes(master)
        for sp in decos:
            ph = sp.find("p:nvSpPr/p:nvPr/p:ph", _nsmap)
            assert ph is None
