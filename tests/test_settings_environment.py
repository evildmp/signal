import os
import subprocess
import sys

from django.conf import settings


SETTINGS_PROBE = """
import config.settings
print(config.settings.DEBUG)
print(config.settings.ALLOWED_HOSTS)
print(config.settings.DATABASES['default']['ENGINE'])
"""

SETTINGS_PROBE_WITHOUT_DOTENV = """
import environ

environ.Env.read_env = classmethod(lambda cls, *args, **kwargs: None)

import config.settings
print(config.settings.DEBUG)
print(config.settings.ALLOWED_HOSTS)
print(config.settings.DATABASES['default']['ENGINE'])
"""


def run_settings_import(environment, *, read_dotenv=True, script=None):
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"SECRET_KEY", "DEBUG", "ALLOWED_HOSTS", "DATABASE_URL"}
    }
    env.update(environment)
    env["PYTHONPATH"] = os.getcwd()

    return subprocess.run(
        [
            sys.executable,
            "-c",
            script or (SETTINGS_PROBE if read_dotenv else SETTINGS_PROBE_WITHOUT_DOTENV),
        ],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_settings_load_runtime_configuration_from_environment():
    result = run_settings_import(
        {
            "SECRET_KEY": "test-secret-key",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com,www.example.com",
            "DATABASE_URL": "sqlite:///db.sqlite3",
        }
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "False",
        "['example.com', 'www.example.com']",
        "django.db.backends.sqlite3",
    ]


def test_settings_configures_whitenoise_static_file_serving():
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in settings.MIDDLEWARE
    assert settings.MIDDLEWARE.index(
        "whitenoise.middleware.WhiteNoiseMiddleware"
    ) == settings.MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1
    assert settings.STATIC_ROOT == settings.BASE_DIR / "staticfiles"

    result = run_settings_import(
        {
            "SECRET_KEY": "test-secret-key",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
            "DATABASE_URL": "sqlite:///db.sqlite3",
        },
        script="""
import config.settings
print(sorted(config.settings.STORAGES))
print(config.settings.STORAGES['staticfiles']['BACKEND'])
""",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "['staticfiles']",
        "whitenoise.storage.CompressedManifestStaticFilesStorage",
    ]


def test_settings_require_secret_key():
    result = run_settings_import(
        {
            "DEBUG": "false",
            "ALLOWED_HOSTS": "example.com",
            "DATABASE_URL": "sqlite:///db.sqlite3",
        },
        read_dotenv=False,
    )

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr
