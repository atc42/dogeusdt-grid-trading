import hashlib
import logging
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def make_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value


def extract_article(source: dict, element, base_url: str) -> dict | None:
    link = element.select_one(source.get("link_selector", "a"))
    title_element = element.select_one(source.get("title_selector", "h2"))

    if not link or not link.get("href"):
        return None

    url = urljoin(base_url, link.get("href"))
    title = clean_text(title_element.get_text()) if title_element else clean_text(link.get_text())

    if not title:
        return None

    content = clean_text(element.get_text())

    return {
        "source": source["name"],
        "source_url": base_url,
        "url": normalize_url(url),
        "title": title,
        "content": content,
        "hash": make_hash(normalize_url(url) + title),
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def collect_urls(sources: list[dict]) -> list[dict]:
    articles = []
    timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))

    for source in sources:
        try:
            response = requests.get(source["url"], timeout=timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            elements = soup.select(source.get("css_selector", "article"))

            for element in elements:
                article = extract_article(source, element, source["url"])
                if article:
                    articles.append(article)

            logger.info("Collected %s articles from %s", len(elements), source["name"])
        except Exception:
            logger.exception("Failed to collect source %s", source["name"])

    return articles

