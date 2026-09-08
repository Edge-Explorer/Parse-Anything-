from __future__ import annotations

from dataclasses import dataclass, field

from universal_parser.core.schema import Document


@dataclass
class GraphNode:
    id: str
    type: str  # "document", "section", "table", "content"
    properties: dict[str, str | int | float] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str  # "CONTAINS_SECTION", "CONTAINS", "FOLLOWS"


@dataclass
class KnowledgeGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


def to_graph(doc: Document) -> KnowledgeGraph:
    """
    Export Document into a Knowledge Graph structure for GraphRAG & Neo4j.

    Creates:
        - Document Root Node
        - Heading / Section Nodes with hierarchical edges
        - Paragraph & Table Content Nodes linked to their parent sections
    """
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    # 1. Document Root Node
    doc_node_id = f"doc:{doc.doc_id}"
    nodes.append(
        GraphNode(
            id=doc_node_id,
            type="document",
            properties={
                "file_name": doc.metadata.file_name,
                "file_type": doc.metadata.file_type,
            },
        )
    )

    heading_stack: list[tuple[int, str]] = []  # (level, node_id)
    prev_node_id: str | None = None

    for idx, el in enumerate(doc.content_tree, start=1):
        node_id = f"el:{doc.doc_id}:{idx}"

        if el.type == "heading":
            level = el.level or 1
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()

            parent_id = heading_stack[-1][1] if heading_stack else doc_node_id

            nodes.append(
                GraphNode(
                    id=node_id,
                    type="section",
                    properties={"title": el.text or "", "level": level},
                )
            )
            edges.append(
                GraphEdge(
                    source_id=parent_id,
                    target_id=node_id,
                    relationship="CONTAINS_SECTION",
                )
            )
            heading_stack.append((level, node_id))

        else:
            parent_id = heading_stack[-1][1] if heading_stack else doc_node_id
            node_type = "table" if el.type == "table" else "content"

            nodes.append(
                GraphNode(
                    id=node_id,
                    type=node_type,
                    properties={
                        "text": el.text or el.markdown_repr or "",
                        "element_type": el.type,
                    },
                )
            )
            edges.append(
                GraphEdge(
                    source_id=parent_id,
                    target_id=node_id,
                    relationship="CONTAINS",
                )
            )

        if prev_node_id:
            edges.append(
                GraphEdge(
                    source_id=prev_node_id,
                    target_id=node_id,
                    relationship="FOLLOWS",
                )
            )
        prev_node_id = node_id

    return KnowledgeGraph(nodes=nodes, edges=edges)
