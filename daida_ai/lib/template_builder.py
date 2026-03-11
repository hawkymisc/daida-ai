"""PPTXテンプレートのデザイン生成

Office デフォルトテンプレートをベースに、テーマカラー・背景色・フォントを
プログラム的に書き換えて tech/casual/formal の3テンプレートを生成する。

python-pptxはテーマ編集APIを持たないため、zipfile + lxml で直接XML操作する。
"""

from __future__ import annotations

import shutil
import zipfile
from io import BytesIO
from pathlib import Path

from lxml import etree

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"

_SLIDE_W = 12191695  # 16:9 スライド幅 (EMU)
_SLIDE_H = 6858000   # 16:9 スライド高さ (EMU)

# テンプレートデザイン定義
TEMPLATE_DESIGNS: dict[str, dict[str, str]] = {
    "tech": {
        "bg_color": "1A1A2E",
        "dk1": "E8E8E8",    # メインテキスト（明るいグレー）
        "lt1": "1A1A2E",    # メイン背景
        "dk2": "B0B0B0",    # サブテキスト
        "lt2": "2D2D44",    # サブ背景
        "accent1": "00D4FF",  # シアン
        "accent2": "7B68EE",  # パープル
        "accent3": "00E676",  # グリーン
        "accent4": "FF4081",  # ピンク
        "accent5": "FFD740",  # イエロー
        "accent6": "448AFF",  # ブルー
        "hlink": "00D4FF",
        "folHlink": "7B68EE",
        "major_font_latin": "Consolas",
        "minor_font_latin": "Segoe UI",
        "major_font_jpan": "MS ゴシック",
        "minor_font_jpan": "メイリオ",
        "theme_name": "Tech Dark",
        "color_scheme_name": "Tech",
    },
    "casual": {
        "bg_color": "FFF8F0",
        "dk1": "333333",    # ダークグレーテキスト
        "lt1": "FFF8F0",    # ウォームホワイト背景
        "dk2": "555555",
        "lt2": "FFF0E0",
        "accent1": "FF6B35",  # オレンジ
        "accent2": "F7C948",  # イエロー
        "accent3": "06D6A0",  # ミント
        "accent4": "118AB2",  # ティール
        "accent5": "EF476F",  # コーラル
        "accent6": "8338EC",  # パープル
        "hlink": "118AB2",
        "folHlink": "8338EC",
        "major_font_latin": "Fredoka",
        "minor_font_latin": "Nunito",
        "major_font_jpan": "M PLUS Rounded 1c",
        "minor_font_jpan": "M PLUS Rounded 1c",
        "theme_name": "Casual Warm",
        "color_scheme_name": "Casual",
    },
    "formal": {
        "bg_color": "FFFFFF",
        "dk1": "1B2D45",    # ダークネイビーテキスト
        "lt1": "FFFFFF",    # ホワイト背景
        "dk2": "34495E",
        "lt2": "ECF0F1",
        "accent1": "1B3A5C",  # ネイビー
        "accent2": "2C5F8A",  # ミディアムブルー
        "accent3": "34495E",  # チャコール
        "accent4": "7F8C8D",  # グレー
        "accent5": "2980B9",  # ブルー
        "accent6": "16A085",  # ティール
        "hlink": "2980B9",
        "folHlink": "7F8C8D",
        "major_font_latin": "Georgia",
        "minor_font_latin": "Calibri",
        "major_font_jpan": "游明朝",
        "minor_font_jpan": "游ゴシック",
        "theme_name": "Formal Corporate",
        "color_scheme_name": "Formal",
    },
}

