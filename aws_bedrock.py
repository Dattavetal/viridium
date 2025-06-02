import json
import os
from typing import List, Dict, Optional

import boto3
from dotenv import load_dotenv

load_dotenv()

# ── Load your Bedrock credentials & model ID from environment variables  ──
AWS_REGION = os.getenv("AWS_REGION")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID")
ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

# ── Initialize a Bedrock client via boto3 ──
# * Make sure your ~/.aws/credentials or environment variables are correctly set,
#   or else boto3 will raise authentication errors.
client = boto3.client('bedrock-runtime',
                      region_name=AWS_REGION,
                      aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)


def chat(prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Send a chat‐style prompt + optional conversation history to Claude 3 Haiku
    on Bedrock, then return the assistant’s reply text.

    This version collapses any consecutive messages of the same role so that
    roles alternate (user → assistant → user → …).
    """

    if history is None:
        history = []

    # Append the new user message
    combined = history + [{"role": "user", "content": prompt}]

    # Step 1: Collapse same‐role runs so that roles alternate
    filtered: List[Dict[str, str]] = []
    prev_role: Optional[str] = None

    for msg in combined:
        role = msg.get("role")
        if role != prev_role:
            filtered.append(msg)
            prev_role = role
        # if role == prev_role, skip this message (drop consecutive user/user or assistant/assistant)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": filtered,
        "max_tokens": 600,
        "temperature": 0.2
    }
    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8")
    )

    data = json.loads(response["body"].read())
    try:
        return data["content"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Bedrock response format: {json.dumps(data)}")
