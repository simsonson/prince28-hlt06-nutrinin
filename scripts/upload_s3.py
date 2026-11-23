"""Upload data/raw/ to the configured Supabase S3-compatible bucket."""

import os
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing {name} in .env")
    return value


def main() -> int:
    load_dotenv()
    client = boto3.client(
        "s3",
        endpoint_url=required("SUPABASE_S3_ENDPOINT"),
        aws_access_key_id=required("SUPABASE_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=required("SUPABASE_S3_SECRET_ACCESS_KEY"),
        region_name=required("SUPABASE_S3_REGION"),
        config=Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=60,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )
    bucket = required("SUPABASE_STORAGE_BUCKET")
    root = Path("data/raw")
    files = [path for path in root.rglob("*") if path.is_file() and path.name != ".measured.json"]
    transfer = TransferConfig(use_threads=False, multipart_threshold=100 * 1024 * 1024)
    total_bytes = 0
    for path in files:
        key = path.as_posix()
        size = path.stat().st_size
        try:
            remote = client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey"}:
                raise
            remote = None
        if remote and remote.get("ContentLength") == size:
            print(f"verified {key}", flush=True)
        else:
            client.upload_file(str(path), bucket, key, Config=transfer)
            verified = client.head_object(Bucket=bucket, Key=key)
            if verified.get("ContentLength") != size:
                raise RuntimeError(f"size mismatch after upload: {key}")
            print(f"uploaded {key}", flush=True)
        total_bytes += size
    print(f"uploaded={len(files)} bytes={total_bytes} bucket={bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
