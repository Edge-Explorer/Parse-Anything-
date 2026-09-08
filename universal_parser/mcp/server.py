from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from universal_parser.core.engine import parse
from universal_parser.core.router import FORMAT_REGISTRY
from universal_parser.exports.to_chunks import to_chunks
from universal_parser.exports.to_markdown import to_markdown

# Initialize FastMCP Server
mcp = FastMCP(
    "universal-parser",
    instructions="A zero-GPU universal document ingestion engine for RAG and AI agents.",
)


@mcp.tool()
def parse_document(file_path: str, output_format: str = "markdown") -> str:
    """
    Parse any local document (PDF, DOCX, XLSX, PPTX, HTML, EPUB, CSV, JSON, XML, Parquet, Email, Image).
    Args:
        file_path: Path to the document.
        output_format: 'markdown', 'chunks', or 'json'.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    try:
        doc = parse(path)

        if output_format == "markdown":
            return to_markdown(doc)
        elif output_format == "chunks":
            chunks = to_chunks(doc, max_tokens=512)
            return json.dumps([c.__dict__ for c in chunks], indent=2)
        elif output_format == "json":
            return doc.model_dump_json(indent=2)
        else:
            return f"Error: Unknown output format '{output_format}'. Use 'markdown', 'chunks' or 'json'."

    except Exception as e:  # noqa: BLE001
        return f"Error parsing document: {e!s}"


@mcp.tool()
def list_supported_formats() -> list[str]:
    """List all document file formats supported by Universal Parser."""
    return sorted({ft.name.lower() for ft in FORMAT_REGISTRY})


def run_server() -> None:
    """Run the MCP server over standard I/O (stdio)."""
    mcp.run(transport="studio")


if __name__ == "__main__":
    run_server()
