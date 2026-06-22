from pathlib import Path


ROCKCRAFT_YAML = Path(__file__).resolve().parent.parent / "rockcraft.yaml"


def rockcraft_configuration_lines():
    return "\n".join(
        line for line in ROCKCRAFT_YAML.read_text().splitlines() if not line.strip().startswith("#")
    )


def test_rockcraft_yaml_is_custom_and_not_django_framework_extension():
    content = rockcraft_configuration_lines()

    assert "django-framework" not in content
    assert "extensions:" not in content
    assert "base: ubuntu@24.04" in content


def test_rockcraft_yaml_installs_python_dependencies_from_requirements():
    content = ROCKCRAFT_YAML.read_text()

    assert "plugin: python" in content
    assert "source: ." in content
    assert "python-requirements:" in content
    assert "- requirements.txt" in content
    assert "stage-packages:" in content
    assert "- python3-venv" in content


def test_rockcraft_yaml_copies_runtime_application_files_to_app_directory():
    content = ROCKCRAFT_YAML.read_text()

    assert "application-files:" in content
    assert "plugin: dump" in content
    assert "organize:" in content
    assert "manage.py: app/manage.py" in content
    assert "config: app/config" in content
    assert "app: app/app" in content
    assert "requirements.txt: app/requirements.txt" in content
    assert "prime:" in content
    assert "- app/manage.py" in content
    assert "- app/config" in content
    assert "- app/app" in content
    assert "- app/requirements.txt" in content


def test_rockcraft_yaml_runs_gunicorn_from_app_directory():
    content = ROCKCRAFT_YAML.read_text()

    assert "services:" in content
    assert "django:" in content
    assert "override: replace" in content
    assert "command: /bin/python3 -m gunicorn config.wsgi:application --bind 0.0.0.0:8000" in content
    assert "startup: enabled" in content
    assert "working-dir: /app" in content
    assert "user: _daemon_" in content
    assert "DJANGO_SETTINGS_MODULE: config.settings" in content


def test_rockcraft_yaml_collects_static_files_during_build():
    content = ROCKCRAFT_YAML.read_text()

    assert "override-build: |" in content
    assert "craftctl default" in content
    assert "SECRET_KEY=build-time-only" in content
    assert "DEBUG=false" in content
    assert "ALLOWED_HOSTS=localhost" in content
    assert "DATABASE_URL=sqlite:///build.sqlite3" in content
    assert "manage.py collectstatic --noinput --clear" in content
    assert "cp -a \"$CRAFT_PART_SRC/staticfiles\" \"$CRAFT_PART_INSTALL/app/staticfiles\"" in content
