from __future__ import annotations

import mimetypes   # Actually reads the file content 
from enum import Enum, auto
from pathlib import Path

import magic  

class FileType(Enum):
    """All document types this parser understands."""
    PDF= auto()
    DOCX= auto()
    XLSX= auto()
    PPTX= auto()
    DOC= auto()   # legacy binary — Phase 6
    XLS= auto()   # legacy binary — Phase 6
    PPT= auto()   # legacy binary — Phase 6
    HTML= auto()
    EPUB= auto()
    CSV= auto()
    TSV= auto()
    PARQUET= auto()
    JSON= auto()
    XML= auto()
    EML= auto()
    MSG= auto()
    MBOX= auto()
    IMAGE= auto()    # tiff, bmp, webp, jpg, png
    UNKNOWN= auto()  # never crash — return this for anything unrecognized
    
_EXT_MAP: dict[str, FileType]= {
    ".pdf": FileType.PDF,
    ".docx":    FileType.DOCX,
    ".xlsx":    FileType.XLSX,
    ".pptx":    FileType.PPTX,
    ".doc":     FileType.DOC,
    ".xls":     FileType.XLS,
    ".ppt":     FileType.PPT,
    ".html":    FileType.HTML,
    ".htm":     FileType.HTML,
    ".xhtml":   FileType.HTML,
    ".epub":    FileType.EPUB,
    ".csv":     FileType.CSV,
    ".tsv":     FileType.TSV,
    ".parquet": FileType.PARQUET,
    ".json":    FileType.JSON,
    ".xml":     FileType.XML,
    ".eml":     FileType.EML,
    ".msg":     FileType.MSG,
    ".mbox":    FileType.MBOX,
    ".tiff":    FileType.IMAGE,
    ".tif":     FileType.IMAGE,
    ".bmp":     FileType.IMAGE,
    ".webp":    FileType.IMAGE,
    ".jpg":     FileType.IMAGE,
    ".jpeg":    FileType.IMAGE,
    ".png":     FileType.IMAGE,
}

_MIME_MAP: dict[str, FileType]= {
    "application/pdf":                                          FileType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":   FileType.DOCX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":         FileType.XLSX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "application/msword":                                       FileType.DOC,
    "application/vnd.ms-excel":                                 FileType.XLS,
    "application/vnd.ms-powerpoint":                            FileType.PPT,
    "text/html":                                                FileType.HTML,
    "application/epub+zip":                                     FileType.EPUB,
    "text/csv":                                                 FileType.CSV,
    "text/plain":                                               FileType.CSV,  # resolved by extension
    "application/json":                                         FileType.JSON,
    "text/xml":                                                 FileType.XML,
    "application/xml":                                          FileType.XML,
    "message/rfc822":                                           FileType.EML,
    "image/tiff":                                               FileType.IMAGE,
    "image/bmp":                                                FileType.IMAGE,
    "image/webp":                                               FileType.IMAGE,
    "image/jpeg":                                               FileType.IMAGE,
    "image/png":                                                FileType.IMAGE,
}

def sniff(path: str | Path) -> FileType:
    """
    Detect the file type of the given path.
    Strategy:
        1. Read magic bytes via python-magic -> look up MIME in _MIME_MAP
        2. If ambiguous (e.g. text/plain could be CSV or TSV), fall back to extension
        3. If still unknown, return FileType.UNKNOWN — never raise
    Args:
        path: path to any file
    Returns:
        FileType enum value
    """
    path= Path(path)
    ext= path.suffix.lower()
    
    try:
        mime= magic.from_file(str(path), mime= True)
        file_type= _MIME_MAP.get(mime)
        
        # MIME was recognized but ambiguous — let extension break the tie
        if file_type in (FileType.CSV, None):
            ext_type= _EXT_MAP.get(ext)
            if ext_type is not None:
                return ext_type
            
        if file_type is not None:
            return file_type
        
    except Exception:
        # magic can fail on locked files, permission errors, etc.
        # fall through to extension lookup
        pass
    
    # Last resort: extension only
    return _EXT_MAP.get(ext, FileType.UNKNOWN)