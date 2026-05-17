import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


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
