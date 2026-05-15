# db.py

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

_client: AsyncIOMotorClient | None = None


def connect_mongo():
    global _client

    uri = os.getenv("MONGODB_URI")

    if not uri:
        raise RuntimeError("MONGODB_URI missing")

    _client = AsyncIOMotorClient(uri)


def close_mongo():
    global _client

    if _client:
        _client.close()
        _client = None


def get_db():
    if _client is None:
        raise RuntimeError("Mongo not connected")

    db_name = os.getenv("MONGODB_DB")

    if not db_name:
        raise RuntimeError("MONGODB_DB missing")

    return _client[db_name]


def conversations():
    return get_db()["conversations"]


async def append_message(
    thread_id: str,
    role: str,
    content: str
):
    await conversations().update_one(
        {"thread_id": thread_id},
        {
            "$push": {
                "messages": {
                    "role": role,
                    "content": content,
                    "ts": datetime.now(timezone.utc)
                }
            },
            "$set": {
                "updated_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )


async def load_last_messages(
    thread_id: str,
    limit: int = 10
):
    doc = await conversations().find_one(
        {"thread_id": thread_id},
        {
            "_id": 0,
            "messages": {"$slice": -limit}
        }
    )

    if not doc:
        return []

    return [
        {
            "role": m["role"],
            "content": m["content"]
        }
        for m in doc.get("messages", [])
    ]

