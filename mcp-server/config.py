"""MCP Server configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the mcp-server directory
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(_ENV_PATH)

MCP_PORT: int = int(os.getenv("MCP_PORT", "8007"))

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8006")
BACKEND_USERNAME: str = os.getenv("BACKEND_USERNAME", "")
BACKEND_PASSWORD: str = os.getenv("BACKEND_PASSWORD", "")

PROJECT_DIR: str = os.getenv("PROJECT_DIR", "/data1/165/ocr_v2/manage_card")
