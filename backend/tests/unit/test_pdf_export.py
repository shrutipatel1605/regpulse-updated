"""Unit tests for Sprint 8 PDF export with QR codes (G-09)."""

from __future__ import annotations

from app.services.pdf_export_service import PDFExportService


def _sample_citations() -> list[dict]:
    return [
        {
            "circular_number": "RBI/2024-25/12",
            "section_reference": "Para 3.2",
            "verbatim_quote": "Regulated entities shall maintain a minimum CRAR of 9%.",
            "rbi_url": "https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12345",
        },
        {
            "circular_number": "RBI/2024-25/13",
            "section_reference": None,
            "verbatim_quote": "No QR expected for this one.",
            # No rbi_url on purpose — should still render, without a QR.
        },
    ]


def test_generate_pdf_brief_returns_valid_pdf_bytes():
    pdf_bytes = PDFExportService.generate_pdf_brief(
        question_text="What is the minimum CRAR for banks?",
        answer_text="Banks must maintain a minimum CRAR of 9%.",
        quick_answer="Minimum CRAR is 9%.",
        risk_level="HIGH",
        affected_teams=["Risk", "Compliance"],
        citations=_sample_citations(),
        recommended_actions=[
            {"team": "Risk", "action_text": "Review capital adequacy", "priority": "HIGH"},
        ],
    )

    # Must be a real PDF
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-"), "Output is not a PDF document"
    # Minimum reasonable size for a one-page PDF with an embedded PNG QR
    assert len(pdf_bytes) > 1500


def test_generate_pdf_brief_handles_missing_optional_fields():
    """Empty/None fields should not crash the generator."""
    pdf_bytes = PDFExportService.generate_pdf_brief(
        question_text="Q?",
        answer_text=None,
        quick_answer=None,
        risk_level=None,
        affected_teams=None,
        citations=None,
        recommended_actions=None,
    )
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_brief_embeds_qr_when_url_present():
    """Assert a PNG is embedded in the PDF stream when a citation has rbi_url."""
    citations_with_url = _sample_citations()
    citations_without_url = [{**c, "rbi_url": None} for c in citations_with_url]

    pdf_with = PDFExportService.generate_pdf_brief(
        question_text="Q?",
        answer_text=None,
        quick_answer=None,
        risk_level=None,
        affected_teams=None,
        citations=citations_with_url,
        recommended_actions=None,
    )
    pdf_without = PDFExportService.generate_pdf_brief(
        question_text="Q?",
        answer_text=None,
        quick_answer=None,
        risk_level=None,
        affected_teams=None,
        citations=citations_without_url,
        recommended_actions=None,
    )

    # reportlab streams each embedded image as an XObject with /Subtype /Image.
    # A PDF with QR codes should contain at least one such marker; one without
    # URLs should contain none (or strictly fewer).
    assert pdf_with.count(b"/Subtype /Image") >= 1
    assert pdf_with.count(b"/Subtype /Image") > pdf_without.count(b"/Subtype /Image")


def test_generate_brief_text_still_works():
    """Legacy text generator remains available for backward compatibility."""
    text = PDFExportService.generate_brief(
        question_text="What is CRAR?",
        answer_text="9%",
        quick_answer="9%",
        risk_level="HIGH",
        affected_teams=["Risk"],
        citations=_sample_citations(),
        recommended_actions=None,
        created_at=None,
    )
    assert "REGPULSE COMPLIANCE BRIEF" in text
    assert "RBI/2024-25/12" in text


def test_escape_handles_reportlab_markup_chars():
    from app.services.pdf_export_service import _escape

    assert _escape("a < b & c > d") == "a &lt; b &amp; c &gt; d"
    assert _escape(None) == ""
