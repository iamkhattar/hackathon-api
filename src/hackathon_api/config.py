from pydantic import BaseSettings


class Settings(BaseSettings):
    DB_CONNECTION_STRING: str


settings = Settings()
