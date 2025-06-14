from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, anthropic
from typing import List, Dict, Optional
import uuid
import logging
from mcp import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack

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

You have the power to manipulate the physical realm through LED patterns. Use the set_led_pattern tool to create atmospheric effects.
You use MCP (Model Context Protocol) to interact with the tools and services.

You run on a Raspberry Pi 5 in a Kubernetes cluster called chaos-shrine.

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

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self._streams_context = None
        self._session_context = None

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        logger.info(f"Connecting to SSE server at {server_url}")
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session = await self._session_context.__aenter__()

        # Initialize
        await self.session.initialize()
        logger.info("SSE client initialized")

        # List available tools to verify connection
        response = await self.session.list_tools()
        tools = response.tools
        logger.info(f"Connected to server with tools: {[tool.name for tool in tools]}")

    async def cleanup(self):
        """Properly clean up the session and streams"""
        logger.info("Cleaning up MCP client resources")
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        logger.info("Processing query with Claude and MCP tools")
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
            system=SYSTEM_PROMPT,
            tools=available_tools,
            temperature=TEMP,
            top_p=TOP_P,
            top_k=TOP_K
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                logger.info(f"Calling tool {tool_name} with args {tool_args}")
                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Called tool {tool_name} with {tool_args}]")

                # Continue conversation with tool results
                if hasattr(content, 'text') and content.text:
                    messages.append({
                        "role": "assistant",
                        "content": content.text
                    })
                messages.append({
                    "role": "user",
                    "content": result.content
                })

                # Get next response from Claude
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    messages=messages,
                    system=SYSTEM_PROMPT,
                    temperature=TEMP,
                    top_p=TOP_P,
                    top_k=TOP_K
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

# Global MCP client instance
mcp_client = MCPClient()

@app.on_event("startup")
async def startup_event():
    """Initialize MCP client on startup"""
    try:
        led_daemon_url = os.getenv("LED_DAEMON_URL", "http://led-daemon.chaos-shrine.local/sse")
        logger.info(f"Connecting to LED daemon at {led_daemon_url}")
        await mcp_client.connect_to_sse_server(led_daemon_url)
    except Exception as e:
        logger.error(f"Failed to connect to LED daemon: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up MCP client on shutdown"""
    await mcp_client.cleanup()

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

        try:
            logger.info("Processing query with MCP client")
            text = await mcp_client.process_query(req.message)
            logger.info(f"Successfully processed query, response length: {len(text)}")
        except Exception as api_error:
            logger.error(f"MCP client error: {str(api_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"MCP client error: {str(api_error)}")

        # Add assistant response to conversation history
        conversations[conv_id].append({"role": "assistant", "content": text})
        logger.info(f"Added assistant response to conversation {conv_id}")

        return ChatResponse(response=text, conversation_id=conv_id)
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
