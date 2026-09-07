"""PDF text extraction with pdfplumber primary and OCR fallback.

Standalone scraper module. NEVER imports from backend/app/.
Downloads PDFs via httpx, validates %PDF- magic bytes, extracts text with
pdfplumber, falls back to pdf2image + pytesseract OCR if text is blank or
>25% non-ASCII.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pdfplumber
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger("regpulse.extractor")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DOWNLOAD_TIMEOUT = 15.0  # seconds
_TEMP_DIR = Path("/tmp/regpulse")  # noqa: S108
_NON_ASCII_THRESHOLD = 0.25  # 25% non-ASCII triggers OCR fallback
_PDF_MAGIC_BYTES = b"%PDF-"

# Rotating User-Agent pool (reuse from crawler)
_USER_AGENTS: list[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
]

# Default max pages for OCR to bound runtime
DEFAULT_OCR_MAX_PAGES = 10


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ExtractedDocument:
    """Result of PDF text extraction."""

    raw_text: str
    extraction_method: str  # "pdfplumber", "ocr", or "failed"
    page_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractionFailure:
    """Represents a failed extraction with reason for tracking."""

    url: str
    reason: str  # "not_pdf", "download_error", "extraction_error", "empty_after_ocr"


# ---------------------------------------------------------------------------
# PDFExtractor
# ---------------------------------------------------------------------------


class PDFExtractor:
    """Download and extract text from RBI PDF documents.

    Primary extraction via pdfplumber; OCR fallback (pdf2image + pytesseract)
    when text is blank or contains >25% non-ASCII characters.

    Key safety features:
    - Pre-validates %PDF- magic bytes before extraction (catches HTML pages)
    - Catches poppler exceptions per-document; logs + continues
    - OCR limited to configurable max pages to bound runtime
    """

    def __init__(self, *, ocr_max_pages: int = DEFAULT_OCR_MAX_PAGES) -> None:
        self._ocr_max_pages = ocr_max_pages

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def download(self, url: str) -> bytes:
        """Download a PDF from the given URL.

        Returns raw PDF bytes. Stores temp file at /tmp/regpulse/{uuid}.pdf.
        """
        _TEMP_DIR.mkdir(parents=True, exist_ok=True)
        file_id = uuid.uuid4()
        temp_path = _TEMP_DIR / f"{file_id}.pdf"

        headers = {
            "User-Agent": random.choice(_USER_AGENTS),  # noqa: S311
            "Accept": "application/pdf,*/*",
        }

        async with httpx.AsyncClient(
            timeout=_DOWNLOAD_TIMEOUT,
            follow_redirects=True,
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        pdf_bytes = response.content
        temp_path.write_bytes(pdf_bytes)

        logger.info(
            "pdf_downloaded",
            url=url,
            size_bytes=len(pdf_bytes),
            temp_path=str(temp_path),
        )
        return pdf_bytes

    @staticmethod
    def validate_pdf_bytes(pdf_bytes: bytes) -> bool:
        """Check if bytes start with %PDF- magic marker.

        Returns True if valid PDF, False otherwise. This catches the most
        common failure mode: HTML pages served instead of PDFs.
        """
        if not pdf_bytes or len(pdf_bytes) < 5:
            return False
        return pdf_bytes[:5] == _PDF_MAGIC_BYTES

    def extract_pdfplumber(self, pdf_bytes: bytes) -> tuple[str, int]:
        """Extract text from PDF bytes using pdfplumber.

        Returns (extracted_text, page_count). Inserts page markers between pages.
        """
        pages_text: list[str] = []
        page_count = 0

        with pdfplumber.open(_bytes_to_tmp_file(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages_text.append(f"--- Page {i} ---\n{text}")

        full_text = "\n\n".join(pages_text)
        logger.info(
            "pdfplumber_extraction",
            page_count=page_count,
            text_length=len(full_text),
        )
        return full_text, page_count

    def extract_ocr(self, pdf_bytes: bytes, *, max_pages: int | None = None) -> tuple[str, int]:
        """Extract text from PDF bytes using OCR (pdf2image + pytesseract).

        Returns (extracted_text, page_count).
        Raises RuntimeError if pdf2image/poppler is not available.

        Args:
            max_pages: Maximum number of pages to OCR. Defaults to
                       self._ocr_max_pages.
        """
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise RuntimeError(
                "pdf2image not installed or poppler missing — OCR fallback unavailable"
            ) from exc

        import pytesseract

        effective_max = max_pages if max_pages is not None else self._ocr_max_pages

        images = convert_from_bytes(pdf_bytes)
        total_page_count = len(images)

        # Limit pages to OCR to bound runtime
        if effective_max and len(images) > effective_max:
            logger.warning(
                "ocr_page_limit_applied",
                total_pages=total_page_count,
                max_pages=effective_max,
            )
            images = images[:effective_max]

        pages_text: list[str] = []
        for i, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image, lang="eng")
            pages_text.append(f"--- Page {i} ---\n{text}")

        full_text = "\n\n".join(pages_text)
        logger.info(
            "ocr_extraction",
            page_count=total_page_count,
            pages_ocrd=len(images),
            text_length=len(full_text),
        )
        return full_text, total_page_count

    async def extract(self, url: str) -> ExtractedDocument:
        """Download PDF and extract text. Try pdfplumber first; fall back to OCR.

        Pre-validates %PDF- magic bytes. Returns a failed ExtractedDocument
        (empty text) for non-PDF content instead of crashing.

        OCR fallback triggers when:
        - pdfplumber returns blank/empty text
        - Extracted text has >25% non-ASCII characters (scanned PDF artifact)
        """
        warnings: list[str] = []

        try:
            # Step 1: Download
            try:
                pdf_bytes = await self.download(url)
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                logger.warning("pdf_download_failed", url=url, error=str(exc))
                return ExtractedDocument(
                    raw_text="",
                    extraction_method="failed",
                    page_count=0,
                    warnings=[f"Download failed: {exc}"],
                )

            # Step 2: Validate magic bytes — this is the key guard against
            # HTML pages, .aspx responses, and other non-PDF content.
            if not self.validate_pdf_bytes(pdf_bytes):
                # Log a snippet of what we actually got for debugging
                preview = pdf_bytes[:100].decode("utf-8", errors="replace")
                logger.warning(
                    "pdf_magic_bytes_invalid",
                    url=url,
                    preview=preview[:80],
                    content_length=len(pdf_bytes),
                )
                return ExtractedDocument(
                    raw_text="",
                    extraction_method="failed",
                    page_count=0,
                    warnings=[
                        f"Not a valid PDF (missing %PDF- header). " f"Got: {preview[:40]}..."
                    ],
                )

            # Step 3: Primary extraction via pdfplumber
            try:
                raw_text, page_count = self.extract_pdfplumber(pdf_bytes)
            except Exception as exc:
                warnings.append(f"pdfplumber failed: {exc}")
                logger.warning(
                    "pdfplumber_extraction_failed",
                    url=url,
                    error=str(exc),
                )
                raw_text = ""
                page_count = 0

            # Step 4: Decide if OCR is needed
            needs_ocr = False
            stripped = raw_text.replace("--- Page", "").strip()

            if not stripped:
                needs_ocr = True
                warnings.append("pdfplumber returned blank text — trying OCR")
            elif _non_ascii_ratio(stripped) > _NON_ASCII_THRESHOLD:
                needs_ocr = True
                warnings.append(
                    f"pdfplumber text has >{_NON_ASCII_THRESHOLD * 100:.0f}% "
                    "non-ASCII — trying OCR"
                )

            # Step 5: OCR fallback
            if needs_ocr:
                try:
                    raw_text, page_count = self.extract_ocr(pdf_bytes)
                    extraction_method = "ocr"
                except RuntimeError as exc:
                    warnings.append(str(exc))
                    extraction_method = "pdfplumber"
                except Exception as exc:
                    warnings.append(f"OCR fallback failed: {exc}")
                    logger.warning(
                        "ocr_fallback_failed",
                        url=url,
                        error=str(exc),
                    )
                    extraction_method = "pdfplumber"
            else:
                extraction_method = "pdfplumber"

            logger.info(
                "extraction_complete",
                url=url,
                method=extraction_method,
                page_count=page_count,
                text_length=len(raw_text),
                warnings=warnings,
            )

            return ExtractedDocument(
                raw_text=raw_text,
                extraction_method=extraction_method,
                page_count=page_count,
                warnings=warnings,
            )

        except Exception as exc:
            # Catch-all: never crash the entire scraper run for one document.
            logger.error(
                "extraction_unexpected_error",
                url=url,
                error=str(exc),
                exc_info=True,
            )
            return ExtractedDocument(
                raw_text="",
                extraction_method="failed",
                page_count=0,
                warnings=[f"Unexpected extraction error: {exc}"],
            )

        finally:
            # Clean up temp files
            _cleanup_temp_dir()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bytes_to_tmp_file(pdf_bytes: bytes) -> Path:
    """Write PDF bytes to a temp file and return the path."""
    _TEMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = _TEMP_DIR / f"{uuid.uuid4()}.pdf"
    tmp_path.write_bytes(pdf_bytes)
    return tmp_path


def _non_ascii_ratio(text: str) -> float:
    """Calculate the ratio of non-ASCII characters in text."""
    if not text:
        return 0.0
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return non_ascii / len(text)


def _cleanup_temp_dir() -> None:
    """Remove all .pdf files in /tmp/regpulse/ older than current session."""
    try:
        if _TEMP_DIR.exists():
            for f in _TEMP_DIR.glob("*.pdf"):
                try:
                    f.unlink()
                except OSError:
                    pass
    except OSError:
        pass
