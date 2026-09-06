from __future__ import annotations

from dataclasses import dataclass, field

from universal_parser.core.schema import Document


@dataclass
class Chunk:
    """A token-budgeted chunk ready for vector database embeddings."""
    chunk_id: str
    text: str
    headings: list[str]= field(default_factory= list)
    element_types: list[str]= field(default_factory= list)
    page_numbers: list[int]= field(default_factory= list)
    estimated_tokens: int= 0
    
def to_chunks(doc: Document, max_tokens: int= 512, overlap_tokens: int= 50,) -> list[Chunk]:
    """
    Hierarchical token-aware chunker for RAG pipelines.
    Rules:
        - Tracks active H1, H2, H3 hierarchy across elements
        - Prefixes chunk with current heading path context
        - Bundles elements until max_tokens budget is reached
        - Keeps tables intact within a single chunk where possible
    """
    chunks: list[Chunk]= []
    current_headings: dict[int, str]= {}   # level -> heading text
    current_elements: list[str]= []
    current_types: list[int]= []
    current_pages: list[int]= []
    current_tokens= 0
    chunk_index= 1
    
    for el in doc.content_tree:
        # 1. Update heading stack
        if el.type == "heading":
            level= el.level or 1
            current_headings= {lvl: txt for lvl, txt in current_headings.items() if lvl < level}
            current_headings[level]= el.text or ""
            
        # 2. Get text representation
        el_text= el.markdown_repr or el.text or ""
        if not el_text.strip():
            continue
        
        # Fast token estimation (~4 chars per token)
        el_tokens= max(1, len(el_text) // 4)
        
        # 3. Check if adding exceeds budget
        if current_tokens + el_tokens > max_tokens and current_elements:
            heading_hierarchy= [txt for _, txt in sorted(current_headings.items())]
            heading_prefix= " > ".join(heading_hierarchy)
            header_str= f"Context: {heading_prefix}\n\n" if heading_prefix else ""
            chunk_text= header_str + "\n\n".join(current_elements)
            total_est= len(chunk_text) // 4
            
            chunks.append(
                Chunk(
                    chunk_id= f"{doc.doc_id}-chunk-{chunk_index}",
                    text= chunk_text,
                    headings= heading_hierarchy,
                    element_types= list(set(current_types)),
                    page_numbers= sorted(set(current_pages)),
                    estimated_tokens= total_est,
                )
            )
            chunk_index += 1
            
            current_elements= []
            current_types= []
            current_pages= []
            current_tokens= []
            
        # 4. Append element to current buffer
        current_elements.append(el_text)
        current_types.append(el.type)
        if el.page is not None:
            current_pages.append(el.page)
        current_tokens += el_tokens
    
    # Flush remaining buffer    
    if current_elements:
        heading_hierarchy= [txt for _, txt in sorted(current_headings.items())]
        heading_prefix= " > ".join(heading_hierarchy)
        header_str= f"Context: {heading_prefix}\n\n" if heading_prefix else ""
        
        chunk_text= header_str + "\n\n".join(current_elements)
        total_est= len(chunk_text) // 4
        
        chunks.append(
            Chunk(
                chunk_id= f"{doc.doc_id}-chunk-{chunk_index}",
                text= chunk_text,
                headings= heading_hierarchy,
                element_types= list(set(current_types)),
                page_numbers= sorted(set(current_pages)),
                estimated_tokens= total_est,
            )
        )
        
    return chunks