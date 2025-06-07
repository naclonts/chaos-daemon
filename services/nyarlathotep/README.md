# Nyarlathotep

> The Messenger of the Outer Gods

Communicates with an LLM server, allowing users to chat in.

Will make MCP calls within cluster.

## Run manually

To run the Python app via the command line:

```sh
uvicorn app.main:app --host 0.0.0.0 --port 8086
```

From another terminal:

```sh
curl -X POST localhost:8086/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello, Nyarlathotep"}'

