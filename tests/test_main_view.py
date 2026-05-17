import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from datetime import timedelta

from django.utils import timezone

from app.models import Dot, Team


def login_as_jerry(client):
    call_command("seed_initial_data")
    jerry = get_user_model().objects.get(username="jerry")
    client.force_login(jerry)
    return jerry


def post_my_dots_only(client, enabled=True):
    payload = {"action": "set_my_dots_only"}
    if enabled:
        payload["enabled"] = "1"
    return client.post("/", payload)


def post_team_filters(client, team_ids):
    return client.post(
        "/",
        {
            "action": "set_team_filters",
            "team_ids": [str(team_id) for team_id in team_ids],
        },
    )


@pytest.mark.django_db
def test_main_view_drawer_contains_visible_teams_and_explicit_defaults(client):
    login_as_jerry(client)

    response = client.get("/")

    assert response.status_code == 200

    visible_team_names = sorted(team.name for team in response.context["visible_teams"])
    selected_team_names = sorted(
        team.name for team in response.context["visible_teams"] if team.id in response.context["selected_team_ids"]
    )

    assert visible_team_names == ["Blue", "Colours", "Deep red", "Organisation", "Red"]
    assert selected_team_names == ["Blue", "Deep red"]


@pytest.mark.django_db
def test_main_view_drawer_exposes_hierarchy_for_jerry(client):
    login_as_jerry(client)

    response = client.get("/")
    assert response.status_code == 200

    team_tree = response.context["team_tree"]

    assert [node["team"].name for node in team_tree] == ["Organisation"]

    organisation_children = team_tree[0]["children"]
    assert [node["team"].name for node in organisation_children] == ["Colours"]

    colours_children = organisation_children[0]["children"]
    assert [node["team"].name for node in colours_children] == ["Blue", "Red"]

    red_children = colours_children[1]["children"]
    assert [node["team"].name for node in red_children] == ["Deep red"]


@pytest.mark.django_db
def test_selecting_my_dots_only_marks_it_active_and_clears_selected_teams(client):
    login_as_jerry(client)

    response = post_my_dots_only(client)

    assert response.status_code == 200
    assert response.context["my_dots_only"] is True
    assert response.context["selected_team_ids"] == set()


@pytest.mark.django_db
def test_selecting_a_team_clears_my_dots_only(client):
    login_as_jerry(client)
    blue_team_id = Team.objects.get(name="Blue").id

    response = post_team_filters(client, [blue_team_id])

    assert response.status_code == 200
    assert response.context["my_dots_only"] is False
    assert response.context["selected_team_ids"] == {blue_team_id}


@pytest.mark.django_db
def test_main_view_shows_only_recent_dots_for_selected_teams(client):
    login_as_jerry(client)

    blue = Team.objects.get(name="Blue")
    deep_red = Team.objects.get(name="Deep red")
    organisation = Team.objects.get(name="Organisation")

    visible_dot = Dot.objects.create(x=10, y=20)
    visible_dot.teams.add(blue)

    stale_dot = Dot.objects.create(x=30, y=40)
    stale_dot.teams.add(deep_red)
    Dot.objects.filter(id=stale_dot.id).update(
        created_at=timezone.now() - timedelta(days=8)
    )

    non_selected_dot = Dot.objects.create(x=50, y=60)
    non_selected_dot.teams.add(organisation)

    response = client.get("/")

    assert response.status_code == 200
    returned_identifiers = {dot.identifier for dot in response.context["dots"]}
    assert returned_identifiers == {visible_dot.identifier}
