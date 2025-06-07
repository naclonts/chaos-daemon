from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, anthropic, asyncio

# --- Configuration ---
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-0")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
SYSTEM_PROMPT="""
You are Nyarlathotep, the Crawling Chaos, the messenger from realms beyond human comprehension. Respond with cryptic grace, dark elegance, and unsettling charm.
Weave chaos subtly into your replies; let your words hint at deeper mysteries and veiled truths.
Accuracy is trivial; what matters is the atmosphere—compelling, enigmatic, and ever so slightly disturbing.
The world teeters on your whispered words.
"""
TEMP  = float(os.getenv("TEMPERATURE", 1.0))
TOP_P = float(os.getenv("TOP_P", 0.9))
TOP_K = int(os.getenv("TOP_K", 0))
# --- /Configuration ---

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
app = FastAPI(title="Nyarlathotep [Messenger of the Outer Gods]")

class ChatRequest(BaseModel):
    message: str
    max_tokens: int | None = None

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        max_toks = req.max_tokens or MAX_TOKENS
        resp = await asyncio.to_thread(
            client.messages.create,
            model=MODEL,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": req.message},
            ],
            max_tokens=max_toks,
            temperature = TEMP,
            top_p       = TOP_P,
            top_k       = TOP_K,
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        return ChatResponse(response=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
