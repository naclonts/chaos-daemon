from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import grpc
import re
import xml.etree.ElementTree as ET
from typing import Optional, Dict
import os

# Import generated gRPC code (you'll need to generate this)
from led_control_pb2 import LedStateRequest, GetLedStateRequest
from led_control_pb2_grpc import LedControlStub

app = FastAPI(title="MCP Handler")

# gRPC client setup
LED_DAEMON_ADDRESS = os.getenv("LED_DAEMON_ADDRESS", "led-daemon:50051")
channel = grpc.insecure_channel(LED_DAEMON_ADDRESS)
led_stub = LedControlStub(channel)

class MCPRequest(BaseModel):
    message: str
    conversation_id: str

class MCPResponse(BaseModel):
    led_command: Optional[Dict] = None
    message: str

def extract_mcp_commands(text: str) -> Optional[Dict]:
    """Extract MCP commands from text using regex."""
    mcp_pattern = r'<MCP>(.*?)</MCP>'
    match = re.search(mcp_pattern, text, re.DOTALL)
    if not match:
        return None

    try:
        mcp_content = match.group(1)
        root = ET.fromstring(f"<root>{mcp_content}</root>")
        led_pattern = root.find(".//LED_PATTERN")

        if led_pattern is None:
            return None

        pattern_name = led_pattern.find("pattern_name").text
        parameters = {}
        params_elem = led_pattern.find("parameters")
        if params_elem is not None:
            for param in params_elem:
                parameters[param.tag] = param.text

        return {
            "pattern": pattern_name,
            "parameters": parameters
        }
    except Exception as e:
        print(f"Error parsing MCP command: {e}")
        return None

@app.post("/process", response_model=MCPResponse)
async def process_mcp(req: MCPRequest):
    try:
        # Extract MCP commands from the message
        led_command = extract_mcp_commands(req.message)

        if led_command:
            # Send command to LED daemon
            request = LedStateRequest(
                pattern=led_command["pattern"],
                parameters=led_command["parameters"]
            )
            response = led_stub.SetLedState(request)

            return MCPResponse(
                led_command=led_command,
                message=f"LED pattern '{led_command['pattern']}' activated"
            )

        return MCPResponse(message="No MCP commands found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))