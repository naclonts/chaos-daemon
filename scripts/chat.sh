#!/usr/bin/env bash
# Interactive shell client for the Chaos‑Brain (Nyarlathotep) service running in the
# local kind cluster on the Raspberry Pi 5.  Requires `jq` and Docker CLI.

set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "❌  jq is required but not installed.  Install it and try again." >&2
  exit 1
fi

# Allow overriding the control‑plane container name via env (handy if you renamed the cluster)
NODE_CONTAINER=${NODE_CONTAINER:-chaos-shrine-control-plane}

NODE_IP=$(docker container inspect "$NODE_CONTAINER" --format '{{ .NetworkSettings.Networks.kind.IPAddress }}')
URL="http://${NODE_IP}:31080/chat"

echo "💀  Talking Nyarlathotep at $URL"
echo "Type 'exit' or press Ctrl‑D to quit."

# Initialize conversation ID
CONV_ID=""

# REPL loop
while printf "> " && read -r MSG; do
  [[ "$MSG" == "exit" ]] && break
  # Build JSON body with jq so we handle escaping correctly
  BODY=$(jq -n --arg message "$MSG" --arg conv_id "$CONV_ID" '{message:$message, conversation_id:$conv_id}')
  RESP=$(curl -s -X POST "$URL" -H 'Content-Type: application/json' -d "$BODY")
  # Update conversation ID from response
  CONV_ID=$(echo "$RESP" | jq -r '.conversation_id')
  echo -e "\033[0;32m$(echo "$RESP" | jq -r '.response')\033[0m"
done

