from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(BASE_DIR / ".env.development")
environ.Env.read_env(BASE_DIR / ".env", overwrite=True)

from .settings import *  # noqa: F403
