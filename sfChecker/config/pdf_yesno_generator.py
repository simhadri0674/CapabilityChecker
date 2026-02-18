from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table
from reportlab.platypus import TableStyle

def generate_yes_no_pdf(report, output_path="feature_yes_no_report.pdf"):

    doc = SimpleDocTemplate(output_path)
    elements = []

    data = [["Feature Name", "Available"]]

    for feature in report.all_features:
        status = "YES" if feature.status == "used" else "NO"
        data.append([feature.name, status])

    table = Table(data, colWidths=[4 * inch, 1.5 * inch])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER')
    ]))

    elements.append(table)
    doc.build(elements)

    print(f"✅ PDF Generated: {output_path}")
