# import streamlit as st
# import pandas as pd
# import requests
# import os


# API_URL = "http://127.0.0.1:8000/run-scan"
# OUTPUT_PATH = "output/AI_Service_Cloud_Capability_Report.xlsx"
# LLM_TXT_PATH = "output/AI_Service_Cloud_Capability_Report_LLM_Recommendations.txt"


# st.set_page_config(page_title="Service Cloud Capability Analyzer", layout="wide")

# st.title("🚀 Salesforce Service Cloud Capability Analyzer")

# # Run Scan Button
# if st.button("Run Capability Scan"):

#     with st.spinner("Running scan..."):
#         response = requests.get(API_URL)

#         if response.status_code == 200:
#             data = response.json()
#             st.success(data["message"])
#         else:
#             st.error("Scan failed.")


# # Show Excel Data
# if os.path.exists(OUTPUT_PATH):

#     st.subheader("📊 Capability Assessment Table")

#     df = pd.read_excel(OUTPUT_PATH)
#     st.dataframe(df, use_container_width=True)


# # Show LLM Recommendations
# if os.path.exists(LLM_TXT_PATH):

#     st.subheader("🧠 Improvisation Recommendations")

#     with open(LLM_TXT_PATH, "r", encoding="utf-8") as file:
#         llm_text = file.read()

#     st.markdown(llm_text)


# # # Show TXT Feature Context
# # st.subheader("📄 Capability Definitions")

# # if os.path.exists("capabilities.txt"):
# #     with open("capabilities.txt", "r", encoding="utf-8") as file:
# #         txt_content = file.read()

# #     st.text_area("Feature Context", txt_content, height=300)
import streamlit as st
import pandas as pd
import requests
import os

API_URL = "http://127.0.0.1:8000/run-scan"
OUTPUT_PATH = "output/AI_Service_Cloud_Capability_Report.xlsx"
LLM_TXT_PATH = "output/AI_Service_Cloud_Capability_Report_LLM_Recommendations.txt"

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Service Cloud Capability Analyzer",
    layout="wide"
)

st.title("Salesforce Service Cloud Capability Analyzer")

# --------------------------------------------------
# CLEAN PROFESSIONAL STYLING (ONLY COMPONENTS)
# --------------------------------------------------
st.markdown("""
<style>
.summary-box {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}
.small-title {
    font-size: 14px;
    color: #666;
}
.big-number {
    font-size: 24px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# RUN SCAN BUTTON
# --------------------------------------------------
if st.button("Run Capability Scan"):
    with st.spinner("Running Salesforce Scan..."):
        response = requests.get(API_URL)

        if response.status_code == 200:
            data = response.json()
            st.success(data["message"])
        else:
            st.error("Scan failed. Please check API.")


# --------------------------------------------------
# DISPLAY DATA
# --------------------------------------------------
if os.path.exists(OUTPUT_PATH):

    df = pd.read_excel(OUTPUT_PATH)

    # Calculate metrics
    total = len(df)
    used = len(df[df["Enabled (YES/NO)"] == "YES"])
    unused = len(df[df["Enabled (YES/NO)"] == "NO"])
    percentage = round((used / total) * 100, 2) if total > 0 else 0

    st.subheader("Capability Summary")

    col1, col2, col3,col4 = st.columns(4)

    col1.markdown(f"""
        <div class="summary-box">
            <div class="small-title">Total Capabilities</div>
            <div class="big-number">{total}</div>
        </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
        <div class="summary-box">
            <div class="small-title">Enabled</div>
            <div class="big-number">{used}</div>
        </div>
    """, unsafe_allow_html=True)

    col3.markdown(f"""
        <div class="summary-box">
            <div class="small-title">Utilization %</div>
            <div class="big-number">{unused}%</div>
        </div>
    """, unsafe_allow_html=True)

    col4.markdown(f"""
        <div class="summary-box">
            <div class="small-title">Unused</div>
            <div class="big-number">{percentage}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Capability Assessment")

    # --------------------------------------------------
    # MODIFY COLUMN FOR DISPLAY (✔ / ✖)
    # --------------------------------------------------
    def convert_status(val):
        if val == "YES":
            return "✔ Used"
        else:
            return "✖ Unused"

    df_display = df.copy()
    df_display["Status"] = df_display["Enabled (YES/NO)"].apply(convert_status)
    df_display = df_display.drop(columns=["Enabled (YES/NO)"])

    # --------------------------------------------------
    # TABLE STYLING
    # --------------------------------------------------
    def style_status(val):
        if "✔" in val:
            return "color: green; font-weight: 500;"
        elif "✖" in val:
            return "color: red; font-weight: 500;"
        return ""

    styled_df = df_display.style.map(
        style_status,
        subset=["Status"]
    )

    st.dataframe(styled_df, use_container_width=True)


# --------------------------------------------------
# LLM RECOMMENDATIONS
# --------------------------------------------------
if os.path.exists(LLM_TXT_PATH):

    st.markdown("---")
    st.subheader("Improvization Steps & Roadmap")

    with open(LLM_TXT_PATH, "r", encoding="utf-8") as file:
        llm_text = file.read()

    st.write(llm_text)


