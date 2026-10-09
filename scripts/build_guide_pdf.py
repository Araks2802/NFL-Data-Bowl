"""Render docs/guide_content.py into a polished, beginner-friendly PDF.

Output: docs/Pocket_Integrity_Score_Beginners_Guide.pdf

Pure-Python (fpdf2), no system dependencies. Handles headings, paragraphs
with **bold** inline, bullet lists, callout boxes, and auto-wrapping tables
with repeating headers.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs"))

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from guide_content import CONTENT  # loaded from docs/ (added to path above)

OUT = Path(__file__).resolve().parents[1] / "docs" / \
    "Pocket_Integrity_Score_Beginners_Guide.pdf"

# palette (matches the app)
NAVY = (11, 18, 32)
NAVY_SOFT = (17, 26, 43)
GOLD = (244, 211, 94)
GREEN = (46, 204, 113)
RED = (239, 111, 108)
INK = (33, 37, 41)
GREY = (90, 100, 118)
LIGHT = (235, 238, 243)
NOTE_BG = (235, 243, 255)
NOTE_BORDER = (93, 173, 226)
TABLE_HEAD = (24, 38, 62)
TABLE_ALT = (244, 246, 250)

PAGE_W = 210
MARGIN = 18
CONTENT_W = PAGE_W - 2 * MARGIN


class Guide(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_y(8)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 5, "Pocket Integrity Score - Beginner's Guide",
                  align="L")
        self.cell(0, 5, "", align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*LIGHT)
        self.line(MARGIN, 15, PAGE_W - MARGIN, 15)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, f"Page {self.page_no() - 1}", align="C")


def _bold_segments(text: str):
    """Split a string on **bold** markers into (text, is_bold) pairs."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    out = []
    for p in parts:
        if not p:
            continue
        if p.startswith("**") and p.endswith("**"):
            out.append((p[2:-2], True))
        else:
            out.append((p, False))
    return out


def write_rich(pdf: FPDF, text: str, size=10.5, lh=5.6, color=INK):
    """Write a paragraph honoring **bold** inline segments with wrapping."""
    pdf.set_text_color(*color)
    for seg, is_bold in _bold_segments(text):
        pdf.set_font("Helvetica", "B" if is_bold else "", size)
        pdf.write(lh, seg)
    pdf.ln(lh + 1.5)


def ascii_clean(s: str) -> str:
    """Keep the core font (Helvetica) happy: replace non-latin1 glyphs."""
    repl = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
            "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00b1": "+/-",
            "\u2192": "->", "\u2190": "<-"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def cover(pdf: FPDF, payload: dict):
    pdf.add_page()
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, PAGE_W, 297, "F")
    pdf.set_y(66)
    pdf.set_text_color(*GOLD)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "NFL PASS-PROTECTION ANALYTICS", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 34)
    pdf.multi_cell(0, 15, ascii_clean(payload["title"]), align="C")
    pdf.ln(4)
    pdf.set_text_color(*LIGHT)
    pdf.set_font("Helvetica", "", 18)
    pdf.cell(0, 10, ascii_clean(payload["subtitle"]), align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    # gold divider band, placed BELOW the subtitle
    pdf.ln(8)
    band_y = pdf.get_y()
    pdf.set_fill_color(*GOLD)
    pdf.rect(MARGIN + 25, band_y, CONTENT_W - 50, 1.4, "F")
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*LIGHT)
    pdf.set_x(MARGIN + 10)
    pdf.multi_cell(CONTENT_W - 20, 7, ascii_clean(payload["tagline"]),
                   align="C")
    pdf.set_y(250)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, "Data: NFL Big Data Bowl 2023 (2021 season, weeks 1-8)",
             align="C")


def heading(pdf: FPDF, text: str, level: int):
    if level == 1:
        pdf.add_page()
        pdf.set_y(22)
        pdf.set_fill_color(*GOLD)
        pdf.rect(MARGIN, pdf.get_y(), 4, 9, "F")
        pdf.set_x(MARGIN + 7)
        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(CONTENT_W - 7, 9, ascii_clean(text))
        pdf.ln(3)
    elif level == 2:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*TABLE_HEAD)
        pdf.multi_cell(CONTENT_W, 7, ascii_clean(text))
        pdf.ln(1)
    else:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*GREY)
        pdf.multi_cell(CONTENT_W, 6, ascii_clean(text))
        pdf.ln(0.5)


def bullets(pdf: FPDF, items: list[str]):
    for it in items:
        y0 = pdf.get_y()
        # neat round bullet marker
        pdf.set_fill_color(*NOTE_BORDER)
        pdf.ellipse(MARGIN + 2.0, y0 + 2.1, 1.8, 1.8, "F")
        pdf.set_xy(MARGIN + 7, y0)
        pdf.set_text_color(*INK)
        # rich text for the bullet body
        for seg, is_bold in _bold_segments(ascii_clean(it)):
            pdf.set_font("Helvetica", "B" if is_bold else "", 10.5)
            pdf.write(5.6, seg)
        pdf.ln(6.2)
    pdf.ln(1.5)


