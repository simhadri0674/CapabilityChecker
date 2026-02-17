from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from app.salesforce_service import connect_salesforce, collect_org_metrics
from app.groq_service import analyze_with_groq
from app.report_service import extract_sections, build_excel_format, save_reports
from app.pdf_service import generate_pdf
from app.config import CAPABILITY_FILE, REPORT_FOLDER

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-report")
def generate_report():

    sf = connect_salesforce()
    metrics = collect_org_metrics(sf)

    with open(CAPABILITY_FILE, "r", encoding="utf-8") as f:
        capabilities_text = f.read()

    llm_output = analyze_with_groq(capabilities_text, metrics)

    parsed_json, report_markdown = extract_sections(llm_output)

    df = build_excel_format(parsed_json)
    save_reports(df, report_markdown)
    generate_pdf(report_markdown)

    return {"status": "Report Generated Successfully"}

@app.get("/download/{file_type}")
def download(file_type: str):

    files = {
        "excel": "AI_Service_Cloud_Capability_Report.xlsx",
        "md": "AI_Service_Cloud_Report.md",
        "pdf": "AI_Service_Cloud_Report.pdf"
    }

    file_path = os.path.join(REPORT_FOLDER, files.get(file_type))
    return FileResponse(file_path, filename=files.get(file_type))