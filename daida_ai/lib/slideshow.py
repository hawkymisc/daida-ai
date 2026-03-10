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
# MPEG-1 Layer III ビットレートテーブル (kbps)
_MPEG1_L3_BITRATE = {
    0b0001: 32, 0b0010: 40, 0b0011: 48, 0b0100: 56,
    0b0101: 64, 0b0110: 80, 0b0111: 96, 0b1000: 112,
    0b1001: 128, 0b1010: 160, 0b1011: 192, 0b1100: 224,
    0b1101: 256, 0b1110: 320,
}
# MPEG-2/2.5 Layer III ビットレートテーブル (kbps)
_MPEG2_L3_BITRATE = {
    0b0001: 8, 0b0010: 16, 0b0011: 24, 0b0100: 32,
    0b0101: 40, 0b0110: 48, 0b0111: 56, 0b1000: 64,
    0b1001: 80, 0b1010: 96, 0b1011: 112, 0b1100: 128,
    0b1101: 144, 0b1110: 160,
}


_DEFAULT_UNMEASURABLE_DURATION_MS = 30000


def configure_slideshow(
    input_path: Path,
    output_path: Path,
    *,
    silent_duration_ms: int = 3000,
    audio_buffer_ms: int = 1000,
    unmeasurable_duration_ms: int = _DEFAULT_UNMEASURABLE_DURATION_MS,
) -> None:
    """PPTXにスライドショー自動再生設定を追加する。

    Args:
        input_path: 入力PPTXファイルパス
        output_path: 出力PPTXファイルパス
        silent_duration_ms: 音声なしスライドの表示時間（ミリ秒）
        audio_buffer_ms: 音声付きスライドの再生完了後の余白（ミリ秒）
        unmeasurable_duration_ms: デュレーション計測不能時のフォールバック（ミリ秒）
    """
    prs = Presentation(str(input_path))

    for slide in prs.slides:
        has_audio_shapes = bool(_find_audio_shape_ids(slide))
        audio_duration = _get_audio_duration_ms(slide)

        if has_audio_shapes:
            if audio_duration > 0:
                advance_ms = audio_duration + audio_buffer_ms
            else:
                # 外部リンク/非MP3など計測不能 → フォールバック
                advance_ms = unmeasurable_duration_ms + audio_buffer_ms
            _add_auto_play_animation(slide)
        else:
            advance_ms = silent_duration_ms

        _set_auto_advance(slide, advance_ms)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def _get_audio_duration_ms(slide) -> int:
    """スライドに埋め込まれた音声のデュレーションを推定する（ミリ秒）。

    音声がない場合は0を返す。
    複数の音声トラックがある場合は最長のデュレーションを返す
    （audioノードはdelay="0"で同時再生されるため、maxが正しい）。
    RT.MEDIAにはビデオも含まれるため、content_typeでaudioのみフィルタする。
    """
    media_rels = [r for r in slide.part.rels.values() if r.reltype == RT.MEDIA]
    if not media_rels:
        return 0

    max_duration = 0
    for rel in media_rels:
        if rel.is_external:
            continue
        try:
            part = rel.target_part
        except Exception:
            continue
        # ビデオ等の非音声メディアを除外
        if not part.content_type.startswith("audio/"):
            continue
        duration = _estimate_mp3_duration_ms(part.blob)
        if duration > max_duration:
            max_duration = duration
    return max_duration


def _estimate_mp3_duration_ms(data: bytes) -> int:
    """MP3バイナリからデュレーションをミリ秒で推定する。

    pydub依存を避け、ファイルサイズとビットレートから概算する。
    MP3フレームヘッダが見つからない場合（AAC/WAV等）は0を返す。
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
            # MPEGバージョン判定: ビット4-3 of byte1
            # 11=MPEG1, 10=MPEG2, 00=MPEG2.5
            mpeg_version_bits = (data[offset + 1] >> 3) & 0x03
            is_mpeg1 = mpeg_version_bits == 0b11
            bitrate_table = _MPEG1_L3_BITRATE if is_mpeg1 else _MPEG2_L3_BITRATE
            default_bitrate = 128 if is_mpeg1 else 64

            bitrate_idx = (data[offset + 2] >> 4) & 0x0F
            bitrate_kbps = bitrate_table.get(bitrate_idx, default_bitrate)
            audio_bytes = len(data) - offset
            duration_s = (audio_bytes * 8) / (bitrate_kbps * 1000)
            return max(int(duration_s * 1000), 1)
        offset += 1

    # MP3フレームヘッダが見つからない（AAC/WAV等）→ 計測不能
    return 0


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

    既存のアニメーション（テキスト・図形等）を保持しつつ、
    音声auto-playノードをmainSeqにマージする。

    PowerPointのアニメーション構造:
    p:timing > p:tnLst > p:par (tmRoot) > p:childTnLst > p:seq (mainSeq) >
    p:cTn > p:childTnLst > p:par > p:cTn > p:childTnLst > p:par > p:cTn >
    p:childTnLst > p:audio > p:cMediaNode > p:cTn + p:tgtEl
    """
    audio_shape_ids = _find_audio_shape_ids(slide)
    if not audio_shape_ids:
        return

    slide_elem = slide.element
    existing_timing = slide_elem.find(f"{{{_P_NS}}}timing")

    if existing_timing is not None:
        # 既存のtiming構造にaudioノードをマージ
        _merge_audio_into_timing(existing_timing, audio_shape_ids)
    else:
        # timing要素がない場合は新規作成
        timing_elem = _build_timing_xml(audio_shape_ids)
        slide_elem.append(timing_elem)


