from urllib.parse import quote_plus

from pydantic.v1 import Field, BaseSettings


class EnvironmentConfig(BaseSettings):
    API_PORT: int = Field(default=..., env="API_PORT")
    API_HOST: str = Field(default=..., env="API_HOST")
    API_URL: str = Field(default=..., env="API_URL")
    EMAIL: str = Field(default=..., env="EMAIL")
    EMAIL_HOST: str = Field(default=..., env="EMAIL_HOST")
    EMAIL_PASSWORD: str = Field(default=..., env="EMAIL_PASSWORD")

    DB_USER: str = Field(default=..., env="DB_USER")
    DB_PASSWORD: str = Field(default=..., env="DB_PASSWORD")
    DB_HOST: str = Field(default=..., env="DB_HOST")
    DB_PORT: int = Field(default=5432, env="DB_PORT")
    DB_NAME: str = Field(default=..., env="DB_NAME")

    LOGURU_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    ENV: str = Field(default="dev", env="ENV")

    SECRET_KEY: str = Field(default=..., env="SECRET_KEY")

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def async_database_url(self) -> str:
        return f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file = ".env"
        env_file_encoding = "utf-8"


ENV = EnvironmentConfig()

__all__ = ["ENV", "EnvironmentConfig"]
