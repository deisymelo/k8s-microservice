"""Application configuration, loaded from environment variables.

Reading config from the environment (instead of hard-coding it) is what lets
us change behavior per environment later via Helm values and ArgoCD, without
touching the source code. This follows the 12-factor app principle.
"""
import os


class Settings:
    # Identity / metadata — surfaced in responses so we can SEE which version
    # and environment is actually running in the cluster.
    APP_NAME: str = os.getenv("APP_NAME", "k8s-microservice")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_ENV: str = os.getenv("APP_ENV", "local")  # local | dev | prod

    # Network
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")


settings = Settings()