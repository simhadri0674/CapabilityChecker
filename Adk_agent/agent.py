# import os
# import re
# from groq import Groq
# from dotenv import load_dotenv

# # Load .env if exists
# load_dotenv()

# # Initialize Groq client
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# # -----------------------------
# # Simple Greeting Tool
# # -----------------------------
# def greet_user(name: str) -> str:
#     return f"Hello {name}! 👋 Welcome to your Groq-powered agent."


# # -----------------------------
# # Extract Name (Simple Logic)
# # -----------------------------
# def extract_name(user_input: str):
#     match = re.search(r"my name is (\w+)", user_input.lower())
#     if match:
#         return match.group(1).capitalize()
#     return None


# # -----------------------------
# # Terminal Chat Loop
# # -----------------------------
# def chat():
#     print("🤖 Groq Terminal Agent Started (type 'exit' to quit)\n")

#     messages = [
#         {
#             "role": "system",
#             "content": "You are a friendly assistant."
#         }
#     ]

#     while True:
#         user_input = input("You: ")

#         if user_input.lower() == "exit":
#             print("👋 Goodbye!")
#             break

#         # Check if greeting tool should be used
#         name = extract_name(user_input)
#         if name:
#             print("Agent:", greet_user(name))
#             continue

#         # Otherwise call Groq LLM
#         messages.append({"role": "user", "content": user_input})

#         response = client.chat.completions.create(
#             model="llama-3.3-70b-versatile",   # Fast & powerful Groq model
#             messages=messages,
#         )

#         reply = response.choices[0].message.content
#         print("Agent:", reply)

#         messages.append({"role": "assistant", "content": reply})


# if __name__ == "__main__":
#     chat()
import os
import re
import requests
from groq import Groq
from dotenv import load_dotenv

# -------------------------------------------------
# Load Environment Variables
# -------------------------------------------------
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SN_INSTANCE = os.getenv("SN_INSTANCE_URL")
SN_USERNAME = os.getenv("SN_USERNAME")
SN_PASSWORD = os.getenv("SN_PASSWORD")

client = Groq(api_key=GROQ_API_KEY)

# -------------------------------------------------
# ServiceNow API Call
# -------------------------------------------------
def create_incident(description: str, priority: str) -> str:
    url = f"{SN_INSTANCE}/api/now/table/incident"

    payload = {
        "short_description": description,
        "priority": priority
    }

    response = requests.post(
        url,
        auth=(SN_USERNAME, SN_PASSWORD),
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 201:
        result = response.json()["result"]
        return f"✅ Incident created successfully!\nIncident Number: {result['number']}"
    else:
        return f"❌ Failed to create incident:\n{response.text}"


# -------------------------------------------------
# Extract Fields From User Input
# -------------------------------------------------
def extract_description(text: str):
    match = re.search(r"description\s*:\s*(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_priority(text: str):
    match = re.search(r"priority\s*:\s*(\d+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


# -------------------------------------------------
# Main Chat Loop
# -------------------------------------------------
def chat():
    print("🤖 ServiceNow Incident Agent Started")
    print("Type 'exit' to quit\n")

    session_data = {
        "description": None,
        "priority": None,
        "incident_mode": False
    }

    while True:
        user_input = input("You: ")

        if user_input.lower() in [ "exit", "quit", "bye" ]:
            print("👋 Goodbye!")
            break

        # Detect intent
        if "create incident" in user_input.lower():
            session_data["incident_mode"] = True

        # Extract details if provided
        desc = extract_description(user_input)
        prio = extract_priority(user_input)

        if desc:
            session_data["description"] = desc

        if prio:
            session_data["priority"] = prio

        # If user wants to create incident
        if session_data["incident_mode"]:

            # Ask for missing fields
            if not session_data["description"]:
                print("Agent: Please provide description (format: description: your text)")
                continue

            if not session_data["priority"]:
                print("Agent: Please provide priority (format: priority: 1-5)")
                continue

            # All data available → create incident
            result = create_incident(
                session_data["description"],
                session_data["priority"]
            )

            print("Agent:", result)

            # Reset session after creation
            session_data = {
                "description": None,
                "priority": None,
                "incident_mode": False
            }

            continue

        # Normal conversation using Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an IT support assistant."},
                {"role": "user", "content": user_input}
            ]
        )

        print("Agent:", response.choices[0].message.content)


if __name__ == "__main__":
    chat()