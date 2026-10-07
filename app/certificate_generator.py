"""
app/certificate_generator.py - PDF certificate generation using ReportLab.

Design decisions:
  - A single predefined template is rendered programmatically using ReportLab's
    canvas API. This avoids external template files and keeps the generator
    self-contained.
  - The certificate uses an A4-landscape layout with a two-band header/footer,
    decorative border, and a colour palette inspired by premium academic certificates.
  - The seal is rendered as a pure background watermark (drawn before all text)
    so it never collides with any content.
  - Font sizes auto-shrink for long recipient/course names to prevent overflow.
  - Each certificate is saved as a unique PDF file named by the certificate
    record UUID to avoid collisions during concurrent generation.
  - Raises CertificateGenerationError on any failure so the caller can catch
    and record the error without crashing other generations.
"""
import os
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


class CertificateGenerationError(Exception):
    """Raised when a certificate cannot be generated for a recipient."""
    pass


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
NAVY       = colors.HexColor("#1A2E4A")
GOLD       = colors.HexColor("#C9A84C")
LIGHT_GOLD = colors.HexColor("#F5E6C0")
CREAM      = colors.HexColor("#FDFAF3")
WHITE      = colors.white
DARK_GRAY  = colors.HexColor("#2D2D2D")
MID_GRAY   = colors.HexColor("#5A5A5A")


