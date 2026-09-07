"""Open Graph image renderer for public snippet pages.

Generates a 1200x630 PNG with the RegPulse brand and a snippet preview.
Uses Pillow's default font (always available in any environment) so this
never fails on missing-font errors. The result is small (~30 KB) and
trivially cacheable behind a 24h response header.
"""

from __future__ import annotations

import io
import textwrap

from PIL import Image, ImageDraw, ImageFont

# Brand palette (matches frontend landing page)
BG_COLOR = (10, 25, 49)  # navy
ACCENT = (96, 165, 250)  # light blue
TEXT_COLOR = (240, 245, 255)
MUTED = (160, 180, 210)

WIDTH = 1200
HEIGHT = 630
PADDING = 80


def _load_font(size: int) -> ImageFont.ImageFont:
    """Best-effort font loader. Falls back to default bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_snippet_og(
    *,
    snippet_text: str,
    citation_label: str | None = None,
    consult_expert: bool = False,
) -> bytes:
    """Render a snippet preview as a 1200x630 PNG and return raw bytes."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Accent bar at the top
    draw.rectangle((0, 0, WIDTH, 8), fill=ACCENT)

    # Brand row
    brand_font = _load_font(48)
    draw.text((PADDING, PADDING), "RegPulse", font=brand_font, fill=ACCENT)

    tagline_font = _load_font(22)
    draw.text(
        (PADDING, PADDING + 60),
        "RBI Regulatory Intelligence — Anti-Hallucination Compliance Answers",
        font=tagline_font,
        fill=MUTED,
    )

    # Snippet body
    body_font = _load_font(34)
    wrapped = textwrap.wrap(snippet_text, width=52)[:6]  # Cap at 6 lines
    body_y = PADDING + 130
    for line in wrapped:
        draw.text((PADDING, body_y), line, font=body_font, fill=TEXT_COLOR)
        body_y += 48

    # Footer: citation or consult-expert badge
    footer_font = _load_font(24)
    if consult_expert:
        draw.text(
            (PADDING, HEIGHT - PADDING - 30),
            "⚠  Consult an Expert",
            font=footer_font,
            fill=ACCENT,
        )
    elif citation_label:
        draw.text(
            (PADDING, HEIGHT - PADDING - 30),
            f"Source: {citation_label}",
            font=footer_font,
            fill=MUTED,
        )

    # CTA
    cta_font = _load_font(20)
    draw.text(
        (WIDTH - PADDING - 280, HEIGHT - PADDING - 30),
        "Register for the full answer →",
        font=cta_font,
        fill=ACCENT,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
