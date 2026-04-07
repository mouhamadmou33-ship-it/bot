import re
import time
from urllib.parse import urlparse
from typing import Optional

# Rate limiting: simple in-memory dict, key=user_id, value=last_request_time
rate_limit_store = {}
RATE_LIMIT_SECONDS = 10  # Allow one request every 10 seconds per user


def is_valid_url(url: str) -> bool:
    """Validate if the URL is a valid HTTP/HTTPS URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except:
        return False


def detect_platform(url: str) -> Optional[str]:
    """Detect the platform from the URL."""
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "facebook.com" in url or "fb.com" in url:
        return "facebook"
    return None


def is_rate_limited(user_id: int) -> bool:
    """Check if the user is rate limited."""
    now = time.time()
    last_time = rate_limit_store.get(user_id, 0)
    if now - last_time < RATE_LIMIT_SECONDS:
        return True
    rate_limit_store[user_id] = now
    return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    return re.sub(r'[<>:"/\\|?*]', "_", filename)
