import pytest
from django.contrib.auth import get_user_model

from app.models import Team, TeamMembership


@pytest.fixture
def minimum_team_hierarchy():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    blue = Team.objects.create(name="Blue", parent=colours)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)

    return {
        "organisation": organisation,
        "colours": colours,
        "blue": blue,
        "red": red,
        "deep_red": deep_red,
    }


@pytest.fixture
def jerry_with_explicit_teams(minimum_team_hierarchy):
    jerry = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.bulk_create(
        [
            TeamMembership(user=jerry, team=minimum_team_hierarchy["blue"]),
            TeamMembership(user=jerry, team=minimum_team_hierarchy["deep_red"]),
        ]
    )
    return jerry
