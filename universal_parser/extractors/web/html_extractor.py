from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from selectolax.parser import HTMLParser

from universal_parser.core.router import register
from universal_parser.core.schema import Element, TableData
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class HTMLExtractor(BaseExtractor):
    """
    Ultra-fast HTML/XHTML extractor using selectolax.

    Handles:
        - Headings (h1 - h6) preserving document tree hierarchy
        - Text paragraphs (<p>, <li>)
        - HTML <table> tags -> TableData + Markdown tables
        - Strips script, style, and navigation junk tags
    """

    supported_types: ClassVar[list[FileType]] = [FileType.HTML]

    def stream(self, path: str | Path) -> Iterator[Element]:
        path_obj = Path(path)

        try:
            with open(path_obj, encoding="utf-8", errors="replace") as f:
                html_content = f.read()

            if not html_content.strip():
                return

            parser = HTMLParser(html_content)

            # Strip noise (script, style, svg)
            for tag in parser.css("script, style, noscript, svg"):
                tag.decompose()

            body = parser.body or parser.root
            if body is None:
                return

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

                # Paragraphs and Lists
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

                # Tables
                elif tag_name == "table":
                    headers = []
                    rows = []

                    for th in node.css("th"):
                        h_text = th.text(strip=True)
                        if h_text:
                            headers.append(h_text)

                    for tr in node.css("tr"):
                        tds = [td.text(strip=True) for td in tr.css("td")]
                        if any(tds):
                            rows.append(tds)

                    if not headers and rows:
                        headers = [f"Column_{i+1}" for i in range(len(rows[0]))]

                    if headers or rows:
                        md_header = "| " + " | ".join(headers) + " |"
                        md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                        md_rows = ["| " + " | ".join(r) + " |" for r in rows]
                        markdown_repr = "\n".join([md_header, md_separator] + md_rows)

                        yield Element(
                            type="table",
                            text=path_obj.name,
                            data=TableData(headers=headers, rows=rows),
                            markdown_repr=markdown_repr,
                            confidence=1.0,
                        )

        except Exception:  # noqa: BLE001
            return