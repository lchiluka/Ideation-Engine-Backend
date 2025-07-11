# settings.py
from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    DATABASE_URL: AnyUrl
    AZURE_STORAGE_CONNECTION_STRING: str
    BLOB_CONTAINER: str = "my-container"    # default container name

    class Config:
        env_file = ".env"      # for local dev
        env_file_encoding = "utf-8"
