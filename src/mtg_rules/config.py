from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "MTG Rules Assistant"
    scryfall_base_url: str = "https://api.scryfall.com"


settings = Settings()
