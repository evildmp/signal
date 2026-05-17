import re
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from app.models import Dot


@pytest.mark.django_db
def test_dot_coordinates_must_be_within_zero_to_hundred():
    valid_dot = Dot(x=0, y=100)
    valid_dot.full_clean()

    invalid_x = Dot(x=-1, y=50)
    invalid_y = Dot(x=50, y=101)

    with pytest.raises(ValidationError):
        invalid_x.full_clean()
    with pytest.raises(ValidationError):
        invalid_y.full_clean()


@pytest.mark.django_db
def test_dot_identifier_is_unique_and_matches_expected_pattern():
    first = Dot.objects.create(x=10, y=20)
    second = Dot.objects.create(x=30, y=40)

    pattern = re.compile(r"^[a-z]+-[a-z]+-[a-z]+$")
    assert pattern.match(first.identifier)
    assert pattern.match(second.identifier)
    assert first.identifier != second.identifier


@pytest.mark.django_db
def test_dot_created_at_is_set_on_create():
    before = timezone.now()
    dot = Dot.objects.create(x=10, y=20)
    after = timezone.now()

    assert before <= dot.created_at <= after


@pytest.mark.django_db
def test_dot_visibility_is_limited_to_last_week():
    recent_dot = Dot.objects.create(x=10, y=20)
    stale_dot = Dot.objects.create(x=30, y=40)

    Dot.objects.filter(id=recent_dot.id).update(
        created_at=timezone.now() - timedelta(days=6)
    )
    Dot.objects.filter(id=stale_dot.id).update(
        created_at=timezone.now() - timedelta(days=8)
    )

    recent_dot.refresh_from_db()
    stale_dot.refresh_from_db()

    assert recent_dot.is_visible()
    assert not stale_dot.is_visible()
