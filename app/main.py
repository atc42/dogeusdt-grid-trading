import logging
import os
import threading
import time
from typing import Literal

from fastapi import FastAPI, HTTPException

from .collector import collect_urls
from .processor import process_articles
from .publisher import publish_posts
from .storage import save_jsonl, load_state, save_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="News Pipeline MAX", version="0.1.0")

PIPELINE_LOCK = threading.Lock()
PIPELINE_STATUS = {
    "status": "idle",
    "last_started_at": None,
    "last_finished_at": None,
    "last_error": None,
    "last_result": None,
}


def get_sources() -> list[dict]:
    return [
        {
            "name": "example_source",
            "url": os.getenv("NEWS_SOURCE_URL", "https://example.com/news"),
            "css_selector": os.getenv("NEWS_CSS_SELECTOR", "article"),
            "link_selector": os.getenv("NEWS_LINK_SELECTOR", "a"),
            "title_selector": os.getenv("NEWS_TITLE_SELECTOR", "h2"),
        }
    ]


def run_pipeline_sync() -> dict:
    state = load_state()
    seen_hashes = set(state.get("seen_hashes", []))

    raw_articles = collect_urls(get_sources())
    save_jsonl("raw/articles.jsonl", raw_articles)

    processed = process_articles(raw_articles, seen_hashes)
    save_jsonl("processed/articles.jsonl", processed)

    published = publish_posts(processed)
    save_jsonl("published/posts.jsonl", published)

    new_hashes = [item["hash"] for item in processed]
    state["seen_hashes"] = list(set(state.get("seen_hashes", []) + new_hashes))
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_state(state)

    return {
        "raw_count": len(raw_articles),
        "processed_count": len(processed),
        "published_count": len([p for p in published if p.get("publication_status") == "published"]),
        "dry_run_count": len([p for p in published if p.get("publication_status") == "dry_run"]),
        "error_count": len([p for p in published if p.get("publication_status") == "error"]),
    }


def run_pipeline_background():
    def worker():
        with PIPELINE_LOCK:
            PIPELINE_STATUS.update(
                {
                    "status": "running",
                    "last_started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "last_error": None,
                }
            )

            try:
                result = run_pipeline_sync()
                PIPELINE_STATUS.update(
                    {
                        "status": "success",
                        "last_finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "last_result": result,
                    }
                )
            except Exception as exc:
                logger.exception("Pipeline failed")
                PIPELINE_STATUS.update(
                    {
                        "status": "error",
                        "last_finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "last_error": str(exc),
                    }
                )

    threading.Thread(target=worker, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/pipeline/status")
def pipeline_status():
    return PIPELINE_STATUS


@app.post("/pipeline/run")
def pipeline_run(mode: Literal["background", "sync"] = "background"):
    if PIPELINE_STATUS["status"] == "running":
        raise HTTPException(status_code=409, detail="Pipeline is already running")

    if mode == "background":
        run_pipeline_background()
        return {"status": "started"}

    with PIPELINE_LOCK:
        PIPELINE_STATUS.update(
            {
                "status": "running",
                "last_started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "last_error": None,
            }
        )

        try:
            result = run_pipeline_sync()
            PIPELINE_STATUS.update(
                {
                    "status": "success",
                    "last_finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "last_result": result,
                }
            )
            return {"status": "success", "result": result}
        except Exception as exc:
            logger.exception("Pipeline failed")
            PIPELINE_STATUS.update(
                {
                    "status": "error",
                    "last_finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "last_error": str(exc),
                }
            )
            raise HTTPException(status_code=500, detail=str(exc))

