#!/bin/bash

set -e

PORT="${PORT:-8080}"

if [ "$ENABLE_TUNNEL" = "true" ]; then
  if [ -n "$TUNNEL_TOKEN" ]; then
    cloudflared tunnel --no-autoupdate run --token "$TUNNEL_TOKEN" &
  else
    # Temporary trycloudflare.com URL, printed in the logs 
    cloudflared tunnel --no-autoupdate --url "http://localhost:$PORT" &
  fi
fi

exec uvicorn aiphish.livewraith.main:app --port "$PORT" --host 0.0.0.0

