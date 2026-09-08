# extractors/mail

Extractor implementations for email message formats (.eml, .msg, .mbox).

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| eml.py | EML and MBOX email parser with mime body decoding and attachment extraction. | EMLExtractor |
| msg.py | Outlook MSG binary compound document parser. | MSGExtractor |