def generate_certificate(
    *,
    record_id: str,
    recipient_name: str,
    recipient_email: str,
    course_name: str,
    event_name: str,
    issuer_name: str,
    issue_date: str,
    output_dir: Path,
) -> str:
    """
    Generate a PDF certificate for one recipient and save it to *output_dir*.

    Parameters
    ----------
    record_id       : UUID string used as the filename (prevents collisions).
    recipient_name  : Full name printed on the certificate.
    recipient_email : Email of the recipient (printed in small text at bottom).
    course_name     : Course / achievement being certified.
    event_name      : Name of the event / programme.
    issuer_name     : Name of the issuing organisation.
    issue_date      : ISO date string (YYYY-MM-DD) shown on the certificate.
    output_dir      : Directory where the PDF should be saved.

    Returns
    -------
    str : Absolute path of the generated PDF file.

    Raises
    ------
    CertificateGenerationError : If PDF creation fails for any reason.
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{record_id}.pdf"

        page_width, page_height = landscape(A4)

        c = canvas.Canvas(str(file_path), pagesize=landscape(A4))
        _draw_certificate(
            c,
            page_width=page_width,
            page_height=page_height,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            course_name=course_name,
            event_name=event_name,
            issuer_name=issuer_name,
            issue_date=issue_date,
        )
        c.save()
        return str(file_path.resolve())

    except Exception as exc:
        raise CertificateGenerationError(
            f"Failed to generate certificate for '{recipient_name}': {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Internal drawing helpers
# ---------------------------------------------------------------------------

def _draw_certificate(
    c: canvas.Canvas,
    *,
    page_width: float,
    page_height: float,
    recipient_name: str,
    recipient_email: str,
    course_name: str,
    event_name: str,
    issuer_name: str,
    issue_date: str,
) -> None:
    """Draw all elements of the certificate onto the canvas."""

    # Band heights
    HEADER_H = 22 * mm
    FOOTER_H = 22 * mm
    GOLD_STRIP = 2.5 * mm   # thin gold strip between band and content area

    # ── 1. Cream background ──────────────────────────────────────────────────
    c.setFillColor(CREAM)
    c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

    # ── 2. Top navy header band ──────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.rect(0, page_height - HEADER_H, page_width, HEADER_H, fill=True, stroke=False)
    # Gold accent strip immediately below header band
    c.setFillColor(GOLD)
    c.rect(0, page_height - HEADER_H - GOLD_STRIP, page_width, GOLD_STRIP, fill=True, stroke=False)

    # ── 3. Bottom navy footer band ────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.rect(0, 0, page_width, FOOTER_H, fill=True, stroke=False)
    # Gold accent strip immediately above footer band
    c.setFillColor(GOLD)
    c.rect(0, FOOTER_H, page_width, GOLD_STRIP, fill=True, stroke=False)

    # ── 4. Background watermark seal (drawn BEFORE text, very faint) ─────────
    #    Centred in the cream content zone — no overlap with any bands
    _draw_watermark_seal(c, page_width, page_height, HEADER_H, FOOTER_H, GOLD_STRIP)

    # ── 5. Decorative border (inside content area only) ───────────────────────
    _draw_decorative_border(c, page_width, page_height, HEADER_H, FOOTER_H, GOLD_STRIP)

    # ── 6. Issuer name in header band (GOLD on NAVY — high contrast) ──────────
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2, page_height - HEADER_H + 7 * mm, issuer_name.upper())

    # ── 7. Certificate title — positioned just below gold strip ───────────────
    title_y = page_height - HEADER_H - GOLD_STRIP - 14 * mm
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(page_width / 2, title_y, "CERTIFICATE")

    subtitle_y = title_y - 9 * mm
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_width / 2, subtitle_y, "O F   A C H I E V E M E N T")

    # Gold rule under subtitle
    rule_y = subtitle_y - 5 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(page_width / 2 - 55 * mm, rule_y, page_width / 2 + 55 * mm, rule_y)

    # ── 8. "This is to certify that" ─────────────────────────────────────────
    certify_y = rule_y - 12 * mm
    c.setFillColor(MID_GRAY)
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(page_width / 2, certify_y, "This is to certify that")

    # ── 9. Recipient name (auto-shrink for long names) ────────────────────────
    name_y = certify_y - 14 * mm
    c.setFillColor(NAVY)
    name_font_size = 34
    max_name_width = page_width - 80 * mm
    while c.stringWidth(recipient_name, "Helvetica-Bold", name_font_size) > max_name_width:
        name_font_size -= 2
    c.setFont("Helvetica-Bold", name_font_size)
    c.drawCentredString(page_width / 2, name_y, recipient_name)

    # Gold underline directly below the name
    name_w = c.stringWidth(recipient_name, "Helvetica-Bold", name_font_size)
    underline_y = name_y - 3 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.2)
    c.line(
        page_width / 2 - name_w / 2, underline_y,
        page_width / 2 + name_w / 2, underline_y,
    )

    # ── 10. "has successfully completed" ──────────────────────────────────────
    completed_y = underline_y - 10 * mm
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", 11)
    c.drawCentredString(page_width / 2, completed_y, "has successfully completed")

    # ── 11. Course name (auto-shrink) ─────────────────────────────────────────
    course_y = completed_y - 10 * mm
    c.setFillColor(NAVY)
    course_font_size = 20
    max_course_width = page_width - 80 * mm
    while c.stringWidth(course_name, "Helvetica-Bold", course_font_size) > max_course_width:
        course_font_size -= 1
    c.setFont("Helvetica-Bold", course_font_size)
    c.drawCentredString(page_width / 2, course_y, course_name)

    # ── 12. Event / programme name (auto-shrink) ──────────────────────────────
    event_y = course_y - 8 * mm
    c.setFillColor(MID_GRAY)
    event_text = f'as part of  "{event_name}"'
    event_font_size = 11
    max_event_width = page_width - 80 * mm
    while c.stringWidth(event_text, "Helvetica-Oblique", event_font_size) > max_event_width:
        event_font_size -= 1
    c.setFont("Helvetica-Oblique", event_font_size)
    c.drawCentredString(page_width / 2, event_y, event_text)

    # ── 13. Footer (inside NAVY band — all text WHITE or LIGHT_GOLD) ──────────
    footer_mid_y = FOOTER_H / 2   # vertical midpoint of the band

    # Left: Date of Issue
    c.setFillColor(LIGHT_GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(28 * mm, footer_mid_y + 4 * mm, "DATE OF ISSUE")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 10)
    c.drawString(28 * mm, footer_mid_y - 4 * mm, issue_date)

    # Right: Recipient email
    c.setFillColor(LIGHT_GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(page_width - 28 * mm, footer_mid_y + 4 * mm, "RECIPIENT EMAIL")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 10)
    c.drawRightString(page_width - 28 * mm, footer_mid_y - 4 * mm, recipient_email)

    # Centre: Signature line + issuer label
    sig_x = page_width / 2
    sig_line_y = FOOTER_H - 5 * mm   # near the top of the footer band
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.line(sig_x - 38 * mm, sig_line_y, sig_x + 38 * mm, sig_line_y)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-BoldOblique", 10)
    c.drawCentredString(sig_x, footer_mid_y + 1 * mm, issuer_name)

    c.setFillColor(LIGHT_GOLD)
    c.setFont("Helvetica", 8)
    c.drawCentredString(sig_x, footer_mid_y - 5 * mm, "Authorised Signatory")


def _draw_watermark_seal(
    c: canvas.Canvas,
    w: float,
    h: float,
    header_h: float,
    footer_h: float,
    gold_strip: float,
) -> None:
    """
    Draw a very faint decorative seal as a background watermark.

    Placed in the exact vertical centre of the content area (between the two
    gold strips) so it never overlaps the header or footer bands.  Its fill
    colours are very light so body text remains fully readable over it.
    """
    content_top = h - header_h - gold_strip
    content_bot = footer_h + gold_strip
    cy = content_bot + (content_top - content_bot) / 2 - 4 * mm
    cx = w / 2
    radius = 30 * mm

    # Outer faint champagne circle
    c.setFillColor(colors.HexColor("#EDE0C0"))
    c.setStrokeColor(colors.HexColor("#D4B87A"))
    c.setLineWidth(0.4)
    c.circle(cx, cy, radius, fill=True, stroke=True)

    # Inner slightly deeper ring
    c.setFillColor(colors.HexColor("#E2CFA0"))
    c.setStrokeColor(colors.HexColor("#C9A84C"))
    c.setLineWidth(0.4)
    c.circle(cx, cy, radius * 0.70, fill=True, stroke=True)

    # Star glyph
    c.setFillColor(colors.HexColor("#2A4060"))
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(cx, cy - 8, "\u2605")

    # "CERTIFIED" label
    c.setFillColor(colors.HexColor("#2A4060"))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, cy + 15, "CERTIFIED")


def _draw_decorative_border(
    c: canvas.Canvas,
    w: float,
    h: float,
    header_h: float,
    footer_h: float,
    gold_strip: float,
) -> None:
    """
    Draw a gold outer + navy inner border that lives strictly inside the
    content area (between the gold accent strips), not overlapping the bands.
    """
    margin = 9 * mm
    inner  = 12 * mm

    content_top = h - header_h - gold_strip
    content_bot = footer_h + gold_strip
    content_h = content_top - content_bot

    # Outer gold rectangle
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.5)
    c.rect(
        margin, content_bot + margin,
        w - 2 * margin, content_h - 2 * margin,
        fill=False, stroke=True,
    )

    # Inner navy rectangle
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.rect(
        inner, content_bot + inner,
        w - 2 * inner, content_h - 2 * inner,
        fill=False, stroke=True,
    )
