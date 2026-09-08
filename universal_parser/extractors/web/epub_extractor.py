from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import ebooklib
from ebooklib import epub
from selectolax.parser import HTMLParser

from universal_parser.core.router import register
from universal_parser.core.schema import Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class EPUBExtractor(BaseExtractor):
    """
    Extractor for EPUB e-books (.epub) using ebooklib & selectolax.

    Handles:
        - Iterates over document items (chapters/sections)
        - Converts chapter titles to Headings
        - Extracts chapter paragraphs and list items
    """

    supported_types: ClassVar[list[FileType]] = [FileType.EPUB]

    def stream(self, path: str | Path) -> Iterator[Element]:
        path_obj = Path(path)

        try:
            book = epub.read_epub(str(path_obj))

            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                html_content = item.get_content().decode("utf-8", errors="replace")
                if not html_content.strip():
                    continue

                parser = HTMLParser(html_content)

                # Clean noise tags
                for tag in parser.css("script, style, noscript, svg"):
                    tag.decompose()

                body = parser.body or parser.root
                if body is None:
                    continue

                for node in body.iter():
                    tag_name = node.tag.lower() if node.tag else ""

                    # Headings
                    if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                        level = int(tag_name[1])
                        text = node.text(strip=True)
                        if text:
                            yield Element(
                                type="heading",
                                level=level,
                                text=text,
                                markdown_repr=f"{'#' * level} {text}",
                                confidence=1.0,
                            )

                    # Paragraphs & Lists
                    elif tag_name in ("p", "li"):
                        text = node.text(strip=True)
                        if text:
                            prefix = "- " if tag_name == "li" else ""
                            elem_type = "list_item" if tag_name == "li" else "paragraph"
                            yield Element(
                                type=elem_type,
                                text=text,
                                markdown_repr=f"{prefix}{text}",
                                confidence=1.0,
                            )

        except Exception:  # noqa: BLE001
            return
