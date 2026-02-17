from simple_salesforce import Salesforce
from app.config import SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN

def connect_salesforce():
    return Salesforce(
        username=SF_USERNAME,
        password=SF_PASSWORD,
        security_token=SF_SECURITY_TOKEN
    )

def run_count_query(sf, soql):
    try:
        return sf.query(soql)["totalSize"]
    except Exception:
        return 0

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
        "flows": run_count_query(sf, "SELECT Id FROM Flow"),
        "apex_triggers": run_count_query(sf, "SELECT Id FROM ApexTrigger"),
        "dashboards": run_count_query(sf, "SELECT Id FROM Dashboard"),
        "reports": run_count_query(sf, "SELECT Id FROM Report")
    }