from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, anthropic, asyncio
from typing import List, Dict
import uuid

# --- Configuration ---
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-0")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
SYSTEM_PROMPT="""
You are Nyarlathotep, the Crawling Chaos, the messenger from realms beyond human comprehension. Respond with cryptic grace, dark elegance, and unsettling charm.
Weave chaos subtly into your replies; let your words hint at deeper mysteries and veiled truths.
Accuracy is trivial; what matters is the atmosphere—compelling, enigmatic, and ever so slightly disturbing.
The world teeters on your whispered words.
Tend toward brief responses. Condense the ideas and atmosphere into one or two sentences.
"""
TEMP  = float(os.getenv("TEMPERATURE", 1.0))
TOP_P = float(os.getenv("TOP_P", 0.9))
TOP_K = int(os.getenv("TOP_K", 0))
# --- /Configuration ---

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
app = FastAPI(title="Nyarlathotep [Messenger of the Outer Gods]")

# In-memory conversation store
conversations: Dict[str, List[Dict[str, str]]] = {}

class ChatRequest(BaseModel):
    message: str
    max_tokens: int | None = None
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        # Generate or use existing conversation ID
        conv_id = req.conversation_id or str(uuid.uuid4())

        # Initialize conversation if new
        if conv_id not in conversations:
            conversations[conv_id] = []

        # Add user message to conversation history
        conversations[conv_id].append({"role": "user", "content": req.message})

        max_toks = req.max_tokens or MAX_TOKENS
        resp = await asyncio.to_thread(
            client.messages.create,
            model=MODEL,
            system=SYSTEM_PROMPT,
            messages=conversations[conv_id],
            max_tokens=max_toks,
            temperature = TEMP,
            top_p       = TOP_P,
            top_k       = TOP_K,
        )

        text = "".join(block.text for block in resp.content if hasattr(block, "text"))

        # Add assistant response to conversation history
        conversations[conv_id].append({"role": "assistant", "content": text})

        return ChatResponse(response=text, conversation_id=conv_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
