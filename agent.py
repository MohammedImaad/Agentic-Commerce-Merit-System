from typing import Annotated, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage
)

from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

import os
import json

from tools import (
    search_tools,
    execute_x402_tool,
    check_balance,
    get_wallet_addresses,
    create_wallet_if_not_exists
)

from db import (
    connect_mongo,
    close_mongo,
    append_message,
    load_last_messages
)

# =========================================
# ENV
# =========================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================================
# LLM
# =========================================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

# =========================================
# STATE
# =========================================

class State(TypedDict):

    messages: Annotated[list[AnyMessage], add_messages]

    thread_id: str

    search_results: list

    selected_tool: Optional[dict]

    required_fields: list[str]

    allowed_values: dict

    collected_inputs: dict

    pending_fields: list[str]

# =========================================
# TOOLS
# =========================================

tools_for_llm = [
    search_tools,
    execute_x402_tool,
    check_balance,
    get_wallet_addresses,
    create_wallet_if_not_exists
]

tool_node = ToolNode(tools_for_llm)

llm_with_tools = llm.bind_tools(tools_for_llm)

# =========================================
# HELPERS
# =========================================

def extract_required_fields(tool):

    semantic = tool.get("semanticDescription", "")

    required = []
    allowed_values = {}

    if "360p" in semantic:

        required.append("quality")

        allowed_values["quality"] = [
            "360p",
            "720p",
            "1080p"
        ]

    if "tube-100mb" in semantic:

        required.append("tier")

        allowed_values["tier"] = [
            "tube-100mb",
            "tube-500mb",
            "tube-1gb"
        ]

    if "youtube" in semantic.lower():
        required.append("url")

    return required, allowed_values

# =========================================
# AGENT NODE
# =========================================

def agent_node(state: State):

    print("\n===== AGENT NODE =====")
    print(state)

    # =====================================
    # HANDLE SLOT FILLING
    # =====================================

    if state["pending_fields"]:

        field = state["pending_fields"][0]

        user_value = state["messages"][-1].content.strip()

        state["collected_inputs"][field] = user_value

        state["pending_fields"] = state["pending_fields"][1:]

        if state["pending_fields"]:

            next_field = state["pending_fields"][0]

            allowed = state["allowed_values"].get(next_field)

            if allowed:

                return {
                    "messages": [
                        AIMessage(
                            content=f"""
Please provide: {next_field}

Allowed values:
{allowed}
"""
                        )
                    ]
                }

            return {
                "messages": [
                    AIMessage(
                        content=f"Please provide: {next_field}"
                    )
                ]
            }

        tool = state["selected_tool"]

        print("\n===== EXECUTING TOOL =====")
        print(tool)

        result = execute_x402_tool(
            url=tool["origin"]["url"] + tool["path"],
            method=tool["method"],
            body=state["collected_inputs"]
        )

        return {
            "messages": [
                AIMessage(
                    content=json.dumps(result, indent=2)
                )
            ]
        }

    # =====================================
    # NORMAL LLM FLOW
    # =====================================

    prompt = """
You are an AI API marketplace agent.

You help users:
- search APIs
- inspect APIs
- buy/use APIs
- execute paid APIs

Rules:
- Use tools when necessary
- Be concise
- Never hallucinate parameters
- If user wants to use an API,
  gather required fields first
"""

    response = llm_with_tools.invoke(
        [HumanMessage(content=prompt)] + state["messages"]
    )

    print("\n===== LLM RESPONSE =====")
    print(response)

    return {
        "messages": [response]
    }

# =========================================
# ROUTER
# =========================================

def should_continue(state: State):

    last_message = state["messages"][-1]

    print("\n===== SHOULD CONTINUE =====")
    print(last_message)

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    if state["search_results"]:

        user_text = last_message.content.lower()

        if (
            "use this" in user_text
            or "i want this" in user_text
            or "use api" in user_text
        ):

            selected_tool = state["search_results"][0]

            required_fields, allowed_values = extract_required_fields(
                selected_tool
            )

            pending = required_fields.copy()

            first_field = pending[0]

            allowed = allowed_values.get(first_field)

            if allowed:

                return {
                    "selected_tool": selected_tool,
                    "required_fields": required_fields,
                    "allowed_values": allowed_values,
                    "collected_inputs": {},
                    "pending_fields": pending,
                    "messages": [
                        AIMessage(
                            content=f"""
Please provide: {first_field}

Allowed values:
{allowed}
"""
                        )
                    ]
                }

            return {
                "selected_tool": selected_tool,
                "required_fields": required_fields,
                "allowed_values": allowed_values,
                "collected_inputs": {},
                "pending_fields": pending,
                "messages": [
                    AIMessage(
                        content=f"Please provide: {first_field}"
                    )
                ]
            }

    return END

# =========================================
# GRAPH
# =========================================

builder = StateGraph(State)

builder.add_node("agent", agent_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "agent")

builder.add_conditional_edges(
    "agent",
    should_continue
)

builder.add_edge("tools", "agent")

graph = builder.compile()
# =========================================
# TEST LOOP
# =========================================
'''
async def main():

    connect_mongo()

    try:

        thread_id = "demo-thread"

        while True:

            user_input = input("\nYou: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            # =====================================
            # STORE USER MESSAGE
            # =====================================

            await append_message(
                thread_id=thread_id,
                role="user",
                content=user_input
            )

            # =====================================
            # LOAD HISTORY
            # =====================================

            history = await load_last_messages(
                thread_id=thread_id,
                limit=10
            )

            # =====================================
            # CONVERT TO LANGCHAIN MESSAGES
            # =====================================

            messages = []

            for m in history:

                if m["role"] == "user":

                    messages.append(
                        HumanMessage(content=m["content"])
                    )

                else:

                    messages.append(
                        AIMessage(content=m["content"])
                    )

            # =====================================
            # RUN GRAPH
            # =====================================

            conversation_state = {
                "thread_id": thread_id,
                "messages": messages,
                "search_results": [],
                "selected_tool": None,
                "required_fields": [],
                "allowed_values": {},
                "collected_inputs": {},
                "pending_fields": []
            }

            result = graph.invoke(conversation_state)

            assistant_response = result["messages"][-1].content

            print("\nAgent:")
            print(assistant_response)

            # =====================================
            # STORE ASSISTANT MESSAGE
            # =====================================

            await append_message(
                thread_id=thread_id,
                role="assistant",
                content=assistant_response
            )

    finally:

        close_mongo()


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())
'''