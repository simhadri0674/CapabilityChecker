import os
import pandas as pd
from groq import Groq
from salesforce import SalesforceConnector


# -----------------------------
# TXT READER
# -----------------------------
def read_txt_file(txt_path):

    capabilities = []

    with open(txt_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            if "-" in line:
                capability, description = line.split("-", 1)
            else:
                capability, description = line, ""

            capabilities.append({
                "Capability Name": capability.strip(),
                "Description": description.strip()
            })

    return capabilities


# -----------------------------
# CAPABILITY EVALUATION
# -----------------------------
def evaluate_capability(capability_name, metadata):

    name = capability_name.lower()

    object_counts = metadata.get("object_record_counts", {})
    flows = metadata.get("flows", {})
    apex_classes = metadata.get("apex_classes", [])
    service_channels = metadata.get("service_channels", [])

    if "case" in name:
        return "YES" if object_counts.get("Case", 0) > 0 else "NO"

    if "knowledge" in name:
        return "YES" if object_counts.get("KnowledgeArticleVersion", 0) > 0 else "NO"

    if "entitlement" in name or "sla" in name:
        return "YES" if object_counts.get("Entitlement", 0) > 0 else "NO"

    if "report" in name:
        return "YES" if object_counts.get("Report", 0) > 0 else "NO"

    if "dashboard" in name:
        return "YES" if object_counts.get("Dashboard", 0) > 0 else "NO"

    if "flow" in name:
        return "YES" if flows.get("total", 0) > 0 else "NO"

    if "apex" in name:
        return "YES" if len(apex_classes) > 0 else "NO"

    if "omni" in name or "routing" in name:
        return "YES" if len(service_channels) > 0 else "NO"

    return "NO"


# -----------------------------
# EXCEL GENERATION
# -----------------------------
def generate_excel(capabilities, metadata, output_path):

    rows = []

    for cap in capabilities:
        status = evaluate_capability(cap["Capability Name"], metadata)

        rows.append({
            "Capability Name": cap["Capability Name"],
            #"Description": cap["Description"],
            "Enabled (YES/NO)": status
        })

    df = pd.DataFrame(rows)

    os.makedirs("output", exist_ok=True)

    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except PermissionError:
            print("⚠️ Please close the Excel file before running again.")
            return None

    df.to_excel(output_path, index=False)

    print(f"✅ Excel Generated Successfully at: {output_path}")
    return df


# -----------------------------
# LLM ANALYSIS USING GROQ
# -----------------------------
def analyze_with_llm(df):

    client = Groq()

    capability_summary = df.to_string(index=False)

    prompt = f"""
    You are a Salesforce Service Cloud expert.

    Below is a capability assessment table.

    {capability_summary}

    Based on this:
    1. Identify missing capabilities(NO): As well add keypoints to increase volume of words context.
    2. Suggest practical improvement steps mention along with keywords and add some more intersting points.
    3. Provide a 3-phase roadmap (Immediate, Mid-term, Advanced).
    4. Keep recommendations business-oriented and concise.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a Salesforce architecture advisor."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )

    return response.choices[0].message.content


# -----------------------------
# SAVE LLM OUTPUT
# -----------------------------
def save_llm_output(output_text, output_path):

    suggestion_path = output_path.replace(".xlsx", "_LLM_Recommendations.txt")

    with open(suggestion_path, "w", encoding="utf-8") as file:
        file.write(output_text)

    print(f"🧠 LLM Recommendations saved at: {suggestion_path}")


# -----------------------------
# MAIN
# -----------------------------
def main():

    
    output_path = "output/AI_Service_Cloud_Capability_Report.xlsx"

    print("🔐 Connecting to Salesforce...")
    sf = SalesforceConnector()

    print("📥 Fetching Metadata...")
    metadata = sf.fetch_metadata()

    orgtypes = metadata.get("orgtype", "Unknown")
    if orgtypes=="Developer Edition":
        print("⚠️ Developer Edition org detected. Some capabilities may not be available.")
        txt_path = "capabilities.txt"
    elif orgtypes in ["Enterprise Edition", "Unlimited Edition", "Performance Edition"]:
        txt_path = "capabilities_enterprise.txt"
    print("📄 Reading TXT File...")
    capabilities = read_txt_file(txt_path)

    print("📊 Generating Excel...")
    df = generate_excel(capabilities, metadata, output_path)

    if df is not None:
        print("🧠 Sending data to LLM (Groq)...")
        recommendations = analyze_with_llm(df)
        # ✅ PRINT TO CONSOLE
        print("\n" + "=" * 80)
        print("🧠 LLM RECOMMENDATIONS")
        print("=" * 80)
        print(recommendations)
        print("=" * 80 + "\n")
        save_llm_output(recommendations, output_path)


if __name__ == "__main__":
    main()
