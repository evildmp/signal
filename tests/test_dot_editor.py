import pytest

from app.models import Dot


@pytest.mark.django_db
def test_dot_editor_endpoint_returns_dialog_for_clicked_dot(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.identifier}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert '<dialog id="dot-editor-dialog"' in content
    assert 'id="dot-editor-form"' in content
    assert dot.identifier in content


@pytest.mark.django_db
def test_dot_editor_endpoint_requires_login(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    dot = Dot.objects.create(x=33, y=44)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.identifier}/edit/")

    assert response.status_code == 302
    assert response.url.startswith("/login/")


@pytest.mark.django_db
def test_dot_editor_endpoint_returns_404_for_unknown_identifier(client, jerry_with_explicit_teams):
    client.force_login(jerry_with_explicit_teams)

    response = client.get("/dot/does-not-exist/edit/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_dot_editor_post_updates_selected_teams(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.identifier}/edit/",
        {"team_ids": [str(minimum_team_hierarchy["deep_red"].id)]},
    )

    assert response.status_code == 200
    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {minimum_team_hierarchy["deep_red"].id}


@pytest.mark.django_db
def test_dot_editor_post_renders_form_errors_for_invalid_team_selection(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=61, y=39)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.identifier}/edit/",
        {"team_ids": ["not-an-integer"]},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert '<dialog id="dot-editor-dialog"' in content
    assert "Select a valid choice" in content


@pytest.mark.django_db
def test_dot_editor_post_with_no_team_selection_saves_as_private(client, jerry_with_explicit_teams, minimum_team_hierarchy):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=48, y=22)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(f"/dot/{dot.identifier}/edit/", {})

    assert response.status_code == 200
    assert response.content == b""

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == set()
