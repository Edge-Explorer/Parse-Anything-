# enrichment

The universal_parser.enrichment module enhances parsed elements by computing document metrics, structural hierarchy metadata, and semantic metadata.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| hierarchy.py | Reconstructs parent-child tree relations among elements based on heading levels. | uild_hierarchy() |
| cleaner.py | Cleans raw extracted text by normalizing whitespace, unicode characters, and ligatures. | clean_text() |

---

## Technical Details

### Hierarchy Construction (hierarchy.py)
Traverses elements linearly and maintains a stack of active headers (H1 -> H2 -> H3) to assign parent_id properties to every paragraph, list, or table element.
