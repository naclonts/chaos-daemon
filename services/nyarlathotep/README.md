# Nyarlathotep

> The Messenger of the Outer Gods

Communicates with an LLM server, allowing users to chat in.

Will make MCP calls within cluster.

## Run manually

To run the Python app via the command line:

```sh
LED_DAEMON_URL=http://0.0.0.0:8010/sse uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

From another terminal:

```sh
curl -X POST localhost:8090/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello, Nyarlathotep. Could you do some eldritch LED patterns?"}'
```
