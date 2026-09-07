"""PDF export service — compliance brief as PDF or text.

Two entry points:

- ``generate_brief`` — legacy, returns a formatted text string.
- ``generate_pdf_brief`` — Sprint 8 (G-09). Returns real PDF bytes using
  reportlab; each citation is accompanied by a QR code pointing to the
  circular's ``rbi_url`` so auditors can scan back to the source.

reportlab + qrcode are pulled in via ``requirements.txt``. The text variant
remains available for callers that still want plain text.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger("regpulse.pdf_export")


class PDFExportService:
    """Generate compliance brief exports from Q&A data."""

    @staticmethod
    def generate_brief(
        *,
        question_text: str,
        answer_text: str | None,
        quick_answer: str | None,
        risk_level: str | None,
        affected_teams: list[str] | None,
        citations: list[dict] | None,
        recommended_actions: list[dict] | None,
        created_at: str | None,
    ) -> str:
        """Generate a structured compliance brief as formatted text.

        Returns a string that can be rendered as a downloadable document.
        """
        now = datetime.now(UTC).strftime("%d %B %Y, %H:%M UTC")
        lines = [
            "=" * 72,
            "REGPULSE COMPLIANCE BRIEF",
            "=" * 72,
            f"Generated: {now}",
            "",
            "-" * 72,
            "QUESTION",
            "-" * 72,
            question_text,
            "",
        ]

        if quick_answer:
            lines += [
                "-" * 72,
                "EXECUTIVE SUMMARY",
                "-" * 72,
                quick_answer,
                "",
            ]

        if risk_level:
            lines.append(f"Risk Level: {risk_level}")
            lines.append("")

        if affected_teams:
            lines.append(f"Affected Teams: {', '.join(affected_teams)}")
            lines.append("")

        if answer_text:
            lines += [
                "-" * 72,
                "DETAILED INTERPRETATION",
                "-" * 72,
                answer_text,
                "",
            ]

        if citations:
            lines += ["-" * 72, "CITATIONS", "-" * 72]
            for i, c in enumerate(citations, 1):
                cn = c.get("circular_number", "Unknown")
                quote = c.get("verbatim_quote", "")
                ref = c.get("section_reference", "")
                lines.append(f"  [{i}] {cn}")
                if ref:
                    lines.append(f"      Section: {ref}")
                if quote:
                    lines.append(f'      "{quote}"')
                lines.append("")

        if recommended_actions:
            lines += ["-" * 72, "RECOMMENDED ACTIONS", "-" * 72]
            for i, a in enumerate(recommended_actions, 1):
                team = a.get("team", "")
                action = a.get("action_text", "")
                priority = a.get("priority", "")
                lines.append(f"  {i}. [{priority}] {team}: {action}")
            lines.append("")

        lines += [
            "=" * 72,
            "DISCLAIMER",
            "RegPulse is not a legal advisory service. This brief is",
            "AI-generated from indexed RBI circulars and should be verified",
            "against official sources at rbi.org.in before making compliance",
            "decisions.",
            "=" * 72,
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Sprint 8 (G-09): real PDF with citation QR codes
    # ------------------------------------------------------------------

    @staticmethod
    def generate_pdf_brief(
        *,
        question_text: str,
        answer_text: str | None,
        quick_answer: str | None,
        risk_level: str | None,
        affected_teams: list[str] | None,
        citations: list[dict] | None,
        recommended_actions: list[dict] | None,
        created_at: str | None = None,
    ) -> bytes:
        """Generate a PDF compliance brief with QR codes per citation.

        Each citation block renders:
            [n] <circular_number> — <section_reference>
                "<verbatim_quote>"
                <rbi_url>
                <QR code pointing to rbi_url>

        Citations without an ``rbi_url`` skip the QR code.
        """
        import qrcode
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Image,
            KeepTogether,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title="RegPulse Compliance Brief",
        )

        styles = getSampleStyleSheet()
        h1 = styles["Heading1"]
        h2 = styles["Heading2"]
        body = styles["BodyText"]
        small = ParagraphStyle(
            "small",
            parent=body,
            fontSize=8,
            textColor=colors.grey,
        )
        quote_style = ParagraphStyle(
            "quote",
            parent=body,
            fontSize=9,
            leftIndent=12,
            textColor=colors.HexColor("#444444"),
            italic=True,
        )

        story: list = []
        now = datetime.now(UTC).strftime("%d %B %Y, %H:%M UTC")

        story.append(Paragraph("RegPulse Compliance Brief", h1))
        story.append(Paragraph(f"Generated: {now}", small))
        story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph("Question", h2))
        story.append(Paragraph(_escape(question_text), body))
        story.append(Spacer(1, 0.1 * inch))

        if quick_answer:
            story.append(Paragraph("Executive Summary", h2))
            story.append(Paragraph(_escape(quick_answer), body))
            story.append(Spacer(1, 0.1 * inch))

        meta_bits: list[str] = []
        if risk_level:
            meta_bits.append(f"<b>Risk:</b> {_escape(risk_level)}")
        if affected_teams:
            meta_bits.append("<b>Affected Teams:</b> " + _escape(", ".join(affected_teams)))
        if meta_bits:
            story.append(Paragraph(" &nbsp; • &nbsp; ".join(meta_bits), body))
            story.append(Spacer(1, 0.1 * inch))

        if answer_text:
            story.append(Paragraph("Detailed Interpretation", h2))
            for para in answer_text.split("\n\n"):
                clean = para.strip()
                if clean:
                    story.append(Paragraph(_escape(clean), body))
                    story.append(Spacer(1, 0.05 * inch))

        if citations:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("Citations", h2))
            for i, c in enumerate(citations, 1):
                cn = c.get("circular_number", "Unknown")
                quote = c.get("verbatim_quote", "")
                ref = c.get("section_reference", "")
                url = c.get("rbi_url")

                header = f"[{i}] <b>{_escape(cn)}</b>"
                if ref:
                    header += f" — {_escape(ref)}"
                text_cells: list = [Paragraph(header, body)]
                if quote:
                    text_cells.append(Paragraph(f"&ldquo;{_escape(quote)}&rdquo;", quote_style))
                if url:
                    text_cells.append(Paragraph(_escape(url), small))

                if url:
                    qr_img = qrcode.make(url)
                    qr_buf = io.BytesIO()
                    qr_img.save(qr_buf, format="PNG")
                    qr_buf.seek(0)
                    qr_flowable = Image(qr_buf, width=0.75 * inch, height=0.75 * inch)
                    row = [text_cells, qr_flowable]
                    col_widths = [5.5 * inch, 0.9 * inch]
                else:
                    row = [text_cells, ""]
                    col_widths = [5.5 * inch, 0.9 * inch]

                table = Table([row], colWidths=col_widths, hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ]
                    )
                )
                story.append(KeepTogether([table]))

        if recommended_actions:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("Recommended Actions", h2))
            for i, a in enumerate(recommended_actions, 1):
                team = a.get("team", "")
                action = a.get("action_text", "")
                priority = a.get("priority", "")
                line = f"{i}. <b>[{_escape(priority)}]</b> {_escape(team)}: {_escape(action)}"
                story.append(Paragraph(line, body))

        story.append(Spacer(1, 0.25 * inch))
        story.append(
            Paragraph(
                "<b>Disclaimer:</b> RegPulse is not a legal advisory service. "
                "This brief is AI-generated from indexed RBI circulars and "
                "should be verified against official sources at rbi.org.in "
                "before making compliance decisions.",
                small,
            )
        )

        doc.build(story)
        return buf.getvalue()


def _escape(text: str | None) -> str:
    """Escape the small subset of special characters reportlab's Paragraph
    parser treats as markup (``&``, ``<``, ``>``)."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
