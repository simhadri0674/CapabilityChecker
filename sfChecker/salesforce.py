from importlib import metadata
import os
from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()

class SalesforceConnector:

    def __init__(self):
        self.sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            domain=os.getenv("SF_DOMAIN", "login")
        )

    def fetch_metadata(self):
        """
        Fetch minimal metadata required for analyzer
        """
        metadata = {}

        # Org Info
        # Execute the query
        org_result = self.sf.query("SELECT Id, OrganizationType FROM Organization LIMIT 1")

        # Safely extract records
        if org_result["totalSize"] > 0:
            record = org_result["records"][0]
            metadata["org_id"] = record.get("Id")
            # Note: Case sensitivity matters! Ensure it matches your SOQL casing.
            metadata["orgtype"] = record.get("OrganizationType") 
        else:
            metadata["org_id"] = None
            metadata["orgtype"] = None

        metadata["instance_url"] = self.sf.sf_instance

        # Object record counts
        metadata["object_record_counts"] = {}
        objects_to_check = [
 
            # Core Case Management
            "Case",
            "AssignmentRule",
            "EscalationRule",
            "AutoResponseRule",
        
            # Queues & Routing
            "Group",                 # Case Queues
            "ServiceChannel",        # Omni-channel
            "PresenceConfig",
            "Skill",
            "SkillRequirement",
        
            # Knowledge
            "KnowledgeArticleVersion",
        
            # Communication Channels
            "EmailServices",         # Email-to-Case
            "WebToCaseSettings",     # Web-to-Case
            "LiveChatTranscript",    # Live Chat
        
            # Productivity
            "Macro",
            "QuickText",
        
            # Service Agreements
            "Entitlement",           # SLAs
            "MilestoneType",
            "ServiceContract",
        
            # Field Service
            "WorkOrder",
            "ServiceAppointment",
            "Asset",
        
            # Analytics
            "Report",
            "Dashboard",
        
            # Automation
            "Flow",
            "ApexTrigger",
        
            # Security
            "PermissionSet",
            "Profile",
        
            # Communities
            "Network",               # Customer/Partner Community
        
            # Surveys
            "Survey",
            "SurveyInvitation",
        
            # Social / Messaging
            "MessagingChannel",
        
        ]

        for obj in objects_to_check:
            try:
                result = self.sf.query(f"SELECT COUNT() FROM {obj}")
                metadata["object_record_counts"][obj] = result["totalSize"]
            except:
                metadata["object_record_counts"][obj] = -1

        # Empty placeholders required by analyzer
        metadata["apex_classes"] = []
        metadata["flows"] = {"total": 0}
        metadata["service_channels"] = []
        metadata["bots"] = []
        metadata["knowledge"] = {"enabled": False, "article_count": 0}
        metadata["entitlements"] = {"entitlement_count": 0}
        metadata["networks"] = []
        metadata["surveys"] = {"count": 0}
        metadata["macros"] = {"macro_count": 0, "quick_text_count": 0}
        metadata["reports"] = {"service_reports": 0}

        return metadata
