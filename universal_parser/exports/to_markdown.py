from __future__ import annotations

from universal_parser.core.schema import Document


def to_markdown(doc: Document) -> str:
    """
    Convert a parsed Document into a clean, unified Markdown string.
    Rules:
        - Headings render as # H1, ## H2, ### H3
        - Paragraphs render as clean prose
        - List items render with "- "
        - Tables render with structured Markdown grids
        - Code blocks render within ``` fences
    """
    blocks: list[str] = []

    for el in doc.content_tree:
        if el.markdown_repr:
            blocks.append(el.markdown_repr)
        elif el.type == "heading":
            level = el.level or 1
            blocks.append(f"{'#' * level} {el.text or ''}")
        elif el.type == "list_item":
            blocks.append(f"- {el.text or ''}")
        elif el.type == "code_block":
            blocks.append(f"```\n{el.text or ''}\n```")
        elif el.text:
            blocks.append(el.text)

    return "\n\n".join(blocks)
