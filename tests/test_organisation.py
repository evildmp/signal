import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

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
        team.name for team in Team.objects.visible_for_user(user, include_implicit=False)
    )
    implied_names = sorted(
        team.name for team in Team.objects.visible_for_user(user, include_implicit=True)
    )

    assert explicit_names == ["Blue", "Deep red"]
    assert implied_names == ["Blue", "Colours", "Deep red", "Organisation", "Red"]


@pytest.mark.django_db
def test_seed_initial_data_creates_hierarchy_users_and_memberships():
    call_command("seed_initial_data")

    assert Team.objects.count() == 12
    assert get_user_model().objects.count() == 11

    jerry = get_user_model().objects.get(username="jerry")
    explicit_team_names = sorted(
        TeamMembership.objects.filter(user=jerry)
        .select_related("team")
        .values_list("team__name", flat=True)
    )
    assert explicit_team_names == ["Blue", "Deep red"]


@pytest.mark.django_db
def test_seed_initial_data_is_idempotent():
    call_command("seed_initial_data")
    call_command("seed_initial_data")

    assert Team.objects.count() == 12
    assert TeamMembership.objects.count() == 12
    assert get_user_model().objects.count() == 11


@pytest.mark.django_db
def test_deleting_team_reparents_children_to_grandparent():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)

    red.delete()
    deep_red.refresh_from_db()

    assert deep_red.parent == colours
