import streamlit as st
import pandas as pd
import requests
import os


API_URL = "http://127.0.0.1:8000/run-scan"
OUTPUT_PATH = "output/AI_Service_Cloud_Capability_Report.xlsx"
LLM_TXT_PATH = "output/AI_Service_Cloud_Capability_Report_LLM_Recommendations.txt"


st.set_page_config(page_title="Service Cloud Capability Analyzer", layout="wide")

st.title("🚀 Salesforce Service Cloud Capability Analyzer")

# Run Scan Button
if st.button("Run Capability Scan"):

    with st.spinner("Running scan..."):
        response = requests.get(API_URL)

        if response.status_code == 200:
            data = response.json()
            st.success(data["message"])
        else:
            st.error("Scan failed.")


# Show Excel Data
if os.path.exists(OUTPUT_PATH):

    st.subheader("📊 Capability Assessment Table")

    df = pd.read_excel(OUTPUT_PATH)
    st.dataframe(df, use_container_width=True)


# Show LLM Recommendations
if os.path.exists(LLM_TXT_PATH):

    st.subheader("🧠 Improvisation Recommendations")

    with open(LLM_TXT_PATH, "r", encoding="utf-8") as file:
        llm_text = file.read()

    st.markdown(llm_text)


# # Show TXT Feature Context
# st.subheader("📄 Capability Definitions")

# if os.path.exists("capabilities.txt"):
#     with open("capabilities.txt", "r", encoding="utf-8") as file:
#         txt_content = file.read()

#     st.text_area("Feature Context", txt_content, height=300)
