import logging
import secrets

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("sentio")


class Settings(BaseSettings):
    # Local Postgres by default. Override in .env when you move to Neon.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sentio"
    app_name: str = "Sentio.io API"

    # Flip to False once the real ML service is running.
    use_fake_model: bool = True
    ml_service_url: str = "http://localhost:8001"
    # Shared secret sent to the model service, so only this API can use it.
    # Leave empty locally; set the same value on both sides when it is public (ngrok).
    ml_service_token: str = ""

    # Login tokens. Set a long random JWT_SECRET in .env; never commit it.
    # If it is missing, a random one is made at startup (logins then reset on every restart).
    jwt_secret: str = ""
    jwt_expire_minutes: int = 60

    # Websites allowed to call the API (comma-separated). Add your Vercel URL here.
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @model_validator(mode="after")
    def _strong_jwt_secret(self):
        if len(self.jwt_secret) < 32 or self.jwt_secret == "change-me-in-env":
            log.warning("JWT_SECRET is missing or too short; using a random one for this run. "
                        "Set a long random JWT_SECRET in .env so logins survive restarts.")
            self.jwt_secret = secrets.token_urlsafe(48)
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """Hosts like Neon and Render give 'postgresql://' or 'postgres://' URLs;
        SQLAlchemy needs the driver name, so add '+psycopg'."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
