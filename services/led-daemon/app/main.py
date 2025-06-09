import asyncio
import threading
from typing import Optional
import random
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import board
import busio
from adafruit_pca9685 import PCA9685
import time
import os
from typing import Dict
import logging
import uvicorn

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

# Initialize FastMCP server for LED tools
mcp = FastMCP("led_daemon")
logger.info("Initialized FastMCP server for LED daemon")

@mcp.tool()
def set_led_pattern(pattern: str, parameters: Optional[Dict[str, str]]) -> str:
    """
    Set the LED pattern with optional parameters.
    Args:
        pattern: Name of the pattern to run (chaos_wave, void_pulse, cosmic_spiral, eldritch_flicker)
        parameters: Optional parameters for the pattern
    Returns:
        A string describing the result
    """
    logger.info(f"Received request to set LED pattern: {pattern}")
    if pattern not in patterns:
        return f"Unknown pattern: {pattern}"
    pattern_queue.put_nowait((pattern, parameters or {}))
    logger.info("Queued pattern %s", pattern)
    return f"Pattern {pattern} queued"


@mcp.tool()
def get_current_pattern() -> str:
    return f"LEDs are currently running: {current_pattern_name}"

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

def _slow_pulse(parameters: Dict[str, str], *, stop_event: threading.Event):
    """Slow breathing pattern that exits early when stop_event is set."""
    while not stop_event.is_set():
        for led in (LED1, LED2):
            inc = random.randint(1, 5)
            for up in range(0, 101, inc):
                if stop_event.is_set(): return
                set_led(led, up / 100.0); time.sleep(0.05)
            dec = random.randint(1, 5)
            for down in range(100, -1, -dec):
                if stop_event.is_set(): return
                set_led(led, down / 100.0); time.sleep(0.05)


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")
    logger.info("Created SSE server transport")

    async def handle_sse(request: Request) -> None:
        logger.info("New SSE connection request received")
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            logger.info("SSE connection established, starting MCP server")
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
            logger.info("MCP server session completed")

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

# Create the Starlette app at module level
mcp_server = mcp._mcp_server  # noqa: WPS437
app = create_starlette_app(mcp_server, debug=True)

# Patterns of LED behavior
# TODO: move out of global scope
patterns = {
    "chaos_wave": _chaos_wave,
    "void_pulse": _void_pulse,
    "cosmic_spiral": _cosmic_spiral,
    "eldritch_flicker": _eldritch_flicker,
    "slow_pulse": _slow_pulse,
}

# run async process that constantly runs current_pattern
# queue carries (pattern_name, parameters) tuples
# maxsize=1 means “only care about the *latest* request”
pattern_queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()
idle_stop: threading.Event = threading.Event()   # tells slow_pulse to stop
current_pattern_name: str = "slow_pulse"

async def pattern_worker() -> None:
    """Worker that runs LED patterns based on requests in the queue."""
    global current_pattern_name, idle_stop

    idle_thread: threading.Thread | None = None

    while True:
        # ── 1. start idle animation when nothing is queued ─────────────
        if pattern_queue.empty() and (idle_thread is None or not idle_thread.is_alive()):
            idle_stop.clear()                                    # <-- ensure flag is down
            idle_thread = threading.Thread(
                target=_slow_pulse,
                args=({},),
                kwargs={"stop_event": idle_stop},
                daemon=True,
            )
            idle_thread.start()

        # ── 2. wait for next queued pattern ───────────────────────────
        pattern_name, params = await pattern_queue.get()

        # ── 3. interrupt idle immediately ─────────────────────────────
        idle_stop.set()                 # tell slow_pulse to exit
        if idle_thread and idle_thread.is_alive():
            idle_thread.join()          # wait until it’s really gone
        idle_thread = None              # forget the old thread
        idle_stop = threading.Event()   # <-- reset the flag object

        # ── 4. run the requested pattern (blocking, in worker thread) ─
        current_pattern_name = pattern_name
        await asyncio.to_thread(patterns[pattern_name], params)

        # loop resumes; if the queue is now empty, step 1 restarts idle



@app.on_event("startup")
async def _start_pattern_worker() -> None:
    asyncio.create_task(pattern_worker())


if __name__ == "__main__":
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
