from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os
from app.config import REPORT_FOLDER

def generate_pdf(report_text):

    os.makedirs(REPORT_FOLDER, exist_ok=True)

    pdf_path = os.path.join(REPORT_FOLDER, "AI_Service_Cloud_Report.pdf")

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    for line in report_text.split("\n"):
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 8))

    doc.build(elements)

    return pdf_path