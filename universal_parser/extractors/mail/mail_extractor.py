from __future__ import annotations

import email
import mailbox
import tempfile
from collections.abc import Iterator
from email import policy
from pathlib import Path
from typing import ClassVar

import extract_msg
from selectolax.parser import HTMLParser

from universal_parser.core.router import get_extractor, register
from universal_parser.core.schema import Element
from universal_parser.core.sniffer import FileType, sniff
from universal_parser.extractors.base import BaseExtractor


@register
class MailExtractor(BaseExtractor):
    """
    Extractor for email formats (.eml, .msg, .mbox).

    Handles:
        - Header metadata (Subject, From, To, Date)
        - Body extraction (HTML / Plaintext via selectolax)
        - Recursive attachment parsing through the sniffer/router
    """

    supported_types: ClassVar[list[FileType]] = [
        FileType.EML,
        FileType.MSG,
        FileType.MBOX,
    ]

    def stream(self, path: str | Path) -> Iterator[Element]:
        path_obj = Path(path)
        ext = path_obj.suffix.lower()

        if ext == ".eml":
            yield from self._stream_eml(path_obj)
        elif ext == ".msg":
            yield from self._stream_msg(path_obj)
        elif ext == ".mbox":
            yield from self._stream_mbox(path_obj)

    def _stream_eml(self, path: Path) -> Iterator[Element]:
        try:
            with open(path, "rb") as f:
                msg = email.message_from_binary_file(f, policy=policy.default)

            yield from self._process_email_message(msg)
        except Exception:  # noqa: BLE001
            return

    def _stream_msg(self, path: Path) -> Iterator[Element]:
        try:
            msg = extract_msg.Message(str(path))
            subject = msg.subject or "No Subject"
            sender = msg.sender or "Unknown Sender"
            to = msg.to or "Unknown Recipient"
            date = str(msg.date) if msg.date else ""

            yield Element(
                type="heading",
                level=1,
                text=f"Subject: {subject}",
                markdown_repr=f"# Subject: {subject}",
                confidence=1.0,
            )

            meta_text = f"From: {sender} | To: {to}" + (f" | Date: {date}" if date else "")
            yield Element(
                type="paragraph",
                text=meta_text,
                markdown_repr=f"**{meta_text}**",
                confidence=1.0,
            )

            body_text = msg.body
            if body_text:
                for paragraph in body_text.split("\n\n"):
                    clean_p = paragraph.strip()
                    if clean_p:
                        yield Element(
                            type="paragraph",
                            text=clean_p,
                            markdown_repr=clean_p,
                            confidence=1.0,
                        )

            # Process attachments recursively
            for att in msg.attachments:
                att_data = att.data
                att_name = att.longFilename or att.shortFilename or "attachment"
                if att_data:
                    yield from self._process_attachment_bytes(att_name, att_data)

            msg.close()
        except Exception:  # noqa: BLE001
            return

    def _stream_mbox(self, path: Path) -> Iterator[Element]:
        try:
            mbox = mailbox.mbox(str(path))
            for _, msg in mbox.items():
                yield from self._process_email_message(msg)
        except Exception:  # noqa: BLE001
            return

    def _process_email_message(self, msg: email.message.EmailMessage) -> Iterator[Element]:
        subject = str(msg.get("Subject", "No Subject"))
        sender = str(msg.get("From", "Unknown Sender"))
        to = str(msg.get("To", "Unknown Recipient"))
        date = str(msg.get("Date", ""))

        yield Element(
            type="heading",
            level=1,
            text=f"Subject: {subject}",
            markdown_repr=f"# Subject: {subject}",
            confidence=1.0,
        )

        meta_text = f"From: {sender} | To: {to}" + (f" | Date: {date}" if date else "")
        yield Element(
            type="paragraph",
            text=meta_text,
            markdown_repr=f"**{meta_text}**",
            confidence=1.0,
        )

        # Body extraction
        body_part = msg.get_body(preferencelist=("html", "plain"))
        if body_part:
            content = body_part.get_content()
            if body_part.get_content_type() == "text/html":
                parser = HTMLParser(content)
                for tag in parser.css("script, style, noscript"):
                    tag.decompose()
                body_elem = parser.body or parser.root
                if body_elem:
                    for node in body_elem.iter():
                        tag_name = node.tag.lower() if node.tag else ""
                        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                            h_text = node.text(strip=True)
                            if h_text:
                                yield Element(
                                    type="heading",
                                    level=int(tag_name[1]),
                                    text=h_text,
                                    markdown_repr=f"{'#' * int(tag_name[1])} {h_text}",
                                    confidence=1.0,
                                )
                        elif tag_name in ("p", "li"):
                            p_text = node.text(strip=True)
                            if p_text:
                                yield Element(
                                    type="paragraph",
                                    text=p_text,
                                    markdown_repr=p_text,
                                    confidence=1.0,
                                )
            else:
                for paragraph in str(content).split("\n\n"):
                    clean_p = paragraph.strip()
                    if clean_p:
                        yield Element(
                            type="paragraph",
                            text=clean_p,
                            markdown_repr=clean_p,
                            confidence=1.0,
                        )

        # Attachment extraction (recursive)
        for part in msg.iter_attachments():
            filename = part.get_filename() or "attachment"
            payload = part.get_payload(decode=True)
            if payload:
                yield from self._process_attachment_bytes(filename, payload)

    def _process_attachment_bytes(self, filename: str, data: bytes) -> Iterator[Element]:
        """Save attachment to temp file, sniff type, and route to sub-extractor."""
        try:
            suffix = Path(filename).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = Path(tmp.name)

            file_type = sniff(tmp_path)
            extractor = get_extractor(file_type)

            if extractor:
                yield Element(
                    type="heading",
                    level=2,
                    text=f"Attachment: {filename}",
                    markdown_repr=f"## Attachment: {filename}",
                    confidence=1.0,
                )
                yield from extractor.stream(tmp_path)

            tmp_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            return