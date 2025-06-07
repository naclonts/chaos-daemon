from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
import board
import busio
from adafruit_pca9685 import PCA9685
import time
import os
from typing import Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize I2C and PCA9685
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50  # 50Hz for servos

# LED channels
LED1 = pca.channels[2]  # Green
LED2 = pca.channels[3]  # Red

def set_led(chan, bright: float):
    """Set LED brightness (0.0 to 1.0)"""
    bright = max(0.0, min(bright, 1.0))
    chan.duty_cycle = int(bright * 65_535)

app = FastAPI(title="LED Daemon MCP Server")
mcp = FastMCP("led_daemon")

@mcp.tool()
def set_led_pattern(pattern: str, parameters: Dict[str, str] = None) -> str:
    """
    Set the LED pattern with optional parameters.
    Args:
        pattern: Name of the pattern to run (chaos_wave, void_pulse, cosmic_spiral, eldritch_flicker)
        parameters: Optional parameters for the pattern
    Returns:
        A string describing the result
    """
    logger.info(f"Received request to set LED pattern: {pattern}")

    patterns = {
        "chaos_wave": _chaos_wave,
        "void_pulse": _void_pulse,
        "cosmic_spiral": _cosmic_spiral,
        "eldritch_flicker": _eldritch_flicker
    }

    if pattern not in patterns:
        logger.error(f"Unknown pattern requested: {pattern}")
        return f"Unknown pattern: {pattern}"

    try:
        logger.info(f"Executing pattern: {pattern}")
        patterns[pattern](parameters or {})
        logger.info(f"Successfully executed pattern: {pattern}")
        return f"Pattern {pattern} activated successfully"
    except Exception as e:
        logger.error(f"Error running pattern {pattern}: {str(e)}", exc_info=True)
        return f"Error running pattern {pattern}: {str(e)}"

@mcp.tool()
def get_current_pattern() -> str:
    """
    Get the current LED pattern state.
    Returns:
        A string describing the current pattern state
    """
    logger.info("Received request for current pattern state")
    return "LED is currently running the last set pattern"

def _chaos_wave(parameters: Dict[str, str]):
    """Implement chaos wave pattern"""
    logger.info("Running chaos wave pattern")
    for led in (LED1, LED2):
        for i in range(101):
            set_led(led, i / 100.0)
            time.sleep(0.01)
        for i in range(100, -1, -1):
            set_led(led, i / 100.0)
            time.sleep(0.01)

def _void_pulse(parameters: Dict[str, str]):
    """Implement void pulse pattern"""
    logger.info("Running void pulse pattern")
    for _ in range(5):
        for led in (LED1, LED2):
            set_led(led, 1.0)
        time.sleep(0.2)
        for led in (LED1, LED2):
            set_led(led, 0.0)
        time.sleep(0.2)

def _cosmic_spiral(parameters: Dict[str, str]):
    """Implement cosmic spiral pattern"""
    logger.info("Running cosmic spiral pattern")
    for i in range(0, 101, 2):
        set_led(LED1, i / 100.0)
        set_led(LED2, (100 - i) / 100.0)
        time.sleep(0.05)

def _eldritch_flicker(parameters: Dict[str, str]):
    """Implement eldritch flicker pattern"""
    logger.info("Running eldritch flicker pattern")
    for _ in range(10):
        for led in (LED1, LED2):
            set_led(led, 1.0)
            time.sleep(0.1)
            set_led(led, 0.0)
            time.sleep(0.1)

# Mount the MCP server at /sse endpoint
app.mount("/sse", mcp.sse_app())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting LED daemon MCP server on port {port}")

    # Initialize LEDs with a startup pattern
    logger.info("Running startup pattern")
    try:
        # Quick pulse on both LEDs
        for _ in range(2):
            for led in (LED1, LED2):
                set_led(led, 1.0)
            time.sleep(0.1)
            for led in (LED1, LED2):
                set_led(led, 0.0)
            time.sleep(0.1)

        # Fade up green, then red
        for i in range(101):
            set_led(LED1, i / 100.0)
            time.sleep(0.01)
        for i in range(101):
            set_led(LED2, i / 100.0)
            time.sleep(0.01)

        # Fade both down
        for i in range(100, -1, -1):
            set_led(LED1, i / 100.0)
            set_led(LED2, i / 100.0)
            time.sleep(0.01)

        logger.info("Startup pattern complete")
    except Exception as e:
        logger.error(f"Error during startup pattern: {str(e)}", exc_info=True)

    uvicorn.run(app, host="0.0.0.0", port=port)