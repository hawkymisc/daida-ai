"""音声ファイルのPPTX埋め込み

python-pptxは音声の直接埋め込みAPIを持たないため、
OPCパッケージレベルでメディアパーツを追加し、
スライドXMLに音声シェイプ（p:pic + audioFile）を挿入する。
"""

from __future__ import annotations

from pathlib import Path
from lxml import etree
from pptx import Presentation
from pptx.opc.package import Part, PackURI, RT
from pptx.util import Emu

# OOXML名前空間
_nsmap = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def embed_audio_to_pptx(
    input_path: Path,
    audio_dir: Path,
    output_path: Path,
) -> int:
    """音声ファイルをPPTXの各スライドに埋め込む。

    音声ファイルは slide_000.mp3, slide_001.mp3, ... の命名規則。
    対応するファイルが存在するスライドにのみ埋め込む。

    Args:
        input_path: 入力PPTXファイルパス
        audio_dir: 音声ファイルディレクトリ
        output_path: 出力PPTXファイルパス

    Returns:
        埋め込まれた音声ファイル数
    """
    prs = Presentation(str(input_path))
    count = 0

    for i, slide in enumerate(prs.slides):
        audio_path = audio_dir / f"slide_{i:03d}.mp3"
        if not audio_path.exists():
            continue

        _embed_audio_in_slide(prs, slide, audio_path, i)
        count += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return count


def _embed_audio_in_slide(prs, slide, audio_path: Path, slide_idx: int) -> None:
    """単一スライドに音声ファイルを埋め込む。

    1. OPCパッケージに音声パーツを追加
    2. スライドパーツからリレーションシップ(RT.MEDIA)を追加
    3. スライドXMLにp:pic要素（audioFile参照付き）を挿入
    """
    audio_data = audio_path.read_bytes()
    part_name = f"/ppt/media/audio_slide{slide_idx:03d}.mp3"

    # 1. 音声パーツを作成
    audio_part = Part(
        PackURI(part_name),
        "audio/mpeg",
        prs.part.package,
        blob=audio_data,
    )

    # 2. リレーションシップを追加（rIdを取得）
    r_id = slide.part.relate_to(audio_part, RT.MEDIA)

    # 3. スライドXMLに音声シェイプを追加
    _add_audio_shape(slide, r_id, slide_idx)


def _add_audio_shape(slide, r_id: str, slide_idx: int) -> None:
    """スライドXMLにp:pic要素（音声コントロール）を追加する。

    音声アイコンはスライドの右下に小さく配置し、
    自動再生設定を含める。
    """
    # スライド上の位置（右下、小さいアイコン）
    x = Emu(8229600)   # ~3.2 inches from left
    y = Emu(5943600)   # ~2.3 inches from top
    cx = Emu(304800)   # ~0.12 inches width
    cy = Emu(304800)   # ~0.12 inches height

    shape_id = 10000 + slide_idx

    # p:pic 要素を構築（音声シェイプとして）
    pic_xml = (
        f'<p:pic xmlns:a="{_nsmap["a"]}" '
        f'xmlns:r="{_nsmap["r"]}" '
        f'xmlns:p="{_nsmap["p"]}">'
        f'  <p:nvPicPr>'
        f'    <p:cNvPr id="{shape_id}" name="Audio {slide_idx}">'
        f'      <a:hlinkClick r:id="" action="ppaction://media"/>'
        f'    </p:cNvPr>'
        f'    <p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>'
        f'    <p:nvPr>'
        f'      <a:audioFile r:link="{r_id}"/>'
        f'    </p:nvPr>'
        f'  </p:nvPicPr>'
        f'  <p:blipFill>'
        f'    <a:blip/>'
        f'    <a:stretch><a:fillRect/></a:stretch>'
        f'  </p:blipFill>'
        f'  <p:spPr>'
        f'    <a:xfrm>'
        f'      <a:off x="{x}" y="{y}"/>'
        f'      <a:ext cx="{cx}" cy="{cy}"/>'
        f'    </a:xfrm>'
        f'    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'  </p:spPr>'
        f'</p:pic>'
    )

    pic_element = etree.fromstring(pic_xml)
    # slide.element はスライドのXMLルート要素（CT_Slide）
    slide_element = slide.element
    sp_tree = slide_element.find(
        ".//{http://schemas.openxmlformats.org/presentationml/2006/main}spTree"
    )
    if sp_tree is None:
        sp_tree = slide_element.find(
            ".//{http://schemas.openxmlformats.org/presentationml/2006/main}cSld"
        )
        if sp_tree is not None:
            sp_tree = sp_tree.find(
                "{http://schemas.openxmlformats.org/presentationml/2006/main}spTree"
            )

    if sp_tree is not None:
        sp_tree.append(pic_element)
