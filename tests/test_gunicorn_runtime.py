import os
import subprocess
import sys


def test_gunicorn_can_import_wsgi_application_with_runtime_environment():
    env = {
        **os.environ,
        "SECRET_KEY": "test-secret-key",
        "DEBUG": "false",
        "ALLOWED_HOSTS": "localhost",
        "DATABASE_URL": "sqlite:///db.sqlite3",
        "PYTHONPATH": os.getcwd(),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--check-config",
            "config.wsgi:application",
        ],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
