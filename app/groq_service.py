import json
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL

def analyze_with_groq(capabilities_text, metrics):

    

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """
You are a Salesforce Service Cloud Productivity Consultant.

You MUST return:

=== JSON START ===
[ JSON array with:
  capability_name,
  enabled (true/false),
  used (true/false),
  impact_score (1-5),
  effort_score (1-5),
  priority_score (impact + effort),
  adoption_status (GREEN/AMBER/RED),
  recommendation
]
=== JSON END ===

=== REPORT START ===
Generate structured report:

# Generating AI recommendations...

## 1. Identify Missing or Underused Features

## 2. Suggest Productivity Improvements

## 3. Step-by-Step Actions
### Phase 1
### Phase 2
### Phase 3
### Phase 4

=== REPORT END ===

No explanation outside format.
"""


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