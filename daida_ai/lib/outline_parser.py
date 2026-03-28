"""Markdownアウトラインを構造化データに変換するパーサー"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class OutlineSection:
    """アウトラインの1セクション（## 見出し + 箇条書き）"""

    title: str
    items: list[str] = field(default_factory=list)


@dataclass
class Outline:
    """パース済みアウトライン全体"""

    title: str
    sections: list[OutlineSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "sections": [
                {"title": s.title, "items": list(s.items)} for s in self.sections
            ],
        }


_RE_H1 = re.compile(r"^#\s+(.+)$")
_RE_H2 = re.compile(r"^##\s+(.+)$")
_RE_ITEM = re.compile(r"^(\s*)-\s+(.+)$")


def parse_outline(md: str) -> Outline:
    """Markdown文字列をOutlineに変換する。

    Args:
        md: Markdownアウトライン文字列

    Returns:
        パース済みOutline

    Raises:
        ValueError: 空文字列またはH1タイトルがない場合
    """
    if not md.strip():
        raise ValueError("Outline is empty")

    title: str | None = None
    sections: list[OutlineSection] = []
    current_section: OutlineSection | None = None

    for line in md.splitlines():
        # H1: プレゼンタイトル
        h1 = _RE_H1.match(line)
        if h1:
            title = h1.group(1).strip()
            continue

        # H2: セクション
        h2 = _RE_H2.match(line)
        if h2:
            current_section = OutlineSection(title=h2.group(1).strip())
            sections.append(current_section)
            continue

        # 箇条書き（ネストも含む）
        item = _RE_ITEM.match(line)
        if item and current_section is not None:
            current_section.items.append(item.group(2).strip())
            continue

    if title is None:
        raise ValueError("Title (H1) heading not found")

    return Outline(title=title, sections=sections)
