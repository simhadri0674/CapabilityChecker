import json
import pandas as pd
import os
from app.config import REPORT_FOLDER

def extract_sections(output):
    json_part = output.split("=== JSON START ===")[1].split("=== JSON END ===")[0].strip()
    report_part = output.split("=== REPORT START ===")[1].split("=== REPORT END ===")[0].strip()
    return json.loads(json_part), report_part

def build_excel_format(data):

    rows = []

    for item in data:
        rows.append({
            "Feature": item.get("capability_name", ""),
            "Licensed": "Yes",
            "Enabled": "Yes" if item.get("enabled") else "No",
            "Configured": "Yes" if item.get("enabled") else "No",
            "Actively Used": "Yes" if item.get("used") else "No",
            "Impact Score": item.get("impact_score", 0),
            "Effort Score": item.get("effort_score", 0),
            "Priority Score": item.get("priority_score", 0),
            "Adoption Status": item.get("adoption_status", ""),
            "Recommendation": item.get("recommendation", "")
        })

    return pd.DataFrame(rows)

def save_reports(df, markdown_text):

    os.makedirs(REPORT_FOLDER, exist_ok=True)

    excel_path = os.path.join(REPORT_FOLDER, "AI_Service_Cloud_Capability_Report.xlsx")
    md_path = os.path.join(REPORT_FOLDER, "AI_Service_Cloud_Report.md")

    df.to_excel(excel_path, index=False)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return excel_path, md_path