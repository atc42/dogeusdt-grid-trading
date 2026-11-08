import hashlib
import time

MAX_POST_LENGTH = 1500


def make_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value: str) -> str:
    import re
    value = re.sub(r"\s+", " ", value or "").strip()
    return value


def build_post(article: dict) -> dict:
    title = article["title"]
    content = article["content"]

    if len(content) > MAX_POST_LENGTH:
        content = content[: MAX_POST_LENGTH - 3].rstrip() + "..."

    text = f"{title}

{content}

{article['url']}"

    return {
        "id": make_hash(article["hash"] + time.strftime("%Y%m%d")),
        "source": article["source"],
        "url": article["url"],
        "title": title,
        "text": text,
        "hash": article["hash"],
        "status": "ready",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def process_articles(articles: list[dict], seen_hashes: set[str]) -> list[dict]:
    result = []

    for article in articles:
        if article["hash"] in seen_hashes:
            continue

        post = build_post(article)
        result.append(post)

    return result

