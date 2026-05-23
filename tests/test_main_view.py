import re

import pytest
from django.contrib.auth import get_user_model
import re

from datetime import timedelta

from django.utils import timezone

from app.models import Dot, Team


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
def test_main_view_drawer_contains_visible_teams_and_explicit_defaults(client, jerry_with_explicit_teams):
    client.force_login(jerry_with_explicit_teams)

    response = client.get("/")

    assert response.status_code == 200

    visible_team_names = sorted(team.name for team in response.context["visible_teams"])
    selected_team_names = sorted(
        team.name for team in response.context["visible_teams"] if team.id in response.context["selected_team_ids"]
    )

    assert visible_team_names == ["Blue", "Colours", "Deep red", "Organisation", "Red"]
    assert selected_team_names == ["Blue", "Deep red"]


@pytest.mark.django_db
def test_main_view_drawer_exposes_hierarchy_for_jerry(client, jerry_with_explicit_teams):
    client.force_login(jerry_with_explicit_teams)

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
def test_selecting_my_dots_only_marks_it_active_and_clears_selected_teams(client, jerry_with_explicit_teams):
    client.force_login(jerry_with_explicit_teams)

    response = post_my_dots_only(client)

    assert response.status_code == 200
    assert response.context["my_dots_only"] is True
    assert response.context["selected_team_ids"] == set()


@pytest.mark.django_db
def test_selecting_a_team_clears_my_dots_only(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    client.force_login(jerry_with_explicit_teams)
    blue_team_id = minimum_team_hierarchy["blue"].id

    response = post_team_filters(client, [blue_team_id])

    assert response.status_code == 200
    assert response.context["my_dots_only"] is False
    assert response.context["selected_team_ids"] == {blue_team_id}


@pytest.mark.django_db
def test_my_dots_only_shows_owned_dots_even_without_selected_teams(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    owned_blue = Dot.objects.create(x=15, y=25, owner_user=jerry_with_explicit_teams)
    owned_blue.teams.add(minimum_team_hierarchy["blue"])

    owned_org = Dot.objects.create(x=35, y=45, owner_user=jerry_with_explicit_teams)
    owned_org.teams.add(minimum_team_hierarchy["organisation"])

    other_users_dot = Dot.objects.create(x=55, y=65)
    other_users_dot.teams.add(minimum_team_hierarchy["blue"])

    response = post_my_dots_only(client)

    assert response.status_code == 200
    assert response.context["my_dots_only"] is True
    returned_identifiers = {dot.identifier for dot in response.context["dots"]}
    assert owned_blue.identifier in returned_identifiers
    assert owned_org.identifier in returned_identifiers
    assert other_users_dot.identifier not in returned_identifiers


@pytest.mark.django_db
def test_main_view_shows_only_recent_dots_for_selected_teams(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    client.force_login(jerry_with_explicit_teams)

    organisation = minimum_team_hierarchy["organisation"]
    blue = minimum_team_hierarchy["blue"]
    deep_red = minimum_team_hierarchy["deep_red"]

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


@pytest.mark.django_db
def test_main_view_marks_owner_related_dot_as_claimed_without_token(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=40, y=60, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    match = re.search(
        rf'<span\s+class="([^"]*)"\s+data-dot-identifier="{re.escape(dot.identifier)}"',
        content,
    )
    assert match is not None
    assert "signal-dot--claimed" in match.group(1)


@pytest.mark.django_db
def test_main_view_renders_published_name_label_when_owner_relation_exists(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=40, y=60, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert (
        re.search(
            rf'<span[^>]*class="[^"]*signal-dot-published-label[^"]*"[^>]*data-dot-identifier="{re.escape(dot.identifier)}"[^>]*>.*jerry.*</span>',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        is not None
    )


@pytest.mark.django_db
def test_main_view_omits_published_name_label_when_owner_relation_is_null(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=40, y=60)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert (
        re.search(
            rf'<span[^>]*class="[^"]*signal-dot-published-label[^"]*"[^>]*data-dot-identifier="{re.escape(dot.identifier)}"[^>]*>.*jerry.*</span>',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        is None
    )


@pytest.mark.django_db
def test_main_view_renders_sentiment_labels_for_published_dot(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(
        x=40,
        y=60,
        owner_user=jerry_with_explicit_teams,
        feeling=["happy"],
        feeling_free_text="steady",
        action_sentiment=["I need help"],
        action_sentiment_free_text="Need a chat",
    )
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert (
        re.search(
            rf'<span[^>]*class="[^"]*signal-dot-published-label[^"]*"[^>]*data-dot-identifier="{re.escape(dot.identifier)}"[^>]*>.*happy.*steady.*I need help.*Need a chat.*</span>',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        is not None
    )


@pytest.mark.django_db
def test_main_view_deduplicates_sentiment_labels_when_free_text_repeats_selected_values(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(
        x=40,
        y=60,
        owner_user=jerry_with_explicit_teams,
        feeling=["happy"],
        feeling_free_text="happy, steady",
        action_sentiment=["I need help"],
        action_sentiment_free_text="I need help, Need a chat",
    )
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert f'data-dot-identifier="{dot.identifier}"' in content
    assert "happy, steady" in content
    assert "I need help, Need a chat" in content
    assert "happy, happy" not in content.lower()
    assert "i need help, i need help" not in content.lower()
