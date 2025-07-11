# storage.py
from azure.storage.blob import BlobServiceClient
from settings import Settings
from fastapi import HTTPException

settings = Settings()

_blob_svc: BlobServiceClient | None = None

def get_blob_service_client() -> BlobServiceClient:
    global _blob_svc
    if not _blob_svc:
        conn = settings.AZURE_STORAGE_CONNECTION_STRING
        if not conn:
            raise HTTPException(500, "AZURE_STORAGE_CONNECTION_STRING not configured")
        _blob_svc = BlobServiceClient.from_connection_string(conn)
    return _blob_svc

def get_container_client():
    svc = get_blob_service_client()
    return svc.get_container_client(settings.BLOB_CONTAINER)
