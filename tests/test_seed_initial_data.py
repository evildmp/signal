import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from app.management.commands.seed_initial_data import USERS_AND_TEAMS
from app.models import Dot


@pytest.mark.django_db
def test_seed_initial_data_creates_realistic_dot_volume_and_ratios():
    call_command("seed_initial_data")

    dots = list(Dot.objects.all())
    user_count = len(USERS_AND_TEAMS)

    assert user_count * 4 <= len(dots) <= user_count * 12

    anonymous_count = sum(1 for dot in dots if dot.owner_user_id is None)
    anonymous_ratio = anonymous_count / len(dots)
    assert 0.62 <= anonymous_ratio <= 0.78

    with_feeling = sum(
        1 for dot in dots if dot.feeling or (dot.feeling_free_text or "").strip()
    )
    feeling_ratio = with_feeling / len(dots)
    assert 0.32 <= feeling_ratio <= 0.48

    with_action = sum(
        1
        for dot in dots
        if dot.action_sentiment or (dot.action_sentiment_free_text or "").strip()
    )
    action_ratio = with_action / len(dots)
    assert 0.14 <= action_ratio <= 0.28


@pytest.mark.django_db
def test_seed_initial_data_populates_recent_dots_with_team_publication():
    call_command("seed_initial_data")

    now = timezone.now()
    dots = Dot.objects.prefetch_related("teams")

    assert dots.exists()

    for dot in dots:
        assert dot.teams.exists()
        assert dot.created_at <= now
        assert dot.created_at >= now - timedelta(days=7)


@pytest.mark.django_db
def test_seed_initial_data_ensures_expected_users_and_passwords():
    call_command("seed_initial_data")

    user_model = get_user_model()

    for username in USERS_AND_TEAMS:
        user = user_model.objects.get(username=username)
        assert user.check_password(username)
