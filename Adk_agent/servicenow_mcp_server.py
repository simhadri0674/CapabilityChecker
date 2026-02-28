# import os
# import requests
# from dotenv import load_dotenv
# from mcp.server.fastmcp import FastMCP

# load_dotenv()

# SN_INSTANCE = os.getenv("SN_INSTANCE_URL")
# SN_USERNAME = os.getenv("SN_USERNAME")
# SN_PASSWORD = os.getenv("SN_PASSWORD")

# if not SN_INSTANCE or not SN_USERNAME or not SN_PASSWORD:
#     raise ValueError("ServiceNow environment variables not set properly.")

# mcp = FastMCP("ServiceNow-MCP")


# @mcp.tool()
# def create_incident(description: str, priority: str) -> str:
#     url = f"{SN_INSTANCE}/api/now/table/incident"

#     payload = {
#         "short_description": description,
#         "priority": priority
#     }

#     response = requests.post(
#         url,
#         auth=(SN_USERNAME, SN_PASSWORD),
#         json=payload,
#         headers={"Content-Type": "application/json"}
#     )

#     if response.status_code == 201:
#         result = response.json()["result"]
#         return f"Incident created successfully. Number: {result['number']}"
#     else:
#         return f"Failed: {response.text}"


# if __name__ == "__main__":
#     print("🚀 ServiceNow MCP Server Started")
#     mcp.run()
import os
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

instance = os.getenv("SN_INSTANCE")
user = os.getenv("SN_USERNAME")
pwd = os.getenv("SN_PASSWORD")

BASE_URL = f"https://{instance}.service-now.com/api/now/table/incident"

mcp = FastMCP("ServiceNow MCP Server")


def snow_request(method, url, **kwargs):
    try:
        response = requests.request(
            method,
            url,
            auth=(user, pwd),
            headers={"Accept": "application/json"},
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_incident(description: str, priority: str):
    payload = {
        "short_description": description,
        "priority": priority
    }

    data = snow_request("POST", BASE_URL, json=payload)

    if "result" in data:
        return f"✅ Incident created successfully.\nNumber: {data['result']['number']}"
    return f"❌ Error: {data}"


@mcp.tool()
def get_incident_status(number: str):
    url = f"{BASE_URL}?sysparm_query=number={number}"
    data = snow_request("GET", url)

    if data.get("result"):
        incident = data["result"][0]
        return f"📌 Status: {incident['state']} | Priority: {incident['priority']}"
    return "❌ Incident not found."


@mcp.tool()
def update_incident_priority(number: str, priority: str):
    url = f"{BASE_URL}?sysparm_query=number={number}"
    data = snow_request("GET", url)

    if not data.get("result"):
        return "❌ Incident not found."

    sys_id = data["result"][0]["sys_id"]

    update_url = f"{BASE_URL}/{sys_id}"
    update_data = snow_request("PATCH", update_url, json={"priority": priority})

    if "result" in update_data:
        return f"🔄 Priority updated to {priority}"
    return f"❌ Update failed: {update_data}"


@mcp.tool()
def list_recent_incidents(limit: int = 5):
    url = f"{BASE_URL}?sysparm_limit={limit}&sysparm_order_by_desc=sys_created_on"
    data = snow_request("GET", url)

    if data.get("result"):
        output = []
        for inc in data["result"]:
            output.append(f"{inc['number']} - {inc['short_description']}")
        return "\n".join(output)

    return "❌ No incidents found."


if __name__ == "__main__":
    mcp.run()