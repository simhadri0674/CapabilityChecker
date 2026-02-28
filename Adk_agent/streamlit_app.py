import asyncio
import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

load_dotenv()

MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
SYSTEM_PROMPT = "You are an enterprise IT operations assistant. Use tools when required."

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_incident",
            "description": "Create a ServiceNow incident.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["description", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_incident_status",
            "description": "Get the status of a ServiceNow incident.",
            "parameters": {
                "type": "object",
                "properties": {"number": {"type": "string"}},
                "required": ["number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_incident_priority",
            "description": "Update incident priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["number", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recent_incidents",
            "description": "List recent incidents.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
    },
]


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts)
    return str(content or "")


async def run_mcp_turn(messages: list[dict], client: Groq) -> tuple[str, list[str]]:
    script_dir = Path(__file__).resolve().parent
    mcp_server_path = script_dir / "servicenow_mcp_server.py"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(mcp_server_path)],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            message = response.choices[0].message
            tool_calls = message.tool_calls or []

            if not tool_calls:
                return _extract_text(message.content), []

            outputs: list[str] = []
            called_tools: list[str] = []

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                raw_args = tool_call.function.arguments or "{}"
                args = json.loads(raw_args)

                result = await session.call_tool(tool_name, args)
                called_tools.append(tool_name)

                text_chunks = []
                for item in result.content:
                    if getattr(item, "type", "") == "text":
                        text_chunks.append(item.text)
                outputs.append("\n".join(text_chunks).strip())

            combined_output = "\n\n".join([x for x in outputs if x])
            return combined_output or "Tool executed with no text output.", called_tools


def build_app() -> None:
    st.set_page_config(page_title="ServiceNow MCP Agent", page_icon="bot", layout="centered")

    st.title("ServiceNow MCP Agent")
    st.caption("Coordinate with your MCP ServiceNow tools through this UI.")

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        st.error("Missing GROQ_API_KEY in your environment.")
        st.stop()

    client = Groq(api_key=groq_api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.subheader("Session")
        st.text(f"Model: {MODEL_NAME}")
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask to create, update, check, or list incidents")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Working..."):
            try:
                reply, tools_used = asyncio.run(run_mcp_turn(st.session_state.messages, client))
                if tools_used:
                    st.caption(f"Tools: {', '.join(tools_used)}")
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as exc:
                st.error(f"Failed to communicate with MCP server: {exc}")


if __name__ == "__main__":
    build_app()
