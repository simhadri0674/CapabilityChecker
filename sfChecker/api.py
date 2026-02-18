from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import os

from main import (
    read_txt_file,
    evaluate_capability,
    generate_excel,
    analyze_with_llm
)
from salesforce import SalesforceConnector

app = FastAPI(title="Salesforce Capability Scanner API")


class ScanResponse(BaseModel):
    message: str
    excel_path: str
    llm_output: str


@app.get("/run-scan", response_model=ScanResponse)
def run_scan():

    output_path = "output/AI_Service_Cloud_Capability_Report.xlsx"

    sf = SalesforceConnector()
    metadata = sf.fetch_metadata()

    orgtypes = metadata.get("orgtype", "Unknown")

    if orgtypes == "Developer Edition":
        txt_path = "capabilities.txt"
    else:
        txt_path = "capabilities_enterprise.txt"

    capabilities = read_txt_file(txt_path)

    df = generate_excel(capabilities, metadata, output_path)

    if df is None:
        return ScanResponse(
            message="Excel file is open. Please close and retry.",
            excel_path="",
            llm_output=""
        )

    llm_output = analyze_with_llm(df)

    return ScanResponse(
        message="Scan completed successfully.",
        excel_path=output_path,
        llm_output=llm_output
    )
