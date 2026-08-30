from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_host: str = "192.168.1.14"
    postgres_port: int = 5432
    postgres_user: str = "jmbxdbuser"
    postgres_password: str = ""
    postgres_db_rawdata: str = "bsa_db"
    postgres_db_bsa: str = "bsa_db"


    rawdata_postgres_dsn: Optional[str] = None
    bsa_postgres_dsn: Optional[str] = None
    database_schema: str = "public"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def build_dsns(self) -> "Settings":
        if not self.rawdata_postgres_dsn:
            # If password is provided, include it in the URL
            pw = f":{self.postgres_password}" if self.postgres_password else ""
            self.rawdata_postgres_dsn = f"postgresql://{self.postgres_user}{pw}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db_rawdata}"
        if not self.bsa_postgres_dsn:
            pw = f":{self.postgres_password}" if self.postgres_password else ""
            self.bsa_postgres_dsn = f"postgresql://{self.postgres_user}{pw}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db_bsa}"
        return self


settings = Settings()
