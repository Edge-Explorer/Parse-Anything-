# exports

The universal_parser.exports module handles downstream data transformation, converting parsed Document objects into Markdown, hierarchical RAG chunks, and Knowledge Graphs.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| markdown.py | Renders Document elements into clean GitHub-Flavored Markdown. | 	o_markdown() |
| chunking.py | Constructs heading-aware hierarchical chunks for vector databases. | 	o_chunks(), Chunk |
| graph.py | Builds entity and containment graphs for knowledge representation. | 	o_graph() |

---

## Technical Details

### Markdown Generation (markdown.py)
Converts structural elements (headings, paragraphs, tables, lists) into formatted Markdown syntax, automatically formatting tables into GFM pipe tables.

### Hierarchical Chunking (chunking.py)
Maintains a sliding window over document elements while tracking active heading paths. Prepends ancestor headings (e.g. [Document Title > Section 1]) to every chunk context payload to prevent retrieval hallucinations.

---

## Usage Example

`python
from universal_parser.exports import to_markdown, to_chunks

# md = to_markdown(doc)
# chunks = to_chunks(doc, max_tokens=512)
`
