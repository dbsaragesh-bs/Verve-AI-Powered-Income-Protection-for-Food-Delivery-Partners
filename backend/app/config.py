from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "VERVE Backend"
    database_url: str = Field(
        default="postgresql+asyncpg://verve:verve123@localhost:5432/verve",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    sim_weather_url: str = Field(
        default="http://localhost:8001", alias="SIM_WEATHER_URL"
    )
    sim_traffic_url: str = Field(
        default="http://localhost:8002", alias="SIM_TRAFFIC_URL"
    )
    sim_platform_url: str = Field(
        default="http://localhost:8003", alias="SIM_PLATFORM_URL"
    )
    sim_social_url: str = Field(default="http://localhost:8004", alias="SIM_SOCIAL_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
