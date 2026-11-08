import json
import os

import boto3

BUCKET = os.getenv("S3_BUCKET", "news-pipeline-max")
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT", "https://s3.cloud.ru"),
    region_name=os.getenv("S3_REGION", "ru-central1"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
)


def save_jsonl(key: str, items: list[dict]):
    body = "
".join(json.dumps(item, ensure_ascii=False) for item in items)
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )


def load_state() -> dict:
    try:
        obj = s3.get_object(Bucket=BUCKET, Key="state/pipeline_state.json")
        return json.loads(obj["Body"].read().decode("utf-8"))
    except Exception:
        return {}


def save_state(state: dict):
    s3.put_object(
        Bucket=BUCKET,
        Key="state/pipeline_state.json",
        Body=json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

