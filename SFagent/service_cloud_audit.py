import os
import pandas as pd
from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()

# =====================================================
# CONNECT
# =====================================================

def connect_salesforce():
    return Salesforce(
        username=os.getenv("SF_USERNAME"),
        password=os.getenv("SF_PASSWORD"),
        security_token=os.getenv("SF_SECURITY_TOKEN")
    )


# =====================================================
# GENERIC QUERY HELPER
# =====================================================

def run_count_query(sf, soql):
    try:
        result = sf.query(soql)
        return result['records'][0]['total']
    except:
        return 0


# =====================================================
# DYNAMIC SCORING ENGINE
# =====================================================

def calculate_impact(license_utilization, usage_count, criticality_weight):
    # License Gap (0-5)
    license_gap = 5 if license_utilization < 50 else 3 if license_utilization < 80 else 1

    # Usage Gap (0-5)
    usage_gap = 5 if usage_count == 0 else 3 if usage_count < 10 else 1

    impact = round((license_gap + usage_gap + criticality_weight) / 3)
    return min(max(impact, 1), 5)


def calculate_effort(configured, data_volume):
    config_score = 2 if configured else 4
    volume_score = 1 if data_volume > 100 else 2 if data_volume > 10 else 3

    effort = round((config_score + volume_score) / 2)
    return min(max(effort, 1), 5)


def calculate_status(enabled, used):
    if enabled and used:
        return "GREEN"
    elif enabled and not used:
        return "RED"
    else:
        return "AMBER"


# =====================================================
# FEATURE ANALYZERS
# =====================================================

def analyze_cases(sf):

    total_cases = run_count_query(sf,
        "SELECT COUNT(Id) total FROM Case WHERE CreatedDate = LAST_N_DAYS:30"
    )

    total_licenses = run_count_query(sf,
        "SELECT SUM(UsedLicenses) total FROM UserLicense WHERE Name LIKE '%Service%'"
    )

    license_util = 100 if total_licenses == 0 else min((total_cases / total_licenses) * 100, 100)

    enabled = True
    used = total_cases > 0
    criticality = 5

    impact = calculate_impact(license_util, total_cases, criticality)
    effort = calculate_effort(True, total_cases)

    return build_row("SV-SVC-001", "Case Management", enabled, used, impact, effort)


def analyze_omnichannel(sf):

    agent_work = run_count_query(sf,
        "SELECT COUNT(Id) total FROM AgentWork WHERE CreatedDate = LAST_N_DAYS:30"
    )

    routing_config = run_count_query(sf,
        "SELECT COUNT(Id) total FROM RoutingConfiguration"
    )

    enabled = routing_config > 0
    used = agent_work > 0
    criticality = 5

    impact = calculate_impact(50, agent_work, criticality)
    effort = calculate_effort(enabled, agent_work)

    return build_row("SV-SVC-002", "Omni-Channel", enabled, used, impact, effort)


def analyze_email_to_case(sf):

    email_count = run_count_query(sf,
        "SELECT COUNT(Id) total FROM EmailMessage WHERE CreatedDate = LAST_N_DAYS:30"
    )

    enabled = True
    used = email_count > 0
    criticality = 4

    impact = calculate_impact(50, email_count, criticality)
    effort = calculate_effort(True, email_count)

    return build_row("SV-SVC-003", "Email-to-Case", enabled, used, impact, effort)


def analyze_knowledge(sf):

    articles = run_count_query(sf,
        "SELECT COUNT(Id) total FROM KnowledgeArticleVersion WHERE PublishStatus='Online'"
    )

    enabled = articles >= 0
    used = articles > 0
    criticality = 4

    impact = calculate_impact(50, articles, criticality)
    effort = calculate_effort(enabled, articles)

    return build_row("SV-SVC-004", "Knowledge", enabled, used, impact, effort)


# =====================================================
# ROW BUILDER
# =====================================================

def build_row(cap_id, name, enabled, used, impact, effort):

    priority = impact + effort

    return {
        "capability_id": cap_id,
        "capability_name": name,
        "cloud": "Service",
        "enabled": enabled,
        "used": used,
        "adoption_status": calculate_status(enabled, used),
        "impact_score": impact,
        "effort_score": effort,
        "priority_score": priority
    }


# =====================================================
# MAIN
# =====================================================

def main():

    print("Connecting to Salesforce...")
    sf = connect_salesforce()

    capabilities = []

    capabilities.append(analyze_cases(sf))
    capabilities.append(analyze_omnichannel(sf))
    capabilities.append(analyze_email_to_case(sf))
    capabilities.append(analyze_knowledge(sf))

    df = pd.DataFrame(capabilities)

    df.to_excel("Service_Cloud_Dynamic_Capability_Report.xlsx", index=False)

    print("✅ Dynamic Service Cloud Report Generated Successfully")


if __name__ == "__main__":
    main()
