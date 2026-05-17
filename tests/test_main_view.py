import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from app.models import Team


@pytest.mark.django_db
def test_main_view_drawer_contains_visible_teams_and_explicit_defaults(client):
    call_command("seed_initial_data")
    jerry = get_user_model().objects.get(username="jerry")
    client.force_login(jerry)

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
    call_command("seed_initial_data")
    jerry = get_user_model().objects.get(username="jerry")
    client.force_login(jerry)

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
    call_command("seed_initial_data")
    jerry = get_user_model().objects.get(username="jerry")
    client.force_login(jerry)

    response = client.post(
        "/",
        {
            "action": "set_my_dots_only",
            "enabled": "1",
        },
    )

    assert response.status_code == 200
    assert response.context["my_dots_only"] is True
    assert response.context["selected_team_ids"] == set()


@pytest.mark.django_db
def test_selecting_a_team_clears_my_dots_only(client):
    call_command("seed_initial_data")
    jerry = get_user_model().objects.get(username="jerry")
    blue_team_id = Team.objects.get(name="Blue").id
    client.force_login(jerry)

    response = client.post(
        "/",
        {
            "action": "set_team_filters",
            "enabled": "1",
            "team_ids": [str(blue_team_id)],
        },
    )

    assert response.status_code == 200
    assert response.context["my_dots_only"] is False
    assert response.context["selected_team_ids"] == {blue_team_id}
