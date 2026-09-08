# docs

This directory contains the official technical documentation for the universal-doc-parser library. Each file covers a distinct aspect of the system at a level of depth that is not appropriate for the project README but is essential for contributors, integrators, and power users.

---

## Contents

| File | Description |
|---|---|
| `ARCHITECTURE.md` | End-to-end technical architecture documentation covering the extraction pipeline, data flow, schema design, and subsystem responsibilities. Intended for contributors and engineering teams evaluating the library for integration into complex data systems. |
| `SCHEMA.md` | Complete field-level reference for the Pydantic v2 `Document`, `DocumentMetadata`, `Element`, `BBox`, and `TableData` output schemas including field types, optionality, and invariants. |
| `ADDING_A_FORMAT.md` | Step-by-step guide for contributors implementing support for a new file format, covering extractor class structure, format registration, fixture requirements, and test module standards. |
| `CHANGELOG.md` | Full version-by-version release history for the project, organized by Semantic Version with no dates recorded per entry. Each release entry documents the motivation for the release, new capabilities added, changed behaviors, and bugs fixed. |

---

## CHANGELOG.md

The changelog is the authoritative record of every version released to PyPI. It follows Semantic Versioning and does not include dates on individual release entries. Each release section documents:

- **Release Context:** A paragraph explaining the motivation and scope of the release.
- **Added:** New capabilities, modules, classes, or configuration options introduced.
- **Changed:** Modified behaviors, API signature changes, configuration defaults, or dependency version updates.
- **Fixed:** Bugs resolved, incorrect behaviors corrected, or reliability issues addressed.

---

## ARCHITECTURE.md

The architecture document covers:

- The two-pass PDF extraction pipeline (Pass 1: Table extraction with Lattice and Stream strategies; Pass 2: text and heading extraction with table region masking).
- The magic-byte MIME detection and extractor routing registry.
- The column clustering algorithm for multi-column PDF reading order preservation.
- The font-size percentile hierarchy computation for structured heading trees.
- The adaptive layout fingerprinting subsystem.
- The downstream RAG export layer.
- The observability telemetry infrastructure.

---

## SCHEMA.md

The schema document provides the complete field reference for the `Document` output type returned by `parse()`. It includes:

- Every field on `Document`, `DocumentMetadata`, `Element`, `BBox`, and `TableData`.
- The exact Python type annotation for each field.
- Whether each field is required or optional.
- The semantics and invariants of each field.
- Example populated instances for the most common field combinations.

---

## ADDING_A_FORMAT.md

The contributor guide for new format support covers:

- How to register a new `FileType` enum variant.
- How to implement the `BaseExtractor` interface.
- How to annotate the extractor class with `@register(FileType.MY_FORMAT)`.
- Fixture file requirements.
- Test module structure and coverage expectations.
- How to update the README supported formats table.

---

## Contributing to Documentation

When modifying or adding documentation in this directory:

1. Do not add emojis. Maintain a professional, technical tone throughout.
2. Do not add dates to CHANGELOG entries. Version identifiers are the canonical references.
3. When adding a new file, add an entry to the table in this README.
4. Code examples must be verified as executable against the current library version before merging.
5. All Markdown in this directory is linted as part of the CI pipeline.
