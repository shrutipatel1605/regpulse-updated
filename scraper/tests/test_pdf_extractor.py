"""Tests for scraper/extractor/pdf_extractor.py

Three test cases as specified:
(i)   Good PDF → text extracted via pdfplumber
(ii)  Scanned PDF → OCR fallback path
(iii) Malformed/non-PDF → graceful skip (no crash)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.extractor.pdf_extractor import (
    ExtractedDocument,
    PDFExtractor,
    _non_ascii_ratio,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def extractor() -> PDFExtractor:
    return PDFExtractor(ocr_max_pages=5)


@pytest.fixture
def good_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "good_sample.pdf").read_bytes()


@pytest.fixture
def html_not_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "html_not_pdf.pdf").read_bytes()


@pytest.fixture
def scanned_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "scanned_sample.pdf").read_bytes()


@pytest.fixture
def real_rbi_pdf_bytes() -> bytes:
    """Use the actual RBI test PDF if available."""
    rbi_pdf = Path(__file__).parent.parent / "test_RBI.pdf"
    if rbi_pdf.exists():
        return rbi_pdf.read_bytes()
    pytest.skip("test_RBI.pdf not available")


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestNonAsciiRatio:
    def test_empty_string(self) -> None:
        assert _non_ascii_ratio("") == 0.0

    def test_all_ascii(self) -> None:
        assert _non_ascii_ratio("Hello World") == 0.0

    def test_mixed(self) -> None:
        ratio = _non_ascii_ratio("Hello\u00e9\u00e8")
        assert ratio == pytest.approx(2 / 7)

    def test_all_non_ascii(self) -> None:
        assert _non_ascii_ratio("\u00e9\u00e8\u00ea") == 1.0


# ---------------------------------------------------------------------------
# validate_pdf_bytes tests
# ---------------------------------------------------------------------------


class TestValidatePdfBytes:
    def test_valid_pdf_magic(self, extractor: PDFExtractor) -> None:
        assert extractor.validate_pdf_bytes(b"%PDF-1.4 some content")

    def test_html_content_rejected(self, extractor: PDFExtractor) -> None:
        assert not extractor.validate_pdf_bytes(b"<!DOCTYPE html>")

    def test_empty_bytes_rejected(self, extractor: PDFExtractor) -> None:
        assert not extractor.validate_pdf_bytes(b"")

    def test_short_bytes_rejected(self, extractor: PDFExtractor) -> None:
        assert not extractor.validate_pdf_bytes(b"%PD")

    def test_real_pdf_fixture(self, extractor: PDFExtractor, good_pdf_bytes: bytes) -> None:
        assert extractor.validate_pdf_bytes(good_pdf_bytes)

    def test_html_fixture(self, extractor: PDFExtractor, html_not_pdf_bytes: bytes) -> None:
        assert not extractor.validate_pdf_bytes(html_not_pdf_bytes)


# ---------------------------------------------------------------------------
# Case (i): Good PDF → text extracted
# ---------------------------------------------------------------------------


class TestGoodPdfExtraction:
    def test_pdfplumber_extracts_text(self, extractor: PDFExtractor, good_pdf_bytes: bytes) -> None:
        text, page_count = extractor.extract_pdfplumber(good_pdf_bytes)
        assert page_count >= 1
        # The fixture PDF has "Hello RBI KYC" text
        assert "Hello" in text or "RBI" in text or len(text) > 0

    def test_real_rbi_pdf_extracts_text(
        self, extractor: PDFExtractor, real_rbi_pdf_bytes: bytes
    ) -> None:
        text, page_count = extractor.extract_pdfplumber(real_rbi_pdf_bytes)
        assert page_count >= 1
        assert len(text) > 100  # Real PDF should have substantial text

    def test_extract_full_pipeline_good_pdf(
        self, extractor: PDFExtractor, good_pdf_bytes: bytes
    ) -> None:
        """Full extract() pipeline with a good PDF — mock the download step."""

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = good_pdf_bytes
                return await extractor.extract("https://example.com/good.pdf")

        result = asyncio.run(_run())
        assert result.extraction_method in ("pdfplumber", "ocr")
        assert result.page_count >= 1


# ---------------------------------------------------------------------------
# Case (ii): Scanned PDF → OCR fallback
# ---------------------------------------------------------------------------


class TestScannedPdfOcrFallback:
    def test_blank_pdfplumber_triggers_ocr(
        self, extractor: PDFExtractor, scanned_pdf_bytes: bytes
    ) -> None:
        """When pdfplumber returns blank text, extract() should try OCR."""

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = scanned_pdf_bytes
                # Mock pdfplumber to return blank (simulating scanned PDF)
                with patch.object(extractor, "extract_pdfplumber") as mock_plumber:
                    mock_plumber.return_value = ("", 1)
                    # Mock OCR to return something
                    with patch.object(extractor, "extract_ocr") as mock_ocr:
                        mock_ocr.return_value = ("OCR extracted text content", 1)
                        return await extractor.extract("https://example.com/scan.pdf")

        result = asyncio.run(_run())
        assert result.extraction_method == "ocr"
        assert "OCR" in result.raw_text
        assert any("blank" in w.lower() or "ocr" in w.lower() for w in result.warnings)

    def test_ocr_page_limit(self, extractor: PDFExtractor) -> None:
        """OCR should respect the max_pages limit."""
        limited_extractor = PDFExtractor(ocr_max_pages=2)

        # Create mock images
        mock_images = [MagicMock() for _ in range(5)]

        with patch("scraper.extractor.pdf_extractor.pdfplumber"):
            with patch("pdf2image.convert_from_bytes", return_value=mock_images):
                with patch("pytesseract.image_to_string", return_value="page text"):
                    text, page_count = limited_extractor.extract_ocr(b"%PDF-1.4 fake")
                    # Should have only OCR'd 2 pages despite 5 available
                    assert page_count == 5  # total count
                    assert text.count("--- Page") == 2

    def test_ocr_runtime_error_handled(
        self, extractor: PDFExtractor, scanned_pdf_bytes: bytes
    ) -> None:
        """When OCR deps are missing, graceful fallback."""

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = scanned_pdf_bytes
                # Mock pdfplumber to return blank to trigger OCR path
                with patch.object(extractor, "extract_pdfplumber") as mock_plumber:
                    mock_plumber.return_value = ("", 1)
                    with patch.object(extractor, "extract_ocr") as mock_ocr:
                        mock_ocr.side_effect = RuntimeError("pdf2image not installed")
                        return await extractor.extract("https://example.com/scan.pdf")

        result = asyncio.run(_run())
        # Should not crash — returns whatever pdfplumber gave us
        assert result.extraction_method == "pdfplumber"
        assert any("pdf2image" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Case (iii): Malformed / non-PDF → graceful skip
# ---------------------------------------------------------------------------


class TestMalformedGracefulSkip:
    def test_html_content_rejected(
        self, extractor: PDFExtractor, html_not_pdf_bytes: bytes
    ) -> None:
        """HTML content served as 'PDF' should be rejected without crashing."""

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = html_not_pdf_bytes
                return await extractor.extract("https://www.rbi.org.in/scripts/ScreenReader.aspx")

        result = asyncio.run(_run())
        assert result.raw_text == ""
        assert result.extraction_method == "failed"
        assert result.page_count == 0
        assert any("%PDF-" in w or "Not a valid PDF" in w for w in result.warnings)

    def test_empty_bytes_rejected(self, extractor: PDFExtractor) -> None:
        """Empty download should be rejected."""

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = b""
                return await extractor.extract("https://example.com/empty.pdf")

        result = asyncio.run(_run())
        assert result.raw_text == ""
        assert result.extraction_method == "failed"

    def test_download_failure_handled(self, extractor: PDFExtractor) -> None:
        """HTTP errors during download should return failed, not crash."""

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.side_effect = Exception("Connection refused")
                return await extractor.extract("https://example.com/bad.pdf")

        result = asyncio.run(_run())
        assert result.raw_text == ""
        assert result.extraction_method == "failed"

    def test_aspx_url_content_rejected(self, extractor: PDFExtractor) -> None:
        """Typical RBI .aspx page served as response — the main SCR-1 failure mode."""
        aspx_content = (
            b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
            b' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
            b"<html><head><title>RBI</title></head><body>"
            b"<h1>Screen Reader Access</h1></body></html>"
        )

        async def _run() -> ExtractedDocument:
            with patch.object(extractor, "download", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = aspx_content
                return await extractor.extract("https://www.rbi.org.in/scripts/ScreenReader.aspx")

        result = asyncio.run(_run())
        assert result.raw_text == ""
        assert result.extraction_method == "failed"
        assert result.page_count == 0
