from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./hospital.db"

    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    cookie_secure: bool = False

    # When true: the whole database is wiped and reseeded with demo data on
    # every app startup, and POST /api/auth/demo-login (public, no
    # credentials) does the same on demand. Off by default so local dev
    # (uvicorn --reload re-runs startup on every reload) never loses data,
    # and so a real deployment doesn't expose a public data-wipe endpoint
    # unless explicitly opted in. Only ever enable this on a demo/pitch
    # instance — this app has no tenant isolation, so demo mode wipes
    # everything, not just a sandboxed slice.
    demo_mode: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
