#!/usr/bin/env bash
# Start the MCP Server for the Business Card OCR System
# Usage: bash start_mcp.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Kill existing MCP server on port 8007
MCP_PORT=$(grep MCP_PORT .env 2>/dev/null | cut -d= -f2 || echo 8007)
EXISTING_PID=$(lsof -t -i:"$MCP_PORT" 2>/dev/null || true)
if [[ -n "$EXISTING_PID" ]]; then
    echo "Stopping existing MCP server (PID: $EXISTING_PID)..."
    kill "$EXISTING_PID" 2>/dev/null || true
    sleep 1
fi

echo "Starting MCP Server on port $MCP_PORT..."
nohup python server.py > mcp_server.log 2>&1 &
echo "MCP Server started (PID: $!)"
echo "Log: $SCRIPT_DIR/mcp_server.log"
