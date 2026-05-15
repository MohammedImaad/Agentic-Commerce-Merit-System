from fastapi import FastAPI, Request
from langchain_core.messages import HumanMessage, AIMessage

from agent import graph

from db import (
    connect_mongo,
    close_mongo,
    append_message,
    load_last_messages
)

from dotenv import load_dotenv

import requests
import os

# =========================================
# ENV
# =========================================

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# =========================================
# APP
# =========================================

app = FastAPI()

# =========================================
# STARTUP / SHUTDOWN
# =========================================

@app.on_event("startup")
async def startup():
    connect_mongo()

@app.on_event("shutdown")
async def shutdown():
    close_mongo()

# =========================================
# TELEGRAM WEBHOOK
# =========================================

@app.post("/telegram-webhook")
async def telegram_webhook(req: Request):

    data = await req.json()

    print("\n===== TELEGRAM UPDATE =====")
    print(data)

    # =====================================
    # EXTRACT MESSAGE
    # =====================================

    message = data.get("message", {})

    chat_id = message.get("chat", {}).get("id")

    user_text = message.get("text")

    if not chat_id or not user_text:

        return {
            "success": False,
            "error": "No text message"
        }

    thread_id = str(chat_id)

    # =====================================
    # STORE USER MESSAGE
    # =====================================

    await append_message(
        thread_id=thread_id,
        role="user",
        content=user_text
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
    # RUN AGENT
    # =====================================

    state = {
        "thread_id": thread_id,
        "messages": messages,
        "search_results": [],
        "selected_tool": None,
        "required_fields": [],
        "allowed_values": {},
        "collected_inputs": {},
        "pending_fields": []
    }

    result = graph.invoke(state)

    assistant_reply = result["messages"][-1].content

    print("\n===== AGENT REPLY =====")
    print(assistant_reply)

    # =====================================
    # STORE ASSISTANT MESSAGE
    # =====================================

    await append_message(
        thread_id=thread_id,
        role="assistant",
        content=assistant_reply
    )

    # =====================================
    # SEND TELEGRAM MESSAGE
    # =====================================

    telegram_url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    requests.post(
        telegram_url,
        json={
            "chat_id": chat_id,
            "text": assistant_reply
        }
    )

    return {
        "success": True
    }