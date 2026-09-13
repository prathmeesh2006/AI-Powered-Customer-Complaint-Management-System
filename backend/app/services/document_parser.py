"""
Document parser service.

Handles file → normalized text conversion BEFORE the LangGraph workflow starts.
File binary handling stays here, not in LangGraph nodes (architectural correction #3).

Supported formats:
- PDF (text-based, not image-only)
- Plain text files

For image-only PDFs where text extraction yields < 50 characters:
Returns a controlled parse_error rather than pretending extraction succeeded.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MAX_EXTRACTED_TEXT_LENGTH = 50_000  # cap to avoid huge LLM prompts


@dataclass
class ParseResult:
    success: bool
    text: Optional[str] = None
    filename: str = ""
    mime_type: str = ""
    file_size_bytes: int = 0
    error: Optional[str] = None
    is_image_only: bool = False


def parse_uploaded_file(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> ParseResult:
    """
    Convert uploaded file bytes to normalized text.
    Returns ParseResult with success=False and error message on failure.
    """
    file_size = len(file_bytes)
    logger.info("Parsing file: %s (%s, %d bytes)", filename, mime_type, file_size)

    # Normalize mime type from filename if browser sends octet-stream
    effective_mime = mime_type
    if effective_mime == "application/octet-stream":
        if filename.lower().endswith(".pdf"):
            effective_mime = "application/pdf"
        elif filename.lower().endswith(".txt"):
            effective_mime = "text/plain"

    if effective_mime == "application/pdf":
        return _parse_pdf(file_bytes, filename, file_size)
    elif effective_mime.startswith("text/"):
        return _parse_text(file_bytes, filename, mime_type, file_size)
    else:
        return ParseResult(
            success=False,
            filename=filename,
            mime_type=mime_type,
            file_size_bytes=file_size,
            error=(
                f"Unsupported file type: {mime_type}. "
                "Please upload a PDF or plain text file, or paste the complaint text directly."
            ),
        )


def _parse_pdf(file_bytes: bytes, filename: str, file_size: int) -> ParseResult:
    """Extract text from a text-based PDF using pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        all_text_parts = []
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                all_text_parts.append(page_text)

        full_text = "\n".join(all_text_parts).strip()

        if len(full_text) < 50:
            return ParseResult(
                success=False,
                filename=filename,
                mime_type="application/pdf",
                file_size_bytes=file_size,
                is_image_only=True,
                error=(
                    "The uploaded PDF appears to be image-based and could not be read "
                    "by the demo text extractor. Please paste the complaint text directly, "
                    "or use a text-based PDF."
                ),
            )

        # Truncate if very large
        if len(full_text) > MAX_EXTRACTED_TEXT_LENGTH:
            full_text = full_text[:MAX_EXTRACTED_TEXT_LENGTH] + "\n[... document truncated ...]"

        logger.info("PDF parsed successfully: %d chars from %d pages", len(full_text), len(reader.pages))
        return ParseResult(
            success=True,
            text=full_text,
            filename=filename,
            mime_type="application/pdf",
            file_size_bytes=file_size,
        )

    except ImportError:
        return ParseResult(
            success=False,
            filename=filename,
            mime_type="application/pdf",
            file_size_bytes=file_size,
            error="PDF parsing library not available. Please install pypdf.",
        )
    except Exception as e:
        logger.error("PDF parse error: %s", str(e))
        return ParseResult(
            success=False,
            filename=filename,
            mime_type="application/pdf",
            file_size_bytes=file_size,
            error=f"Could not read the PDF file: {str(e)}. Try another file or paste the complaint text.",
        )


def _parse_text(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    file_size: int,
) -> ParseResult:
    """Decode plain text file."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(encoding).strip()
            if text:
                logger.info("Text file parsed with encoding %s: %d chars", encoding, len(text))
                return ParseResult(
                    success=True,
                    text=text[:MAX_EXTRACTED_TEXT_LENGTH],
                    filename=filename,
                    mime_type=mime_type,
                    file_size_bytes=file_size,
                )
        except UnicodeDecodeError:
            continue

    return ParseResult(
        success=False,
        filename=filename,
        mime_type=mime_type,
        file_size_bytes=file_size,
        error="Could not decode the text file. Please ensure it is UTF-8 or paste the content directly.",
    )
