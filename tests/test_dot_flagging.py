import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from app.models import Dot, Team


@pytest.mark.django_db
def test_unowned_dot_dialog_includes_flag_action(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=42, y=61)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Flag for review" in content


@pytest.mark.django_db
def test_any_user_can_flag_dot_they_do_not_own(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")
    dot = Dot.objects.create(x=25, y=78, owner_user=tina)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)

    response = client.post(
        f"/dot/{dot.id}/flag/",
        {"reason": "Looks unsafe"},
    )

    assert response.status_code == 200
    dot.refresh_from_db()
    assert getattr(dot, "flagged_by_id", None) == jerry_with_explicit_teams.id
    assert getattr(dot, "flag_reason", "") == "Looks unsafe"


@pytest.mark.django_db
def test_flagged_dot_is_redacted_in_main_view(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(
        x=57,
        y=21,
        owner_user=jerry_with_explicit_teams,
        feeling=["happy"],
        action_sentiment=["I need help"],
    )
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    flag_response = client.post(f"/dot/{dot.id}/flag/", {"reason": "testing"})
    assert flag_response.status_code == 200

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "Flagged for review" in content
    assert "happy" not in content
    assert "I need help" not in content


@pytest.mark.django_db
def test_owned_dot_editor_does_not_show_flag_action(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=44, y=39, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    assert "Flag this dot" not in response.content.decode()


@pytest.mark.django_db
def test_token_owned_dot_editor_does_not_show_flag_action(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=44, y=39)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    response = client.get(
        f"/dot/{dot.id}/edit/",
        HTTP_X_OWNERSHIP_TOKEN=str(dot.ownership_token),
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="dot-editor-dialog"' in content
    assert "Flag this dot" not in content


@pytest.mark.django_db
def test_dot_with_owner_relation_still_allows_flagging_dialog(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")
    dot = Dot.objects.create(x=35, y=65, owner_user=tina)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="dot-flag-confirm-dialog"' in content
    assert "Flag for review" in content
    assert "Cancel" in content
    assert ">Flag<" in content


@pytest.mark.django_db
def test_flagged_dot_is_locked_for_all_mutations(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=44, y=39, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    assert client.post(f"/dot/{dot.id}/flag/", {"reason": "review"}).status_code == 200

    edit_response = client.post(
        f"/dot/{dot.id}/edit/", {"team_ids": [str(minimum_team_hierarchy["blue"].id)]}
    )
    move_response = client.post(f"/dot/{dot.id}/move/", {"x": "22", "y": "30"})
    delete_response = client.post(f"/dot/{dot.id}/delete/")
    claim_response = client.post(
        f"/dot/{dot.id}/claim/", {"claim_token": dot.claim_token}
    )

    assert edit_response.status_code == 403
    assert move_response.status_code == 403
    assert delete_response.status_code == 403
    assert claim_response.status_code == 403


@pytest.mark.django_db
def test_second_user_cannot_reflag_locked_dot(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")

    dot = Dot.objects.create(x=17, y=88)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    assert client.post(f"/dot/{dot.id}/flag/", {"reason": "first"}).status_code == 200

    client.force_login(tina)
    second_response = client.post(f"/dot/{dot.id}/flag/", {"reason": "second"})

    assert second_response.status_code == 403


@pytest.mark.django_db
def test_only_flagger_or_admin_can_unflag_dot(
    client, admin_client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")

    dot = Dot.objects.create(x=68, y=33)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    assert client.post(f"/dot/{dot.id}/flag/", {"reason": "lock"}).status_code == 200

    client.force_login(tina)
    not_flagger_response = client.post(f"/dot/{dot.id}/unflag/")
    assert not_flagger_response.status_code == 403

    client.force_login(jerry_with_explicit_teams)
    flagger_response = client.post(f"/dot/{dot.id}/unflag/")
    assert flagger_response.status_code == 200

    client.force_login(jerry_with_explicit_teams)
    assert client.post(f"/dot/{dot.id}/flag/", {"reason": "again"}).status_code == 200

    admin_unflag_response = admin_client.post(
        reverse("admin:app_dot_unflag", args=[dot.id])
    )
    assert admin_unflag_response.status_code in (200, 302)


@pytest.mark.django_db
def test_flagged_dot_click_shows_locked_dialog_message(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=31, y=47)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    assert client.post(f"/dot/{dot.id}/flag/", {"reason": "lock"}).status_code == 200

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "This item has been flagged for review." in content
    assert "OK" in content


@pytest.mark.django_db
def test_user_cannot_flag_dot_they_cannot_see(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina_hidden", password="tina")
    hidden_team = Team.objects.create(name="Hidden team")

    dot = Dot.objects.create(x=10, y=10, owner_user=tina)
    dot.teams.add(hidden_team)

    client.force_login(jerry_with_explicit_teams)

    home_response = client.get("/")
    assert home_response.status_code == 200
    assert f'data-dot-id="{dot.id}"' not in home_response.content.decode()

    flag_response = client.post(f"/dot/{dot.id}/flag/", {"reason": "cannot see this"})
    assert flag_response.status_code == 403


@pytest.mark.django_db
def test_dot_flag_dotUpdated_payload_includes_published_label_html_not_label_parts(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    """Flag and unflag must fire a dotUpdated payload that includes publishedLabelHtml
    and excludes the now-redundant labelParts and labelGroups keys."""
    dot = Dot.objects.create(x=44, y=55, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    client.force_login(jerry_with_explicit_teams)
    flag_response = client.post(f"/dot/{dot.id}/flag/", {"reason": "test"})

    assert flag_response.status_code == 200
    trigger = json.loads(flag_response.headers["HX-Trigger"])
    payload = trigger["dotUpdated"]
    assert "publishedLabelHtml" in payload
    assert "labelParts" not in payload
    assert "labelGroups" not in payload

    unflag_response = client.post(f"/dot/{dot.id}/unflag/")

    assert unflag_response.status_code == 200
    trigger = json.loads(unflag_response.headers["HX-Trigger"])
    payload = trigger["dotUpdated"]
    assert "publishedLabelHtml" in payload
    assert "labelParts" not in payload
    assert "labelGroups" not in payload
