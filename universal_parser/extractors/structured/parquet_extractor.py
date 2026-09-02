from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pyarrow.parquet as pq

from universal_parser.core.router import register
from universal_parser.core.schema import Element, TableData
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class ParquetExtractor(BaseExtractor):
    """
    Extractor for Apache Parquet files (.parquet).
    Handles:
        - Reads schema headers and row data using pyarrow
        - Converts columnar data into structured TableData & Markdown
    """
    supported_types: ClassVar[list[FileType]]= [FileType.PARQUET]
    
    def stream(self, path: str | Path) -> Iterator[Element]:
        path_obj= Path(path)
        
        try:
            parquet_file= pq.ParquetFile(str(path_obj))
            schema= parquet_file.schema.to_arrow_schema()
            headers= schema.names
            
            # Read table data
            table= parquet_file.read()
            df_dict= table.to_pydict()
            
            num_rows= table.num_rows
            rows= []
            for i in range(num_rows):
                row= [str(df_dict[col][i]).strip() for col in headers] 
                rows.append(row) 
                
            # Generate markdown table representation
            md_header = "| " + " | ".join(headers) + " |"
            md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
            md_rows = ["| " + " | ".join(r) + " |" for r in rows]
            markdown_repr = "\n".join([md_header, md_separator] + md_rows)
            
            yield Element(
                type= "table",
                text= path_obj.name,
                data= TableData(headers= headers, rows= rows),
                markdown_repr= markdown_repr,
                confidence= 1.0,
            )
        
        except Exception:     # noqa: BLE001
            return