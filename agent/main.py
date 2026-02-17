import os
import json
import pandas as pd
from dotenv import load_dotenv
from simple_salesforce import Salesforce
from groq import Groq
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

load_dotenv()

# =====================================================
# CONNECTIONS
# =====================================================

def connect_salesforce():
    return Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN")
    )

def connect_groq():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

# =====================================================
# SAFE QUERY
# =====================================================

def run_count_query(sf, soql):
    try:
        result = sf.query(soql)
        return result["totalSize"]
    except:
        return 0

# =====================================================
# COLLECT ORG METRICS
# =====================================================

def collect_org_metrics(sf):

    return {
        "cases_last_30_days": run_count_query(sf,
            "SELECT Id FROM Case WHERE CreatedDate = LAST_N_DAYS:30"),

        "email_messages": run_count_query(sf,
            "SELECT Id FROM EmailMessage WHERE CreatedDate = LAST_N_DAYS:30"),

        "knowledge_articles": run_count_query(sf,
            "SELECT Id FROM KnowledgeArticleVersion WHERE PublishStatus='Online'"),

        "agent_work": run_count_query(sf,
            "SELECT Id FROM AgentWork WHERE CreatedDate = LAST_N_DAYS:30"),

        "flows": run_count_query(sf,
            "SELECT Id FROM Flow"),

        "apex_triggers": run_count_query(sf,
            "SELECT Id FROM ApexTrigger"),

        "dashboards": run_count_query(sf,
            "SELECT Id FROM Dashboard"),

        "reports": run_count_query(sf,
            "SELECT Id FROM Report")
    }

# =====================================================
# READ CAPABILITIES FILE
# =====================================================

def read_capabilities(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# =====================================================
# GROQ ANALYSIS
# =====================================================

def analyze_with_groq(client, capabilities_text, metrics):

    model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

    system_prompt = """
You are a Salesforce Service Cloud Productivity Consultant.

You MUST return:

=== JSON START ===
[ JSON array with:
  capability_name,
  enabled (true/false),
  used (true/false),
  impact_score (1-5),
  effort_score (1-5),
  priority_score (impact + effort),
  adoption_status (GREEN/AMBER/RED),
  recommendation
]
=== JSON END ===

=== REPORT START ===
Generate structured report:

# Generating AI recommendations...

## 1. Identify Missing or Underused Features

## 2. Suggest Productivity Improvements

## 3. Step-by-Step Actions
### Phase 1
### Phase 2
### Phase 3
### Phase 4

=== REPORT END ===

No explanation outside format.
"""

    user_prompt = f"""
Capabilities:
{capabilities_text}

Org Metrics:
{json.dumps(metrics, indent=2)}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=6000
    )

    return response.choices[0].message.content

# =====================================================
# PARSE LLM OUTPUT
# =====================================================

def extract_sections(output):

    json_part = output.split("=== JSON START ===")[1].split("=== JSON END ===")[0].strip()
    report_part = output.split("=== REPORT START ===")[1].split("=== REPORT END ===")[0].strip()

    parsed_json = json.loads(json_part)

    return parsed_json, report_part

# =====================================================
# BUILD EXCEL FORMAT
# =====================================================

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

# =====================================================
# PDF GENERATOR
# =====================================================

def generate_pdf(report_text):

    doc = SimpleDocTemplate("AI_Service_Cloud_Report.pdf", pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    for line in report_text.split("\n"):
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 8))

    doc.build(elements)

# =====================================================
# MAIN
# =====================================================

def main():

    print("Connecting to Salesforce...")
    sf = connect_salesforce()

    print("Collecting org metrics...")
    metrics = collect_org_metrics(sf)

    print("Reading capabilities file...")
    capabilities_text = read_capabilities("service_capabilities.txt")

    print("Connecting to Groq...")
    client = connect_groq()

    print("Running LLM analysis...")
    llm_output = analyze_with_groq(client, capabilities_text, metrics)

    parsed_json, report_markdown = extract_sections(llm_output)

    # Excel
    df = build_excel_format(parsed_json)
    df.to_excel("AI_Service_Cloud_Capability_Report.xlsx", index=False)

    # Markdown
    with open("AI_Service_Cloud_Report.md", "w", encoding="utf-8") as f:
        f.write(report_markdown)

    print("\n===== PRODUCTIVITY IMPROVEMENT REPORT =====\n")
    print(report_markdown)

    # PDF
    generate_pdf(report_markdown)

    print("\n✅ Excel, Markdown, and PDF Generated Successfully")

if __name__ == "__main__":
    main()
