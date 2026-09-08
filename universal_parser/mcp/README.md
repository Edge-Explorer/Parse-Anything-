# mcp

The universal_parser.mcp module provides a FastMCP server implementation enabling AI assistants (such as Claude Desktop and Cursor) to use the universal parser as a tool.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| server.py | Defines FastMCP tool endpoints over stdio communication. | mcp, parse_document(), list_supported_formats(), 
un_server() |

---

## Technical Details

Exposes stdio RPC endpoints (parse_document and list_supported_formats). parse_document accepts a file path and output format (markdown, chunks, json) and executes the parsing pipeline.

---

## Running the MCP Server

`ash
python -m universal_parser.mcp.server
`
