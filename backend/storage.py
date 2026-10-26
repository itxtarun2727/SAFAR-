"""
storage.py — Pluggable Storage Backend Interface for Ephemeral Hosting.

Provides two storage implementations:
1. DatabaseStorageBackend (default for demo / Render ephemeral containers, stores in bytea)
2. S3StorageBackend (for S3-compatible cloud object stores via S3_BUCKET env config)
"""

from abc import ABC, abstractmethod
import os
from typing import Optional, Any


class StorageBackend(ABC):
    """Abstract storage interface for document artifacts."""

    @abstractmethod
    def save(self, storage_key: str, data: bytes, content_type: str = "application/pdf", doc: Any = None) -> str:
        """Save file data under storage_key and return location identifier."""
        pass

    @abstractmethod
    def get(self, storage_key: str, doc: Any = None) -> Optional[bytes]:
        """Retrieve file bytes for storage_key."""
        pass


class DatabaseStorageBackend(StorageBackend):
    """
    Stores documents directly in the database (PostgreSQL bytea / LargeBinary).
    Survives container restarts and redeployments on ephemeral platforms like Render.
    """

    def save(self, storage_key: str, data: bytes, content_type: str = "application/pdf", doc: Any = None) -> str:
        if doc is not None:
            doc.file_data = data
        return f"db://{storage_key}"

    def get(self, storage_key: str, doc: Any = None) -> Optional[bytes]:
        if doc and hasattr(doc, "file_data") and doc.file_data is not None:
            return bytes(doc.file_data)
        return None


class S3StorageBackend(StorageBackend):
    """
    Stores documents in an S3-compatible bucket (AWS S3, MinIO, Cloudflare R2).
    Configured via S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ENDPOINT_URL.
    """

    def __init__(self, bucket_name: str, endpoint_url: Optional[str] = None):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url or os.getenv("AWS_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
        return self._client

    def save(self, storage_key: str, data: bytes, content_type: str = "application/pdf", doc: Any = None) -> str:
        client = self._get_client()
        clean_key = storage_key.replace("s3://", "").lstrip("/")
        client.put_object(
            Bucket=self.bucket_name,
            Key=clean_key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self.bucket_name}/{clean_key}"

    def get(self, storage_key: str, doc: Any = None) -> Optional[bytes]:
        client = self._get_client()
        clean_key = storage_key.replace(f"s3://{self.bucket_name}/", "").replace("s3://", "").lstrip("/")
        res = client.get_object(Bucket=self.bucket_name, Key=clean_key)
        return res["Body"].read()


def get_storage() -> StorageBackend:
    """Factory selecting storage backend based on environment configuration."""
    backend_type = os.getenv("STORAGE_BACKEND", "database").lower()
    s3_bucket = os.getenv("S3_BUCKET")
    if backend_type == "s3" and s3_bucket:
        endpoint = os.getenv("AWS_ENDPOINT_URL")
        return S3StorageBackend(bucket_name=s3_bucket, endpoint_url=endpoint)
    return DatabaseStorageBackend()


storage = get_storage()
