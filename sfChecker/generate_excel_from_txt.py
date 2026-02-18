import pandas as pd
import os
from salesforce import SalesforceConnector


def read_txt_file(txt_path):
    """
    Reads capability text file.
    Expected format:
    Capability Name - Description
    """

    capabilities = []

    with open(txt_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if "-" in line:
            parts = line.split("-", 1)
            capability = parts[0].strip()
            description = parts[1].strip()
        else:
            capability = line.strip()
            description = ""

        capabilities.append({
            "Capability Name": capability,
            "Description": description
        })

    return capabilities


def evaluate_capability(capability_name, metadata):
    """
    Safely evaluates capability based on Salesforce metadata.
    """

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


def generate_excel(capabilities, metadata, output_path):
    """
    Generates Excel with Enabled column filled dynamically.
    """

    final_data = []

    for cap in capabilities:
        status = evaluate_capability(cap["Capability Name"], metadata)

        final_data.append({
            "Capability Name": cap["Capability Name"],
            "Description": cap["Description"],
            "Enabled (YES/NO)": status
        })

    df = pd.DataFrame(final_data)

    os.makedirs("output", exist_ok=True)
    df.to_excel(output_path, index=False)

    print(f"✅ Excel Generated Successfully at: {output_path}")


def main():

    txt_path = "capabilities.txt"
    output_path = "output/AI_Service_Cloud_Capability_Report.xlsx"

    print("🔐 Connecting to Salesforce...")
    sf = SalesforceConnector()

    print("📥 Fetching Metadata...")
    metadata = sf.fetch_metadata()

    print("📄 Reading TXT File...")
    capabilities = read_txt_file(txt_path)

    print("📊 Generating Excel...")
    generate_excel(capabilities, metadata, output_path)


if __name__ == "__main__":
    main()