def _merge_audio_into_timing(
    timing_elem: etree._Element, audio_shape_ids: list[int]
) -> None:
    """既存のp:timing構造に音声auto-playノードを追加する。

    mainSeqのchildTnLstに音声用p:parを追加する。
    既存のアニメーションはそのまま保持される。
    """
    # mainSeq (nodeType="mainSeq") を探す
    main_seq_ctn = timing_elem.find(
        f".//{{{_P_NS}}}cTn[@nodeType='mainSeq']"
    )
    if main_seq_ctn is None:
        return

    child_tn_lst = main_seq_ctn.find(f"{{{_P_NS}}}childTnLst")
    if child_tn_lst is None:
        child_tn_lst = etree.SubElement(main_seq_ctn, f"{{{_P_NS}}}childTnLst")

    # 既存のaudioノードのspidを取得して重複を避ける
    existing_spids: set[int] = set()
    for spgt in timing_elem.iter(f"{{{_P_NS}}}spTgt"):
        parent_audio = spgt.getparent()
        while parent_audio is not None:
            if parent_audio.tag == f"{{{_P_NS}}}audio":
                spid = spgt.get("spid")
                if spid is not None:
                    existing_spids.add(int(spid))
                break
            parent_audio = parent_audio.getparent()

    # 次のcTn idを算出
    max_id = _get_max_ctn_id(timing_elem)

    for shape_id in audio_shape_ids:
        if shape_id in existing_spids:
            continue
        audio_par = _build_audio_par_xml(shape_id, max_id + 1)
        child_tn_lst.append(audio_par)
        max_id += 3  # 各audioノードはcTn idを3つ使う


def _get_max_ctn_id(timing_elem: etree._Element) -> int:
    """timing要素内の最大cTn idを取得する。"""
    max_id = 0
    for ctn in timing_elem.iter(f"{{{_P_NS}}}cTn"):
        id_val = ctn.get("id")
        if id_val is not None:
            max_id = max(max_id, int(id_val))
    return max_id


def _build_audio_par_xml(
    shape_id: int, start_id: int
) -> etree._Element:
    """音声auto-play用のp:parノードを構築する。"""
    xml = f"""<p:par xmlns:p="{_P_NS}">
  <p:cTn id="{start_id}" fill="hold">
    <p:stCondLst>
      <p:cond delay="0"/>
    </p:stCondLst>
    <p:childTnLst>
      <p:par>
        <p:cTn id="{start_id + 1}" fill="hold">
          <p:stCondLst>
            <p:cond delay="0"/>
          </p:stCondLst>
          <p:childTnLst>
            <p:audio>
              <p:cMediaNode>
                <p:cTn id="{start_id + 2}" fill="hold" display="0">
                  <p:stCondLst>
                    <p:cond delay="0"/>
                  </p:stCondLst>
                </p:cTn>
                <p:tgtEl>
                  <p:spTgt spid="{shape_id}"/>
                </p:tgtEl>
              </p:cMediaNode>
            </p:audio>
          </p:childTnLst>
        </p:cTn>
      </p:par>
    </p:childTnLst>
  </p:cTn>
</p:par>"""
    return etree.fromstring(xml)


def _build_timing_xml(audio_shape_ids: list[int]) -> etree._Element:
    """音声auto-play用の完全なp:timing要素を構築する。"""
    audio_pars = ""
    ctn_id = 3
    for shape_id in audio_shape_ids:
        audio_pars += f"""
                <p:par>
                  <p:cTn id="{ctn_id}" fill="hold">
                    <p:stCondLst>
                      <p:cond delay="0"/>
                    </p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="{ctn_id + 1}" fill="hold">
                          <p:stCondLst>
                            <p:cond delay="0"/>
                          </p:stCondLst>
                          <p:childTnLst>
                            <p:audio>
                              <p:cMediaNode>
                                <p:cTn id="{ctn_id + 2}" fill="hold" display="0">
                                  <p:stCondLst>
                                    <p:cond delay="0"/>
                                  </p:stCondLst>
                                </p:cTn>
                                <p:tgtEl>
                                  <p:spTgt spid="{shape_id}"/>
                                </p:tgtEl>
                              </p:cMediaNode>
                            </p:audio>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>"""
        ctn_id += 3

    timing_xml = f"""<p:timing xmlns:p="{_P_NS}">
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>{audio_pars}
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
    return etree.fromstring(timing_xml)


def _find_audio_shape_ids(slide) -> list[int]:
    """スライドから全音声シェイプのIDを取得する。

    a:audioFile要素を持つp:pic要素のcNvPr idをリストで返す。
    """
    ids: list[int] = []
    slide_elem = slide.element
    for audio_file in slide_elem.iter(f"{{{_A_NS}}}audioFile"):
        nv_pr = audio_file.getparent()
        if nv_pr is not None:
            nv_pic_pr = nv_pr.getparent()
            if nv_pic_pr is not None:
                c_nv_pr = nv_pic_pr.find(f"{{{_P_NS}}}cNvPr")
                if c_nv_pr is not None:
                    ids.append(int(c_nv_pr.get("id")))
    return ids
