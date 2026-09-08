from universal_parser.core.schema import Document, DocumentMetadata, Element, TableData
from universal_parser.exports.to_chunks import to_chunks
from universal_parser.exports.to_graph import to_graph
from universal_parser.exports.to_markdown import to_markdown


def test_to_markdown_export():
    doc = Document(
        metadata=DocumentMetadata(file_name="sample.pdf", file_type="pdf"),
        content_tree=[
            Element(
                type="heading",
                level=1,
                text="Executive Summary",
                markdown_repr="# Executive Summary",
            ),
            Element(type="paragraph", text="This is an automated parsing report."),
            Element(
                type="table",
                data=TableData(headers=["Quarter", "Growth"], rows=[["Q1", "+15%"]]),
                markdown_repr="| Quarter | Growth |\n| --- | --- |\n| Q1 | +15% |",
            ),
        ],
    )

    md = to_markdown(doc)
    assert "# Executive Summary" in md
    assert "This is an automated parsing report." in md
    assert "| Quarter | Growth |" in md


def test_to_chunks_hierarchical_context():
    doc = Document(
        metadata=DocumentMetadata(file_name="report.docx", file_type="docx"),
        content_tree=[
            Element(type="heading", level=1, text="Architecture Overview"),
            Element(type="heading", level=2, text="Storage Subsystem"),
            Element(
                type="paragraph",
                text="We use S3 for blob storage and PostgreSQL for metadata.",
                page=1,
            ),
        ],
    )

    chunks = to_chunks(doc, max_tokens=100)
    assert len(chunks) == 1
    assert "Architecture Overview > Storage Subsystem" in chunks[0].text
    assert chunks[0].page_numbers == [1]


def test_to_graph_export():
    doc = Document(
        metadata=DocumentMetadata(file_name="spec.pdf", file_type="pdf"),
        content_tree=[
            Element(type="heading", level=1, text="System Design"),
            Element(type="paragraph", text="The pipeline runs on CPU only."),
        ],
    )

    graph = to_graph(doc)
    assert len(graph.nodes) == 3  # Root Document + Heading Section + Paragraph
    assert len(graph.edges) >= 2
    relationships = [edge.relationship for edge in graph.edges]
    assert "CONTAINS_SECTION" in relationships
    assert "CONTAINS" in relationships
