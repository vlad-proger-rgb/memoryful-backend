import os
from dotenv import load_dotenv

load_dotenv()

MEMORYFUL_API_BASE_URL = os.getenv("MEMORYFUL_API_BASE_URL", "")
