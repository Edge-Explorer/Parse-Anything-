# extractors/structured

Extractor implementations for structured data formats (CSV, TSV, Parquet, JSON, XML).

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| csv_tsv.py | CSV/TSV dialect sniffer and tabular data parser. | CSVTSVExtractor |
| parquet.py | PyArrow columnar streaming parquet file parser. | ParquetExtractor |
| json_xml.py | JSON tree flattener and XML element tree extractor. | JSONXMLExtractor |
