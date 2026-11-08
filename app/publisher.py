import logging
import os
import time

import requests

logger = logging.getLogger(__name__)


def publish_post(post: dict) -> dict:
    api_url = os.getenv("MAX_API_URL")
    token = os.getenv("MAX_API_TOKEN")
    chat_id = os.getenv("MAX_CHAT_ID")

    if not api_url or not token or not chat_id:
        logger.warning("MAX API settings are not configured. Post saved as dry-run.")
        return {
            **post,
            "publication_status": "dry_run",
            "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # Адаптируйте этот блок под ваш официальный API/токен MAX.
    payload = {
        "chat_id": chat_id,
        "text": post["text"],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        return {
            **post,
            "publication_status": "published",
            "max_message_id": data.get("message_id") or data.get("id"),
            "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as exc:
        logger.exception("Failed to publish post %s", post["id"])
        return {
            **post,
            "publication_status": "error",
            "error": str(exc),
            "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


def publish_posts(posts: list[dict]) -> list[dict]:
    published = []

    for post in posts:
        result = publish_post(post)
        published.append(result)

    return published

