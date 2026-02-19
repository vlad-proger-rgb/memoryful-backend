import os
from dotenv import load_dotenv

load_dotenv()

MEMORYFUL_API_BASE_URL = os.getenv("MEMORYFUL_API_BASE_URL", "")

MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "3001"))
