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
        org = self.sf.query("SELECT Id FROM Organization LIMIT 1")
        metadata["org_id"] = org["records"][0]["Id"]
        metadata["instance_url"] = self.sf.sf_instance

        # Object record counts
        metadata["object_record_counts"] = {}
        objects_to_check = [
            "Case",
            "Account",
            "Contact",
            "LiveChatTranscript",
            "VoiceCall"
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