DECORATION_CONFIGS: dict[str, list[dict]] = {
    "tech": [],  # ダークテーマで十分差別化
    "casual": [
        {
            "id": 101, "name": "Bottom Strip",
            "x": 0, "y": _SLIDE_H - 342900,
            "cx": _SLIDE_W, "cy": 342900,
            "prst": "rect",
            "fill_scheme": "accent1",
        },
        {
            "id": 102, "name": "Accent Circle 1",
            "x": _SLIDE_W - 900000, "y": _SLIDE_H - 700000,
            "cx": 250000, "cy": 250000,
            "prst": "ellipse",
            "fill_scheme": "accent2",
        },
        {
            "id": 103, "name": "Accent Circle 2",
            "x": _SLIDE_W - 600000, "y": _SLIDE_H - 550000,
            "cx": 200000, "cy": 200000,
            "prst": "ellipse",
            "fill_scheme": "accent3",
        },
    ],
    "formal": [
        {
            "id": 101, "name": "Top Line",
            "x": 0, "y": 0,
            "cx": _SLIDE_W, "cy": 36000,
            "prst": "rect",
            "fill_scheme": "dk1",
        },
        {
            "id": 102, "name": "Bottom Line",
            "x": 0, "y": _SLIDE_H - 36000,
            "cx": _SLIDE_W, "cy": 36000,
            "prst": "rect",
            "fill_scheme": "dk1",
        },
    ],
}

_PH_ADJUSTMENTS: dict[str, dict[tuple[str, str | None], dict[str, int]]] = {
    "ppt/slideMasters/slideMaster1.xml": {
        ("title", None):  {"cx": 11277295},
        ("body", "1"):    {"cx": 11277295},
        ("dt", "2"):      {"cx": 3425898},
        ("ftr", "3"):     {"x": 3883098, "cx": 3425898},
        ("sldNum", "4"):  {"x": 7308996, "cx": 3425898},
    },
    "ppt/slideLayouts/slideLayout1.xml": {
        ("ctrTitle", None): {"cx": 10820095},
        ("subTitle", "1"):  {"cx": 9448495},
    },
    "ppt/slideLayouts/slideLayout3.xml": {
        ("title", None): {"cx": 10747069},
        ("body", "1"):   {"cx": 10747069},
    },
    "ppt/slideLayouts/slideLayout4.xml": {
        ("body", "1"): {"cx": 5562447},
        ("body", "2"): {"x": 6172047, "cx": 5562447},
    },
    "ppt/slideLayouts/slideLayout5.xml": {
        ("body", "1"): {"cx": 5562447},
        ("body", "2"): {"cx": 5562447},
        ("body", "3"): {"x": 6172047, "cx": 5562447},
        ("body", "4"): {"x": 6172047, "cx": 5562447},
    },
    "ppt/slideLayouts/slideLayout8.xml": {
        ("title", None): {"cx": 3425898},
        ("body", "1"):   {"x": 3883098, "cx": 7851397},
        ("body", "2"):   {"cx": 3425898},
    },
    "ppt/slideLayouts/slideLayout9.xml": {
        ("title", None): {"x": 1828800, "cx": 8534095},
        ("pic", "1"):    {"x": 1828800, "cx": 8534095},
        ("body", "2"):   {"x": 1828800, "cx": 8534095},
    },
    "ppt/slideLayouts/slideLayout11.xml": {
        ("body", "1"):   {"cx": 9067495},
        ("title", None): {"x": 9677095},
    },
}

# ベーステンプレートのデフォルトパス（パッケージ内に同梱）
_DEFAULT_BASE_TEMPLATE = (
    Path(__file__).resolve().parents[1] / "assets" / "base_template.pptx"
)


def _qn(tag: str) -> str:
    """'a:solidFill' → '{http://...}solidFill' に変換"""
    nsmap = {"a": _A_NS, "p": _P_NS}
    prefix, local = tag.split(":")
    return f"{{{nsmap[prefix]}}}{local}"


def build_template(
    name: str,
    output_path: Path,
    *,
    base_template: Path | None = None,
) -> None:
    """テンプレート名からデザイン済みPPTXを生成する。

    Args:
        name: "tech", "casual", "formal"
        output_path: 出力ファイルパス
        base_template: ベーステンプレートのパス（省略時はデフォルト）

    Raises:
        ValueError: 不正なテンプレート名
    """
    if name not in TEMPLATE_DESIGNS:
        raise ValueError(f"Unknown template: {name}")

    design = TEMPLATE_DESIGNS[name]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    src = base_template or _DEFAULT_BASE_TEMPLATE
    # ベーステンプレートをコピーしてから内部XMLを書き換え
    shutil.copy2(str(src), str(output_path))
    _apply_design(output_path, design, name)


