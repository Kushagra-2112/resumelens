"""
Combines the four rendered HTML report sections into a single downloadable
PDF using WeasyPrint. Section keys must match exactly what
report_generator.generate_html_reports() returns:
'summary', 'skill_report', 'jd_report', 'recommendations'.
"""

import logging
from typing import Dict

from weasyprint import HTML

logger = logging.getLogger('ats_resume_scorer')

# Order matters — this is the order sections appear in the final PDF.
# Keys must match report_generator.generate_html_reports()'s return dict.
_SECTION_ORDER = ['summary', 'skill_report', 'jd_report', 'recommendations']


def _extract_body(html_doc: str) -> str:
    """Pull just the <body>...</body> content out of a full HTML document,
    so multiple documents can be concatenated without nested <html>/<head>
    tags confusing the renderer."""
    start = html_doc.find('<body>')
    end = html_doc.find('</body>')
    if start == -1 or end == -1:
        return html_doc
    return html_doc[start + len('<body>'):end]


def generate_combined_pdf(html_docs: Dict[str, str]) -> bytes:
    """Combine the rendered section HTML strings into one PDF and return
    the raw PDF bytes."""

    body_sections = []
    for i, section_name in enumerate(_SECTION_ORDER):
        html_doc = html_docs.get(section_name)
        if not html_doc:
            logger.warning(f"PDF section '{section_name}' was missing or empty — skipped")
            continue
        body = _extract_body(html_doc)
        page_break = 'page-break-before: always;' if i > 0 else ''
        body_sections.append(f'<div style="{page_break}">{body}</div>')

    combined_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        @page {{ size: A4; margin: 1.5cm; }}
        body {{ font-family: 'DejaVu Sans', Arial, sans-serif; margin: 0; }}
      </style>
    </head>
    <body>
      {''.join(body_sections)}
    </body>
    </html>
    """

    try:
        pdf_bytes = HTML(string=combined_html).write_pdf()
        logger.info(f"Generated combined PDF ({len(pdf_bytes)} bytes) from {len(body_sections)} sections")
        return pdf_bytes
    except Exception as exc:
        logger.error(f"PDF generation failed: {exc}")
        raise