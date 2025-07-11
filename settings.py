# settings.py
from pydantic_settings import BaseSettings    # now comes from a separate package
from pydantic.networks import AnyUrl          # URL types still in pydantic.networks
class Settings(BaseSettings):
    DATABASE_URL: AnyUrl
    AZURE_STORAGE_CONNECTION_STRING: str
    BLOB_CONTAINER: str = "my-container"    # default container name

    class Config:
        env_file = ".env"      # for local dev
        env_file_encoding = "utf-8"
