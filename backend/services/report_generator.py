import io
import logging
from typing import Any, Dict
from xhtml2pdf import pisa
from backend.services.report_generator import generate_html_reports

logger = logging.getLogger('ats_resume_scorer')

def generate_pdf_from_analysis(data: Dict[str, Any]) -> bytes:
    """Renders HTML sections and stitches them into a single PDF document."""
    # 1. Render all 4 sections from your Jinja2 templates
    sections = generate_html_reports(data)

    # 2. Combine into one document with page breaks
    combined_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        @page {{
          size: a4 portrait;
          margin: 1.5cm;
        }}
        .page-break {{
          page-break-before: always;
        }}
      </style>
    </head>
    <body>
      <div class="section-summary">{sections.get('summary', '')}</div>
      <div class="page-break"></div>
      <div class="section-jd">{sections.get('jd_comparison', '')}</div>
      <div class="page-break"></div>
      <div class="section-actions">{sections.get('action_items', '')}</div>
      <div class="page-break"></div>
      <div class="section-quick">{sections.get('quick_actions', '')}</div>
    </body>
    </html>
    """

    # 3. Convert HTML to PDF bytes
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(src=combined_html, dest=pdf_buffer)

    if pisa_status.err:
        logger.error(f"xhtml2pdf error status: {pisa_status.err}")
        raise RuntimeError("Failed to generate PDF from report sections.")

    return pdf_buffer.getvalue()