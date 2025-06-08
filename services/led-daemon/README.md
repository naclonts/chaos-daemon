# LED Daemon

Evokes random signals to LEDs. Exposed as a MCP Model Context Protocol server.

Assumes a specific Raspberry Pi 5 + wiring setup.

## Run manually

To run the server directly:

```py
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```
