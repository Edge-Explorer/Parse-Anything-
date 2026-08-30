from __future__ import annotations

import numpy as np
import pdfplumber
from universal_parser.core.schema import TableData

class PDFTableExtractor:
    """
    Handles bordered (Lattice) and borderless (Stream) table extraction from PDF pages.
    
    Provides:
        - Bordered table extraction via coordinate grid mapping
        - Borderless table extraction via whitespace column clustering
        - Confidence scoring based on layout density and cell consistency
    """
    
    def __init__(self, page: pdfplumber.page.Page):
        self.page= page
    
    def extract_tables(self) -> list[dict]:
        """
        Extract all tables from the page.
        
        Returns:
            list[dict]: A list of tables found, each formatted as:
                {
                    "data": TableData,
                    "bbox": tuple(x0, y0, x1, y1),
                    "confidence": float (0.0 to 1.0)
                }
        """
        
        tables= []
        
        # 1. Try Lattice extraction first (bordered tables)
        lattice_tables= self._extract_lattice()
        if lattice_tables:
            tables.extend(lattice_tables)
        
        # 2. Try Stream extraction (borderless tables)
        # We only run stream extraction if we don't find lattice tables
        # to prevent duplicate extractions on the same area.
        if not lattice_tables:
            stream_tables= self._extract_stream()
            if stream_tables:
                tables.extend(stream_tables)
        
        return tables
    
    def _extract_lattice(self) -> list[dict]:
        """Extract tables using vertical and horizontal vector lines."""
        extracted= []
        # pdfplumber vertical and horizontal line settings
        table_settings= {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3
        }
        
        plumber_tables= self.page.find_tables(table_settings= table_settings)
        for table in plumber_tables:
            raw_data= table.extract()
            if not raw_data or len(raw_data) < 2:
                continue
            
            clean_rows= []
            for row in raw_data:
                # Convert None to empty string
                clean_row= [str(cell).strip() if cell is not None else "" for cell in row]
                clean_rows.append(clean_row)
            
            headers= clean_rows[0]
            data_rows= clean_rows[1:]
            
            # Lattice table confidence is high (0.95+) since lines physically define cells
            confidence= 0.98 if all(len(row) == len(headers) for row in data_rows) else 0.90
            
            extracted.append({
                "data": TableData(headers=headers, rows= data_rows),
                "bbox": table.bbox,   # (x0, y0, x1, y1)
                "confidence": confidence
            }) 
            
        return extracted
    
    def _extract_stream(self) -> list[dict]:
        """Extract borderless tables using whitespace distance clustering."""
        # This is a baseline implementation of borderless table detection.
        # We find blocks of text spans that are horizontally aligned in multiple rows.
        extracted= []
        words= self.page.extract_words()
        
        if len(words) < 10:
            return extracted
        
        # Group words into approximate rows based on their vertical (top) coordinate
        rows_dict= {}
        for w in words:
            # Round top coordinate to cluster words into the same line
            top_coord= round(w["top"], 1)
            found_row= False
            
            # Check if there is an existing row within 3 points of vertical distance
            for key in rows_dict:
                if abs(key - w["top"]) <=3.0:
                    rows_dict[key].append(w)
                    found_row= True
                    break
            
            if not found_row:
                rows_dict[w["top"]] = [w]
                
        # Sort rows top-to-bottom
        sorted_rows_keys= sorted(rows_dict.keys())
        
        # Reconstruct lines of text by sorting words left-to-right within each row
        lines=[]
        for key in sorted_rows_keys:
            row_words= sorted(rows_dict[key], key= lambda w: w["x0"])
            lines.append(row_words)
            
        # Identify dense vertical regions that look like borderless tables.
        # If multiple rows have similar horizontal gaps (gaps between words), we flag it.
        # For our baseline MVP, we search for lines containing multiple distinct space gaps
        # that align vertically across at least 3 consecutive lines.
        # Real borderless extraction is highly complex; we'll refine this in Phase 2.
        # For now, if we detect consecutive multi-word lines, we output a low-confidence table:
        table_candidate_lines= []
        for line in lines:
            if len(line) >= 3:  # at least 3 words in a line suggest columns
                table_candidate_lines.append(line)
        
        if len(table_candidate_lines) >= 3:
            # We construct a table representation by mapping words to columns.
            # In a basic table, we can just split lines by large horizontal spaces.
            table_rows= []
            max_cols= 0
            
            for line in table_candidate_lines:
                row_cells= []
                current_cell= []
                
                for i in range(len(line)):
                    w= line[i]
                    current_cell.append(w["text"])
                    
                    # If this is the last word, or the next word is far away (> 15 points)
                    if i == len(line) - 1 or (line[i+1]["x0"]-w["x1"]) > 15.0:
                        row_cells.append(" ".join(current_cell))
                        current_cell=[]
                
                table_rows.append(row_cells)
                max_cols= max(max_cols, len(row_cells))
            
            if len(table_rows) >= 2 and max_cols >= 2:
                # Pad rows to make sure they all have the same column count
                padded_rows= []
                for r in table_rows:
                    if len(r) < max_cols:
                        r= r+[""] * (max_cols - len(r))
                    padded_rows.append(r)
                
                headers= padded_rows[0]
                data_rows= padded_rows[1:]
                
                # Bbox covers from the first word of the first line to the last word of the last line
                x0 = min(line[0]["x0"] for line in table_candidate_lines)
                y0 = min(line[0]["top"] for line in table_candidate_lines)
                x1 = max(line[-1]["x1"] for line in table_candidate_lines)
                y1 = max(line[-1]["bottom"] for line in table_candidate_lines)
                
                # Confidence is low (0.50) since borderless estimation is error-prone
                extracted.append({
                    "data": TableData(headers=headers, rows=data_rows),
                    "bbox": (x0, y0, x1, y1),
                    "confidence": 0.50
                })
        return extracted