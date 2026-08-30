from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    rawdata_postgres_dsn: str = "postgresql:///rawdata_db?host=/var/run/postgresql"
    bsa_postgres_dsn: str = "postgresql:///bsa_db?host=/var/run/postgresql"
    database_schema: str = "public"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
