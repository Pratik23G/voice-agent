import os
import sys
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY: str = os.getenv("VAPI_API_KEY", "")
VAPI_PHONE_NUMBER_ID: str = os.getenv("VAPI_PHONE_NUMBER_ID", "")
TARGET_PHONE_NUMBER: str = os.getenv("TARGET_PHONE_NUMBER", "+18054398008")
DEEPGRAM_API_KEY: str | None = os.getenv("DEEPGRAM_API_KEY")
LLM_API_KEY: str | None = os.getenv("LLM_API_KEY")

VAPI_BASE_URL = "https://api.vapi.ai"

RECORDINGS_DIR = "recordings"
TRANSCRIPTS_DIR = "transcripts"


def require_env() -> None:
    missing = [k for k, v in {
        "VAPI_API_KEY": VAPI_API_KEY,
        "VAPI_PHONE_NUMBER_ID": VAPI_PHONE_NUMBER_ID,
    }.items() if not v]
    if missing:
        print(f"Error: missing required env vars: {', '.join(missing)}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your Vapi credentials.", file=sys.stderr)
        sys.exit(1)
