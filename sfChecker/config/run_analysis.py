import pandas as pd
import os
from salesforce  import SalesforceConnector


def detect_capability_column(df):
    """
    Auto-detect capability column (no hardcoding)
    """
    for col in df.columns:
        if "capability" in col.lower() or "feature" in col.lower():
            return col
    raise Exception("Capability column not found in Excel")


def detect_status_column(df):
    """
    Auto-detect status/enabled column
    """
    for col in df.columns:
        if "enabled" in col.lower() or "status" in col.lower():
            return col
    raise Exception("Enabled/Status column not found in Excel")


def evaluate_capability(capability_name, metadata):
    """
    Dynamic evaluation logic (no hardcoded values)
    Basic keyword-based mapping using metadata keys.
    """

    name = capability_name.lower()

    # Object-based checks
    if "case" in name:
        return "YES" if metadata["object_record_counts"].get("Case", 0) > 0 else "NO"

    if "knowledge" in name:
        return "YES" if metadata["object_record_counts"].get("KnowledgeArticleVersion", 0) > 0 else "NO"

    if "entitlement" in name or "sla" in name:
        return "YES" if metadata["object_record_counts"].get("Entitlement", 0) > 0 else "NO"

    if "report" in name:
        return "YES" if metadata["object_record_counts"].get("Report", 0) > 0 else "NO"

    if "dashboard" in name:
        return "YES" if metadata["object_record_counts"].get("Dashboard", 0) > 0 else "NO"

    if "flow" in name:
        return "YES" if metadata["flows"]["total"] > 0 else "NO"

    if "apex" in name:
        return "YES" if len(metadata["apex_classes"]) > 0 else "NO"

    if "omni" in name or "routing" in name:
        return "YES" if len(metadata.get("service_channels", [])) > 0 else "NO"

    # Default fallback
    return "NO"


def main():

    print("🔐 Connecting to Salesforce...")
    sf = SalesforceConnector()

    print("📥 Fetching Metadata...")
    metadata = sf.fetch_metadata()

    print("📊 Reading Excel (Exact Format)...")
    input_path = "AI_Service_Cloud_Capability_Report.xlsx"
    df = pd.read_excel(input_path)

    capability_col = detect_capability_column(df)
    status_col = detect_status_column(df)

    print(f"Detected Capability Column: {capability_col}")
    print(f"Detected Status Column: {status_col}")

    print("🔬 Updating Capability Status...")

    for index, row in df.iterrows():
        capability_name = str(row[capability_col])
        result = evaluate_capability(capability_name, metadata)
        df.at[index, status_col] = result

    os.makedirs("output", exist_ok=True)

    output_path = "output/AI_Service_Cloud_Capability_Report_UPDATED.xlsx"
    df.to_excel(output_path, index=False)

    print("🎉 Completed Successfully")
    print(f"📁 Output Saved At: {output_path}")


if __name__ == "__main__":
    main()
