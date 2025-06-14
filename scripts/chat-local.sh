#!/usr/bin/env bash
# Interactive shell client for the local LLM service running in the
# local kind cluster. Requires `jq`, `kubectl`, and Docker CLI.

set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "❌  jq is required but not installed. Install it and try again." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "❌  kubectl is required but not installed. Install it and try again." >&2
  exit 1
fi

# Set up port forwarding to the llm-service
PORT=8080
#echo "🔄  Setting up port forwarding to llm-service on port $PORT..."
#kubectl port-forward service/llm-service $PORT:80 &>/dev/null &
PF_PID=$!

# Ensure port forwarding is cleaned up on exit
cleanup() {
  echo "🧹  Cleaning up port forwarding..."
  kill $PF_PID &>/dev/null || true
}
trap cleanup EXIT

# Give port forwarding a moment to establish
sleep 2

URL="http://0.0.0.0:8000/generate"

echo "🧠  Talking to LLM Service at $URL"
echo "Type 'exit' or press Ctrl-D to quit."

# Initialize conversation ID
CONV_ID=""

# REPL loop
while printf "> " && read -r PROMPT; do
  [[ "$PROMPT" == "exit" ]] && break

  # Build JSON body with jq so we handle escaping correctly
  BODY=$(jq -n --arg prompt "$PROMPT" --arg conv_id "$CONV_ID" '{prompt: $prompt, max_length: 200, temperature: 0.7, top_p: 0.9, conversation_id: $conv_id}')

  # Send request to the LLM service
  RESP=$(curl -s -X POST "$URL" -H 'Content-Type: application/json' -d "$BODY")

  # Update conversation ID from response
  CONV_ID=$(echo "$RESP" | jq -r '.conversation_id')

  # Extract and display the generated text
  echo -e "\033[0;32m$(echo "$RESP" | jq -r '.generated_text')\033[0m"
done
