"""スライドショー自動再生設定

PPTXにauto-advance transition と 音声auto-play animation を設定し、
スライドショー開始から終了まで完全自動で走るようにする。
"""

from __future__ import annotations

from pathlib import Path
from lxml import etree
from pptx import Presentation
from pptx.opc.package import RT

_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_nsmap = {"p": _P_NS, "a": _A_NS, "r": _R_NS}

# MP3フレームベースの簡易デュレーション推定用
_MP3_BITRATE_TABLE = {
    0b0001: 32, 0b0010: 40, 0b0011: 48, 0b0100: 56,
    0b0101: 64, 0b0110: 80, 0b0111: 96, 0b1000: 112,
    0b1001: 128, 0b1010: 160, 0b1011: 192, 0b1100: 224,
    0b1101: 256, 0b1110: 320,
}


def configure_slideshow(
    input_path: Path,
    output_path: Path,
    *,
    silent_duration_ms: int = 3000,
    audio_buffer_ms: int = 1000,
) -> None:
    """PPTXにスライドショー自動再生設定を追加する。

    Args:
        input_path: 入力PPTXファイルパス
        output_path: 出力PPTXファイルパス
        silent_duration_ms: 音声なしスライドの表示時間（ミリ秒）
        audio_buffer_ms: 音声付きスライドの再生完了後の余白（ミリ秒）
    """
    prs = Presentation(str(input_path))

    for slide in prs.slides:
        audio_duration = _get_audio_duration_ms(slide)

        if audio_duration > 0:
            advance_ms = audio_duration + audio_buffer_ms
            _add_auto_play_animation(slide)
        else:
            advance_ms = silent_duration_ms

        _set_auto_advance(slide, advance_ms)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def _get_audio_duration_ms(slide) -> int:
    """スライドに埋め込まれた音声のデュレーションを推定する（ミリ秒）。

    音声がない場合は0を返す。
    OPCリレーションシップからメディアパーツを取得し、
    MP3バイナリからデュレーションを推定する。
    """
    media_rels = [r for r in slide.part.rels.values() if r.reltype == RT.MEDIA]
    if not media_rels:
        return 0

    # 最初のメディアリレーションシップの音声データを取得
    media_part = media_rels[0].target_part
    audio_blob = media_part.blob
    return _estimate_mp3_duration_ms(audio_blob)


def _estimate_mp3_duration_ms(data: bytes) -> int:
    """MP3バイナリからデュレーションをミリ秒で推定する。

    pydub依存を避け、ファイルサイズとビットレートから概算する。
    精度は実用上十分（±数秒）。
    """
    if len(data) < 10:
        return 0

    offset = 0
    # ID3タグをスキップ
    if data[:3] == b"ID3":
        if len(data) < 10:
            return 0
        size = (
            (data[6] & 0x7F) << 21
            | (data[7] & 0x7F) << 14
            | (data[8] & 0x7F) << 7
            | (data[9] & 0x7F)
        )
        offset = 10 + size

    # 最初のフレームヘッダを探す
    while offset < len(data) - 4:
        if data[offset] == 0xFF and (data[offset + 1] & 0xE0) == 0xE0:
            bitrate_idx = (data[offset + 2] >> 4) & 0x0F
            bitrate_kbps = _MP3_BITRATE_TABLE.get(bitrate_idx, 128)
            audio_bytes = len(data) - offset
            duration_s = (audio_bytes * 8) / (bitrate_kbps * 1000)
            return max(int(duration_s * 1000), 1)
        offset += 1

    # フレームヘッダが見つからない場合、128kbps仮定で概算
    duration_s = (len(data) * 8) / (128 * 1000)
    return max(int(duration_s * 1000), 1)


def _set_auto_advance(slide, advance_ms: int) -> None:
    """スライドに自動ページ送りを設定する。

    既存のtransition要素があれば属性を更新、なければ追加する。
    advClick="0" でクリックを無効化し、advTm でミリ秒指定。
    """
    slide_elem = slide.element
    trans = slide_elem.find(f"{{{_P_NS}}}transition")

    if trans is None:
        trans = etree.SubElement(slide_elem, f"{{{_P_NS}}}transition")

    trans.set("advClick", "0")
    trans.set("advTm", str(advance_ms))


def _add_auto_play_animation(slide) -> None:
    """スライドの音声シェイプに自動再生アニメーションを設定する。

    PowerPointのアニメーション構造:
    p:timing > p:tnLst > p:par (tmRoot) > p:childTnLst > p:seq (mainSeq) >
    p:cTn > p:childTnLst > p:par > p:cTn > p:childTnLst > p:par > p:cTn >
    p:childTnLst > p:audio > p:cMediaNode > p:cTn + p:tgtEl
    """
    # 音声シェイプのIDを取得
    audio_shape_id = _find_audio_shape_id(slide)
    if audio_shape_id is None:
        return

    # 既存のtiming要素を削除して再構築
    slide_elem = slide.element
    existing_timing = slide_elem.find(f"{{{_P_NS}}}timing")
    if existing_timing is not None:
        slide_elem.remove(existing_timing)

    timing_xml = f"""<p:timing xmlns:p="{_P_NS}">
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>
                <p:par>
                  <p:cTn id="3" fill="hold">
                    <p:stCondLst>
                      <p:cond delay="0"/>
                    </p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="4" fill="hold">
                          <p:stCondLst>
                            <p:cond delay="0"/>
                          </p:stCondLst>
                          <p:childTnLst>
                            <p:audio>
                              <p:cMediaNode>
                                <p:cTn id="5" fill="hold" display="0">
                                  <p:stCondLst>
                                    <p:cond delay="0"/>
                                  </p:stCondLst>
                                </p:cTn>
                                <p:tgtEl>
                                  <p:spTgt spid="{audio_shape_id}"/>
                                </p:tgtEl>
                              </p:cMediaNode>
                            </p:audio>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>
              </p:childTnLst>
            </p:cTn>
            <p:prevCondLst>
              <p:cond evt="onPrev" delay="0">
                <p:tgtEl><p:sldTgt/></p:tgtEl>
              </p:cond>
            </p:prevCondLst>
            <p:nextCondLst>
              <p:cond evt="onNext" delay="0">
                <p:tgtEl><p:sldTgt/></p:tgtEl>
              </p:cond>
            </p:nextCondLst>
          </p:seq>
        </p:childTnLst>
      </p:cTn>
    </p:par>
  </p:tnLst>
</p:timing>"""

    timing_elem = etree.fromstring(timing_xml)
    slide_elem.append(timing_elem)


def _find_audio_shape_id(slide) -> int | None:
    """スライドから音声シェイプのIDを取得する。

    a:audioFile要素を持つp:pic要素のcNvPr idを返す。
    """
    slide_elem = slide.element
    # audioFile要素を持つnvPrを探す
    for audio_file in slide_elem.iter(f"{{{_A_NS}}}audioFile"):
        # audioFile → nvPr → nvPicPr → cNvPr
        nv_pr = audio_file.getparent()
        if nv_pr is not None:
            nv_pic_pr = nv_pr.getparent()
            if nv_pic_pr is not None:
                c_nv_pr = nv_pic_pr.find(f"{{{_P_NS}}}cNvPr")
                if c_nv_pr is not None:
                    return int(c_nv_pr.get("id"))
    return None
