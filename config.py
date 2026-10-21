import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_env(key: str, default: str = "", *aliases: str) -> str:
    for env_key in (key, *aliases):
        value = os.getenv(env_key)
        if value is not None and value.strip() != "":
            return value.strip()
    return default


FLASK_SECRET_KEY = get_env("FLASK_SECRET_KEY", "ai-car-concept-lab-dev-key")
GROQ_API_KEY = get_env("GROQ_API_KEY")
GROQ_MODEL = get_env("GROQ_MODEL", "openai/gpt-oss-120b")
HCAPTCHA_SITE_KEY = get_env("HCAPTCHA_SITE_KEY")
HCAPTCHA_SECRET_KEY = get_env("HCAPTCHA_SECRET_KEY", "", "HCAPTCHA_SECRET")
HF_API_KEY = get_env("HF_API_KEY", "", "HF_TOKEN", "HUGGINGFACE_API_KEY")
SESSION_FILE_DIR = get_env("SESSION_FILE_DIR", str(BASE_DIR / ".flask_session"))


def get_port(default: int = 5000) -> int:
    for key in ("APP_PORT", "PORT"):
        value = os.getenv(key, "").strip()
        if value.isdigit() and int(value) > 0:
            return int(value)
    return default


PORT = get_port()
