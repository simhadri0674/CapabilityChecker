import json
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL

def analyze_with_groq(capabilities_text, metrics):

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = "You are a Salesforce Service Cloud Consultant. Return structured JSON and report."

    user_prompt = f"""
Capabilities:
{capabilities_text}

Org Metrics:
{json.dumps(metrics, indent=2)}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=4000
    )

    return response.choices[0].message.content