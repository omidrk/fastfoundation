import logging
from os import environ
from random import randint
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class GlobalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENVIRONMENT: str = "development"
    # app settings
    ALLOWED_ORIGINS: str = (
        "http://127.0.0.1:3000,http://localhost:3000,http://localhost:5556/dex,http://127.0.0.1:5556"
    )

    # Logging
    LOG_LEVEL: int = logging.DEBUG

    OIDC_URL: str = (
        "http://localhost:5556/dex"  # Adjust this URL based on your Dex deployment
    )
    CLIENT_SECRET: str = ""
    CLIENT_ID: str = "my-app"

    @computed_field
    @property
    def OIDC_CONFIG_URL(self) -> str:
        return f"{self.OIDC_URL}/.well-known/openid-configuration"

    # user status
    SECONDS_TO_SEND_USER_STATUS: int = 60


class TestSettings(GlobalSettings):
    DB_SCHEMA: str = f"test_{randint(1, 100)}"


class DevelopmentSettings(GlobalSettings):
    pass


def get_settings():
    env = environ.get("ENVIRONMENT", "development")
    if env == "test":
        return TestSettings()
    elif env == "development":
        return DevelopmentSettings()

    return GlobalSettings()


settings = get_settings()


LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": settings.LOG_LEVEL,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": settings.LOG_LEVEL, "propagate": False},
        "uvicorn": {
            "handlers": ["default"],
            "level": logging.ERROR,
            "propagate": False,
        },
    },
}
