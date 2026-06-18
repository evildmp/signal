import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from app.management.commands.seed_initial_data import USER_DOT_COUNTS, USERS_AND_TEAMS
from app.models import Dot, Team


@pytest.mark.django_db
def test_seed_initial_data_is_deterministic_with_fixed_dot_counts():
    call_command("seed_initial_data")

    expected_total = sum(USER_DOT_COUNTS.values())
    assert Dot.objects.count() == expected_total

    first_snapshot = list(
        Dot.objects.order_by("claim_token").values_list(
            "claim_token",
            "x",
            "y",
            "owner_user_id",
            "feeling",
            "feeling_free_text",
            "action_sentiment",
            "action_sentiment_free_text",
            "created_at",
        )
    )

    call_command("seed_initial_data")

    second_snapshot = list(
        Dot.objects.order_by("claim_token").values_list(
            "claim_token",
            "x",
            "y",
            "owner_user_id",
            "feeling",
            "feeling_free_text",
            "action_sentiment",
            "action_sentiment_free_text",
            "created_at",
        )
    )
    assert first_snapshot == second_snapshot


@pytest.mark.django_db
def test_seed_initial_data_populates_recent_dots_with_team_publication():
    call_command("seed_initial_data")

    now = timezone.now()
    dots = Dot.objects.prefetch_related("teams")

    assert dots.exists()

    for dot in dots:
        assert dot.teams.exists()
        assert dot.created_at <= now
        assert dot.created_at >= now - timedelta(days=14)


@pytest.mark.django_db
def test_seed_initial_data_correlates_known_labels_with_grid_positions():
    call_command("seed_initial_data")

    dots = list(Dot.objects.all())

    sad_dot = next((dot for dot in dots if dot.feeling == ["sad"]), None)
    assert sad_dot is not None
    assert sad_dot.x < 40
    assert sad_dot.y < 40

    empty_dot = next(
        (
            dot
            for dot in dots
            if (dot.feeling_free_text or "").strip().lower() == "empty"
        ),
        None,
    )
    assert empty_dot is not None
    assert empty_dot.x < 20
    assert empty_dot.y < 20

    excited_dot = next((dot for dot in dots if dot.feeling == ["excited"]), None)
    assert excited_dot is not None
    assert excited_dot.x > 65
    assert excited_dot.y > 65

    irritated_dot = next((dot for dot in dots if dot.feeling == ["irritated"]), None)
    assert irritated_dot is not None
    assert irritated_dot.x < 40
    assert irritated_dot.y > 60

    enraged_dot = next((dot for dot in dots if dot.feeling == ["enraged"]), None)
    assert enraged_dot is not None
    assert enraged_dot.x < 25
    assert enraged_dot.y > 75


@pytest.mark.django_db
def test_seed_initial_data_ensures_expected_users_and_passwords():
    call_command("seed_initial_data")

    user_model = get_user_model()

    for username in USERS_AND_TEAMS:
        user = user_model.objects.get(username=username)
        assert user.check_password(username)


@pytest.mark.django_db
def test_seed_initial_data_makes_jerry_staff_superuser_and_in_all_teams():
    call_command("seed_initial_data")

    user_model = get_user_model()
    jerry = user_model.objects.get(username="jerry")

    assert jerry.is_staff
    assert jerry.is_superuser

    all_team_ids = set(Team.objects.values_list("id", flat=True))
    jerry_team_ids = set(
        Team.objects.explicit_for_user(jerry).values_list("id", flat=True)
    )
    assert jerry_team_ids == all_team_ids
