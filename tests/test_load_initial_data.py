from datetime import timedelta
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone

from app.models import Dot


@pytest.mark.django_db
def test_load_initial_data_loads_recent_dots_without_rewriting_fixture():
    fixture_path = Path("app/fixtures/initial_data.json")
    original_fixture = fixture_path.read_text()

    call_command("load_initial_data")

    now = timezone.now()
    dots = Dot.objects.all()

    assert dots.exists()
    assert dots.count() == 55

    for dot in dots:
        assert dot.created_at <= now
        assert dot.created_at >= now - timedelta(days=7)

    assert fixture_path.read_text() == original_fixture
