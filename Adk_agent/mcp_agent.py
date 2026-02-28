# import os
# import sys
# import json
# import asyncio
# from groq import Groq
# from dotenv import load_dotenv

# from mcp.client.stdio import stdio_client, StdioServerParameters
# from mcp.client.session import ClientSession

# load_dotenv()

# groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# TOOLS = [
#     {
#         "type": "function",
#         "function": {
#             "name": "create_incident",
#             "description": "Create a ServiceNow incident",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "description": {"type": "string"},
#                     "priority": {"type": "string"}
#                 },
#                 "required": ["description", "priority"]
#             }
#         }
#     }
# ]


# async def main():
#     print("🤖 MCP Agent Started")
#     print("Type 'exit' to quit\n")

#     server_params = StdioServerParameters(
#         command=sys.executable,   # ✅ FIXED HERE
#         args=["servicenow_mcp_server.py"],
#     )

#     async with stdio_client(server_params) as (read_stream, write_stream):

#         async with ClientSession(read_stream, write_stream) as session:
#             await session.initialize()

#             while True:
#                 user_input = input("You: ")

#                 if user_input.lower() == "exit":
#                     print("👋 Goodbye!")
#                     break

#                 response = groq_client.chat.completions.create(
#                     model="llama-3.3-70b-versatile",
#                     messages=[
#                         {"role": "system", "content": "You are an IT assistant."},
#                         {"role": "user", "content": user_input}
#                     ],
#                     tools=TOOLS,
#                     tool_choice="auto"
#                 )

#                 message = response.choices[0].message

#                 if message.tool_calls:
#                     tool_call = message.tool_calls[0]
#                     tool_name = tool_call.function.name
#                     arguments = json.loads(tool_call.function.arguments)

#                     print(f"🔧 Executing tool: {tool_name}")

#                     result = await session.call_tool(tool_name, arguments)

#                     output_text = ""
#                     for item in result.content:
#                         if item.type == "text":
#                             output_text += item.text

#                     print("Agent:", output_text)

#                 else:
#                     print("Agent:", message.content)


# if __name__ == "__main__":
#     asyncio.run(main())

import os
import sys
import json
import asyncio
from groq import Groq
from dotenv import load_dotenv

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_incident",
            "description": "Create a ServiceNow incident",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "priority": {"type": "string"}
                },
                "required": ["description", "priority"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_incident_status",
            "description": "Get status of an incident",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "string"}
                },
                "required": ["number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_incident_priority",
            "description": "Update incident priority",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "string"},
                    "priority": {"type": "string"}
                },
                "required": ["number", "priority"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_recent_incidents",
            "description": "List recent incidents",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"}
                }
            }
        }
    }
]


async def main():
    print("🚀 Advanced IT Copilot Started")
    print("Type 'exit' to quit\n")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["servicenow_mcp_server.py"],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            while True:
                user_input = input("You: ")

                if user_input.lower() == "exit":
                    break

                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are an enterprise IT operations assistant."},
                        {"role": "user", "content": user_input}
                    ],
                    tools=TOOLS,
                    tool_choice="auto"
                )

                message = response.choices[0].message

                if message.tool_calls:
                    tool_call = message.tool_calls[0]
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    print(f"🔧 Calling: {tool_name}")
                    result = await session.call_tool(tool_name, arguments)

                    output_text = ""
                    for item in result.content:
                        if item.type == "text":
                            output_text += item.text

                    print("Agent:", output_text)
                else:
                    print("Agent:", message.content)


if __name__ == "__main__":
    asyncio.run(main())