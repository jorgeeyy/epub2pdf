from xhtml2pdf import pisa
from io import BytesIO

def render_pdf(html, output):
    """Convert HTML string to PDF file using xhtml2pdf"""
    with open(output, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(
            html,
            dest=pdf_file
        )
    
    if pisa_status.err:
        raise Exception(f"PDF generation failed with {pisa_status.err} errors")