def _apply_design(pptx_path: Path, design: dict[str, str], name: str) -> None:
    """PPTXファイル内のテーマ・マスターXMLを書き換える。"""
    # zipは in-place 更新不可なので、全エントリをメモリに読み込み→書き戻し
    zip_entries: list[tuple[zipfile.ZipInfo, bytes]] = []
    with zipfile.ZipFile(str(pptx_path), "r") as zf:
        for info in zf.infolist():
            zip_entries.append((info, zf.read(info)))

    # テーマXMLとマスターXMLを書き換え
    updated: dict[str, bytes] = {}

    theme_data = next(d for zi, d in zip_entries if zi.filename == "ppt/theme/theme1.xml")
    theme_root = etree.fromstring(theme_data)
    _apply_color_scheme(theme_root, design)
    _apply_font_scheme(theme_root, design)
    _apply_theme_name(theme_root, design)
    updated["ppt/theme/theme1.xml"] = etree.tostring(
        theme_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    master_data = next(d for zi, d in zip_entries if zi.filename == "ppt/slideMasters/slideMaster1.xml")
    master_root = etree.fromstring(master_data)
    _apply_background(master_root, design)
    _add_decorations(master_root, name)
    updated["ppt/slideMasters/slideMaster1.xml"] = etree.tostring(
        master_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    # 元のZipInfoを保持して書き戻し
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf_out:
        for info, data in zip_entries:
            if info.filename in updated:
                zf_out.writestr(info, updated[info.filename])
            else:
                zf_out.writestr(info, data)

    pptx_path.write_bytes(buf.getvalue())

    # プレースホルダ調整（zip全体を再度読み書き）
    _adjust_placeholders(pptx_path)


def _apply_color_scheme(theme_root: etree._Element, design: dict[str, str]) -> None:
    """テーマのカラースキームを書き換える。"""
    nsmap = {"a": _A_NS}
    clr_scheme = theme_root.find(".//a:clrScheme", nsmap)
    clr_scheme.set("name", design.get("color_scheme_name", "Custom"))

    slots = ["dk1", "lt1", "dk2", "lt2",
             "accent1", "accent2", "accent3", "accent4",
             "accent5", "accent6", "hlink", "folHlink"]

    for slot_name in slots:
        if slot_name not in design:
            continue
        slot = clr_scheme.find(f"a:{slot_name}", nsmap)
        if slot is None:
            continue
        # 既存の子要素を削除
        for child in list(slot):
            slot.remove(child)
        # srgbClr で固定色を設定
        srgb = etree.SubElement(slot, _qn("a:srgbClr"))
        srgb.set("val", design[slot_name])


def _apply_font_scheme(theme_root: etree._Element, design: dict[str, str]) -> None:
    """テーマのフォントスキームを書き換える。"""
    nsmap = {"a": _A_NS}
    font_scheme = theme_root.find(".//a:fontScheme", nsmap)

    for font_type in ["majorFont", "minorFont"]:
        font_elem = font_scheme.find(f"a:{font_type}", nsmap)
        if font_elem is None:
            continue

        # Latin フォント
        key_prefix = "major" if font_type == "majorFont" else "minor"
        latin_key = f"{key_prefix}_font_latin"
        if latin_key in design:
            latin = font_elem.find("a:latin", nsmap)
            if latin is not None:
                latin.set("typeface", design[latin_key])

        # 日本語フォント
        jpan_key = f"{key_prefix}_font_jpan"
        if jpan_key in design:
            jpan = font_elem.find("a:font[@script='Jpan']", nsmap)
            if jpan is not None:
                jpan.set("typeface", design[jpan_key])


def _apply_theme_name(theme_root: etree._Element, design: dict[str, str]) -> None:
    """テーマ名を設定する。"""
    if "theme_name" in design:
        theme_root.set("name", design["theme_name"])


def _apply_background(master_root: etree._Element, design: dict[str, str]) -> None:
    """スライドマスターの背景を bgRef 方式で設定する。

    bgRef idx="1001" はテーマの bgFillStyleLst 第1エントリを参照し、
    schemeClr val="bg1" で lt1 カラー（= bg_color）に解決される。
    """
    nsmap = {"a": _A_NS, "p": _P_NS}
    cSld = master_root.find("p:cSld", nsmap)
    if cSld is None:
        return

    existing_bg = cSld.find("p:bg", nsmap)
    if existing_bg is not None:
        cSld.remove(existing_bg)

    bg = etree.Element(_qn("p:bg"))
    bgRef = etree.SubElement(bg, _qn("p:bgRef"))
    bgRef.set("idx", "1001")
    schemeClr = etree.SubElement(bgRef, _qn("a:schemeClr"))
    schemeClr.set("val", "bg1")

    cSld.insert(0, bg)


def _add_decorations(master_root: etree._Element, name: str) -> None:
    """スライドマスターに装飾シェイプを追加する。"""
    configs = DECORATION_CONFIGS.get(name, [])
    if not configs:
        return
    nsmap = {"a": _A_NS, "p": _P_NS}
    spTree = master_root.find(".//p:cSld/p:spTree", nsmap)
    for cfg in configs:
        spTree.append(_build_decoration_shape(cfg))


def _build_decoration_shape(cfg: dict) -> etree._Element:
    """装飾シェイプの p:sp 要素を生成する。"""
    sp = etree.Element(_qn("p:sp"))
    nvSpPr = etree.SubElement(sp, _qn("p:nvSpPr"))
    cNvPr = etree.SubElement(nvSpPr, _qn("p:cNvPr"))
    cNvPr.set("id", str(cfg["id"]))
    cNvPr.set("name", cfg["name"])
    etree.SubElement(nvSpPr, _qn("p:cNvSpPr"))
    etree.SubElement(nvSpPr, _qn("p:nvPr"))
    spPr = etree.SubElement(sp, _qn("p:spPr"))
    xfrm = etree.SubElement(spPr, _qn("a:xfrm"))
    off = etree.SubElement(xfrm, _qn("a:off"))
    off.set("x", str(cfg["x"]))
    off.set("y", str(cfg["y"]))
    ext = etree.SubElement(xfrm, _qn("a:ext"))
    ext.set("cx", str(cfg["cx"]))
    ext.set("cy", str(cfg["cy"]))
    prstGeom = etree.SubElement(spPr, _qn("a:prstGeom"))
    prstGeom.set("prst", cfg["prst"])
    etree.SubElement(prstGeom, _qn("a:avLst"))
    solidFill = etree.SubElement(spPr, _qn("a:solidFill"))
    schemeClr = etree.SubElement(solidFill, _qn("a:schemeClr"))
    schemeClr.set("val", cfg["fill_scheme"])
    ln = etree.SubElement(spPr, _qn("a:ln"))
    etree.SubElement(ln, _qn("a:noFill"))
    return sp


def _adjust_placeholders(pptx_path: Path) -> None:
    """マスター・レイアウトのプレースホルダを16:9用に左右均等化する。"""
    nsmap = {"a": _A_NS, "p": _P_NS}

    zip_entries: list[tuple[zipfile.ZipInfo, bytes]] = []
    with zipfile.ZipFile(str(pptx_path), "r") as zf:
        for info in zf.infolist():
            zip_entries.append((info, zf.read(info)))

    updated: dict[str, bytes] = {}

    for xml_path, adjustments in _PH_ADJUSTMENTS.items():
        data = next((d for zi, d in zip_entries if zi.filename == xml_path), None)
        if data is None:
            continue
        root = etree.fromstring(data)
        spTree = root.find(".//p:cSld/p:spTree", nsmap)

        for sp in spTree.findall("p:sp", nsmap):
            nvPr = sp.find("p:nvSpPr/p:nvPr", nsmap)
            ph = nvPr.find("p:ph", nsmap) if nvPr is not None else None
            if ph is None:
                continue
            ph_type = ph.get("type", "body")
            ph_idx = ph.get("idx")
            key = (ph_type, ph_idx)
            if key not in adjustments:
                continue

            xfrm = sp.find("p:spPr/a:xfrm", nsmap)
            if xfrm is None:
                continue
            adj = adjustments[key]
            if "x" in adj:
                xfrm.find("a:off", nsmap).set("x", str(adj["x"]))
            if "cx" in adj:
                xfrm.find("a:ext", nsmap).set("cx", str(adj["cx"]))

        updated[xml_path] = etree.tostring(
            root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf_out:
        for info, data in zip_entries:
            zf_out.writestr(info, updated.get(info.filename, data))
    pptx_path.write_bytes(buf.getvalue())
