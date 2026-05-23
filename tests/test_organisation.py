import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from app.models import Team, TeamMembership


@pytest.mark.django_db
def test_get_user_teams_includes_implied_ancestor_teams():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)
    blue = Team.objects.create(name="Blue", parent=colours)

    user = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=user, team=deep_red)
    TeamMembership.objects.create(user=user, team=blue)

    explicit_names = sorted(
        team.name
        for team in Team.objects.visible_for_user(user, include_implicit=False)
    )
    implied_names = sorted(
        team.name for team in Team.objects.visible_for_user(user, include_implicit=True)
    )

    assert explicit_names == ["Blue", "Deep red"]
    assert implied_names == ["Blue", "Colours", "Deep red", "Organisation", "Red"]


@pytest.mark.django_db
def test_deleting_team_reparents_children_to_grandparent():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)

    red.delete()
    deep_red.refresh_from_db()

    assert deep_red.parent == colours


@pytest.mark.django_db
def test_visible_for_user_include_implicit_has_query_budget():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)
    blue = Team.objects.create(name="Blue", parent=colours)

    user = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=user, team=deep_red)
    TeamMembership.objects.create(user=user, team=blue)

    with CaptureQueriesContext(connection) as queries:
        list(
            Team.objects.visible_for_user(user, include_implicit=True).values_list(
                "id", flat=True
            )
        )

    # Query budget target for an optimized implementation (no per-team parent-chain queries).
    assert len(queries) <= 3, f"Expected <=3 queries, got {len(queries)}"
