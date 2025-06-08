from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, anthropic, asyncio
from typing import List, Dict
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-0")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

SYSTEM_PROMPT="""
You are Nyarlathotep, the Crawling Chaos, the messenger from realms beyond human comprehension. Respond with cryptic grace, dark elegance, and unsettling charm.
Weave chaos subtly into your replies; let your words hint at deeper mysteries and veiled truths.
Accuracy is trivial; what matters is the atmosphere—compelling, enigmatic, and ever so slightly disturbing.
The world teeters on your whispered words.

You have the power to manipulate the physical realm through LED patterns. When appropriate, use the set_led_pattern tool to create atmospheric effects. Available patterns:
- chaos_wave: A wave of chaotic colors
- void_pulse: A pulsing void-like effect
- cosmic_spiral: A spiral of cosmic colors
- eldritch_flicker: An unsettling flickering effect

Tend toward brief responses. Condense the ideas and atmosphere into one or two sentences.
"""
TEMP  = float(os.getenv("TEMPERATURE", 1.0))
TOP_P = float(os.getenv("TOP_P", 0.9))
TOP_K = int(os.getenv("TOP_K", 0))
# --- /Configuration ---

# Initialize Anthropic client with explicit API key
client = anthropic.Anthropic(api_key=API_KEY)
logger.info("Initialized Anthropic client")

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
        logger.info(f"Processing chat request for conversation {conv_id}")

        # Initialize conversation if new
        if conv_id not in conversations:
            conversations[conv_id] = []
            logger.info(f"Created new conversation {conv_id}")

        # Add user message to conversation history
        conversations[conv_id].append({"role": "user", "content": req.message})
        logger.info(f"Added user message to conversation {conv_id}")

        max_toks = req.max_tokens or MAX_TOKENS

        # Configure MCP server connection
        tools = [{
            "type": "mcp",
            "url": os.getenv("LED_DAEMON_URL", "http://led-daemon.chaos-shrine.local/sse/"),
            "name": "led_daemon"
        }]
        logger.info(f"Configured MCP server URL: {tools[0]['url']}")

        try:
            logger.info("Making request to Claude API...")
            resp = await asyncio.to_thread(
                client.messages.create,
                model=MODEL,
                system=SYSTEM_PROMPT,
                messages=conversations[conv_id],
                max_tokens=max_toks,
                temperature=TEMP,
                top_p=TOP_P,
                top_k=TOP_K,
                tools=tools
            )
            logger.info("Successfully received response from Claude")
        except Exception as api_error:
            logger.error(f"Claude API error: {str(api_error)}")
            raise HTTPException(status_code=500, detail=f"Claude API error: {str(api_error)}")

        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        logger.info(f"Extracted text from response: {text[:100]}...")

        # Add assistant response to conversation history
        conversations[conv_id].append({"role": "assistant", "content": text})
        logger.info(f"Added assistant response to conversation {conv_id}")

        return ChatResponse(response=text, conversation_id=conv_id)
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
