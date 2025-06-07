from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP
import RPi.GPIO as GPIO
import time
import os
from typing import Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LED configuration
LED_PIN = int(os.getenv("LED_PIN", "18"))
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pwm = GPIO.PWM(LED_PIN, 1000)  # 1000 Hz frequency
pwm.start(0)

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
    for i in range(100):
        pwm.ChangeDutyCycle(i)
        time.sleep(0.01)
    for i in range(100, -1, -1):
        pwm.ChangeDutyCycle(i)
        time.sleep(0.01)

def _void_pulse(parameters: Dict[str, str]):
    """Implement void pulse pattern"""
    logger.info("Running void pulse pattern")
    for _ in range(5):
        pwm.ChangeDutyCycle(100)
        time.sleep(0.2)
        pwm.ChangeDutyCycle(0)
        time.sleep(0.2)

def _cosmic_spiral(parameters: Dict[str, str]):
    """Implement cosmic spiral pattern"""
    logger.info("Running cosmic spiral pattern")
    for i in range(0, 100, 2):
        pwm.ChangeDutyCycle(i)
        time.sleep(0.05)

def _eldritch_flicker(parameters: Dict[str, str]):
    """Implement eldritch flicker pattern"""
    logger.info("Running eldritch flicker pattern")
    for _ in range(10):
        pwm.ChangeDutyCycle(100)
        time.sleep(0.1)
        pwm.ChangeDutyCycle(0)
        time.sleep(0.1)

# Mount the MCP server at /sse endpoint
app.mount("/sse", mcp.app)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting LED daemon MCP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)