def note(pdf: FPDF, text: str):
    text = ascii_clean(text)
    pdf.ln(1)
    x0, y0 = MARGIN, pdf.get_y()
    # measure height by rendering into a temp multi_cell with dry run
    pdf.set_font("Helvetica", "I", 10.5)
    # estimate: use split_only
    lines = pdf.multi_cell(CONTENT_W - 12, 5.8, text, dry_run=True,
                           output="LINES")
    h = len(lines) * 5.8 + 7
    if y0 + h > 275:
        pdf.add_page()
        y0 = pdf.get_y()
    pdf.set_fill_color(*NOTE_BG)
    pdf.set_draw_color(*NOTE_BORDER)
    pdf.rect(x0, y0, CONTENT_W, h, "F")
    pdf.set_fill_color(*NOTE_BORDER)
    pdf.rect(x0, y0, 2.5, h, "F")
    pdf.set_xy(x0 + 7, y0 + 3.5)
    pdf.set_text_color(*TABLE_HEAD)
    pdf.set_font("Helvetica", "I", 10.5)
    pdf.multi_cell(CONTENT_W - 12, 5.8, text)
    pdf.set_y(y0 + h + 3)


def table(pdf: FPDF, headers: list[str], rows: list[list[str]]):
    n = len(headers)
    # column widths: first column a bit wider for term/label tables
    if n == 2:
        widths = [CONTENT_W * 0.34, CONTENT_W * 0.66]
    elif n == 3:
        widths = [CONTENT_W * 0.20, CONTENT_W * 0.26, CONTENT_W * 0.54]
    else:
        widths = [CONTENT_W / n] * n
    line_h = 5.3
    pad = 1.6

    def row_height(cells):
        hmax = line_h + 2 * pad
        pdf.set_font("Helvetica", "", 9.5)
        for i, c in enumerate(cells):
            lines = pdf.multi_cell(widths[i] - 2 * pad, line_h,
                                   ascii_clean(str(c)), dry_run=True,
                                   output="LINES")
            hmax = max(hmax, len(lines) * line_h + 2 * pad)
        return hmax

    def draw_header():
        pdf.set_fill_color(*TABLE_HEAD)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9.5)
        h = row_height(headers)
        x = MARGIN
        y = pdf.get_y()
        for i, head in enumerate(headers):
            pdf.rect(x, y, widths[i], h, "F")
            pdf.set_xy(x + pad, y + pad)
            pdf.multi_cell(widths[i] - 2 * pad, line_h, ascii_clean(head))
            x += widths[i]
        pdf.set_y(y + h)

    pdf.ln(1)
    if pdf.get_y() > 250:
        pdf.add_page()
    draw_header()
    for r, cells in enumerate(rows):
        h = row_height(cells)
        if pdf.get_y() + h > 282:
            pdf.add_page()
            draw_header()
        y = pdf.get_y()
        x = MARGIN
        fill = TABLE_ALT if r % 2 == 0 else (255, 255, 255)
        for i, c in enumerate(cells):
            pdf.set_fill_color(*fill)
            pdf.set_draw_color(*LIGHT)
            pdf.rect(x, y, widths[i], h, "DF")
            pdf.set_xy(x + pad, y + pad)
            pdf.set_text_color(*INK)
            # bold the first column (labels)
            is_label = (i == 0)
            pdf.set_font("Helvetica", "B" if is_label else "", 9.5)
            pdf.multi_cell(widths[i] - 2 * pad, line_h, ascii_clean(str(c)))
            x += widths[i]
        pdf.set_y(y + h)
    pdf.ln(3)


def build():
    pdf = Guide(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(MARGIN, 20, MARGIN)

    for kind, payload in CONTENT:
        if kind == "cover":
            cover(pdf, payload)
        elif kind == "h1":
            heading(pdf, payload, 1)
        elif kind == "h2":
            heading(pdf, payload, 2)
        elif kind == "h3":
            heading(pdf, payload, 3)
        elif kind == "p":
            write_rich(pdf, ascii_clean(payload))
        elif kind == "bullet":
            bullets(pdf, payload)
        elif kind == "note":
            note(pdf, payload)
        elif kind == "table":
            headers, rows = payload
            table(pdf, headers, rows)
        elif kind == "spacer":
            pdf.ln(payload)

    pdf.output(str(OUT))
    print(f"Wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB, {pdf.page_no()} pages)")
    print("SCRIPT_OK")


if __name__ == "__main__":
    build()
