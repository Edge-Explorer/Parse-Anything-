from universal_parser.core.schema import Document, DocumentMetadata, Element, TableData
from universal_parser.exports.to_markdown import to_markdown


def test_to_markdown_exports():
    doc= Document(
        metadata= DocumentMetadata(file_name= "sample.pdf", file_type= "pdf"),
        content_tree= [
            Element(type= "heading", level= 1, text= "Executive Summary", markdown_repr= "# Executive Summary"),
            Element(type= "paragraph", text= "This is an automated parsing report."),
            Element(
                type= "table",
                data= TableData(headers=["Quarter", "Growth"], rows=[["Q1", "+15%"]]),
                markdown_repr= "| Quarter | Growth |\n| --- | --- |\n| Q1 | +15% |",
            ),
        ],
    )
    
    md= to_markdown(doc)
    
    assert "# Executive Summary" in md
    assert "This is an automated parsing report." in md
    assert "| Quarter | Growth |" in md
    assert "| Q1 | +15% |" in md