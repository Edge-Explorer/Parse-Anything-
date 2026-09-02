from __future__ import annotations

import universal_parser.extractors.office.docx_extractor
import universal_parser.extractors.office.xlsx_extractor

# Import all extractors to trigger their @register decorators.
# Without this, the router registry remains empty until the files are imported.
import universal_parser.extractors.pdf.native
import universal_parser.extractors.structured.csv_extractor
import universal_parser.extractors.structured.json_xml_extractor
import universal_parser.extractors.structured.parquet_extractor
import universal_parser.extractors.web.html_extractor  # noqa: F401

# Import the main entry point to expose it at the root of the package
from universal_parser.core.engine import parse

# Define what is exposed when doing: from universal_parser import *
__all__ = ["parse"]
