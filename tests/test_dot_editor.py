import json

import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model

from app.forms import DotEditorForm
from app.models import Dot, Team


@pytest.mark.django_db
def test_dot_editor_form_requires_user():
    with pytest.raises(ValueError, match="DotEditorForm requires a user"):
        DotEditorForm(user=None)


@pytest.mark.django_db
def test_dot_editor_endpoint_returns_dialog_for_clicked_dot(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert '<dialog id="dot-editor-dialog"' in content
    assert 'id="dot-editor-form"' in content
    assert "<script>" not in content


@pytest.mark.django_db
def test_dot_editor_form_exposes_dot_id_for_token_sync(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert f'data-dot-id="{dot.id}"' in content


@pytest.mark.django_db
def test_dot_editor_endpoint_requires_login(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=33, y=44)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 302
    assert response.url.startswith("/login/")


@pytest.mark.django_db
def test_dot_editor_endpoint_returns_404_for_unknown_dot_id(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)

    response = client.get("/dot/999999/edit/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_dot_editor_endpoint_rejects_put_method(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=33, y=44, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.put(f"/dot/{dot.id}/edit/")

    assert response.status_code == 405


@pytest.mark.django_db
def test_dot_editor_post_updates_selected_teams(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {"team_ids": [str(minimum_team_hierarchy["deep_red"].id)]},
    )

    assert response.status_code == 200
    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["deep_red"].id
    }


@pytest.mark.django_db
def test_dot_editor_post_renders_form_errors_for_invalid_team_selection(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=61, y=39, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {"team_ids": ["not-an-integer"]},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert '<dialog id="dot-editor-dialog"' in content
    assert "Select a valid choice" in content


@pytest.mark.django_db
def test_dot_editor_post_with_no_team_selection_saves_as_private(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=48, y=22, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(f"/dot/{dot.id}/edit/", {})

    assert response.status_code == 200
    assert response.content == b""

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == set()


@pytest.mark.django_db
def test_dot_editor_endpoint_renders_sentiment_inputs(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="feeling"' in content
    assert 'name="action_sentiment"' in content
    assert 'name="feeling_free_text"' in content
    assert 'name="action_sentiment_free_text"' in content
    assert 'name="include_name"' in content


@pytest.mark.django_db
def test_home_template_loads_external_dot_editor_script(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)

    response = client.get("/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "/static/app/dot_editor.js" in content


@pytest.mark.django_db
def test_dot_editor_post_updates_sentiment_fields(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "feeling": ["happy"],
            "feeling_free_text": "",
            "action_sentiment": [],
            "action_sentiment_free_text": "Could use a quick chat",
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    assert response.content == b""

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["deep_red"].id
    }
    assert dot.feeling == ["happy"]
    assert dot.feeling_free_text == ""
    assert dot.action_sentiment == []
    assert dot.action_sentiment_free_text == "Could use a quick chat"
    assert dot.owner_user == jerry_with_explicit_teams


@pytest.mark.django_db
def test_dot_editor_post_normalizes_free_text_by_removing_selected_sentiment_duplicates(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "feeling": ["happy"],
            "feeling_free_text": "happy, HAPPY",
            "action_sentiment": ["I need help"],
            "action_sentiment_free_text": "I need help, i need help",
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    assert response.content == b""

    dot.refresh_from_db()
    assert dot.feeling == ["happy"]
    assert dot.feeling_free_text == ""
    assert dot.action_sentiment == ["I need help"]
    assert dot.action_sentiment_free_text == ""


@pytest.mark.django_db
def test_dot_editor_post_rejects_multiple_feelings(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "feeling": ["happy", "calm"],
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Choose only one feeling, either from the list or manual text." in content

    dot.refresh_from_db()
    assert dot.feeling == []
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["blue"].id
    }


@pytest.mark.django_db
def test_dot_editor_post_rejects_feeling_selection_with_manual_text(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "feeling": ["happy"],
            "feeling_free_text": "steady",
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Choose only one feeling, either from the list or manual text." in content

    dot.refresh_from_db()
    assert dot.feeling == []
    assert dot.feeling_free_text == ""
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["blue"].id
    }


@pytest.mark.django_db
def test_dot_editor_post_rejects_multiple_action_sentiments(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "action_sentiment": ["I need help", "I'd love to talk about this"],
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert (
        "Choose only one action sentiment, either from the list or manual text."
        in content
    )

    dot.refresh_from_db()
    assert dot.action_sentiment == []
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["blue"].id
    }


@pytest.mark.django_db
def test_dot_editor_post_rejects_action_sentiment_selection_with_manual_text(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "action_sentiment": ["I need help"],
            "action_sentiment_free_text": "Could use a quick chat",
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert (
        "Choose only one action sentiment, either from the list or manual text."
        in content
    )

    dot.refresh_from_db()
    assert dot.action_sentiment == []
    assert dot.action_sentiment_free_text == ""
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["blue"].id
    }


@pytest.mark.django_db
def test_dot_editor_post_clears_user_with_owner_relation_when_show_my_name_is_unchecked(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "feeling": ["happy"],
            "action_sentiment": ["I need help"],
        },
    )

    assert response.status_code == 200
    assert response.content == b""

    dot.refresh_from_db()
    assert dot.owner_user is None


@pytest.mark.django_db
def test_dot_editor_endpoint_rejects_user_without_ownership(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="dot-claim-dialog"' in content
    assert "Claim or flag for review" in content
    assert 'name="claim_token"' in content


@pytest.mark.django_db
def test_dot_claim_endpoint_rejects_invalid_claim_token(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/claim/",
        {"claim_token": "wrong-token"},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_dot_claim_endpoint_returns_ownership_token_for_valid_claim_token(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/claim/",
        {"claim_token": dot.claim_token},
    )

    assert response.status_code == 200
    assert "HX-Trigger" in response.headers
    assert f'"dotId": {dot.id}' in response.headers["HX-Trigger"]
    assert str(dot.ownership_token) in response.headers["HX-Trigger"]


@pytest.mark.django_db
def test_dot_claim_endpoint_rejects_dot_with_owner_relation(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    tina = get_user_model().objects.create_user(username="tina", password="tina")
    dot = Dot.objects.create(x=22, y=74, owner_user=tina)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/claim/",
        {"claim_token": dot.claim_token},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_dot_editor_endpoint_allows_ownership_token_header(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(
        f"/dot/{dot.id}/edit/",
        HTTP_X_OWNERSHIP_TOKEN=str(dot.ownership_token),
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_dot_editor_endpoint_rejects_ownership_token_in_query_params(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.get(
        f"/dot/{dot.id}/edit/?ownership_token={dot.ownership_token}",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_dot_delete_endpoint_deletes_owned_dot(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/delete/",
        {"ownership_token": str(dot.ownership_token)},
    )

    assert response.status_code == 200
    hx_trigger = json.loads(response["HX-Trigger"])
    assert hx_trigger == {"dotDeleted": {"dotId": dot.id}}
    content = response.content.decode()
    assert f'id="signal-dot-{dot.id}"' in content
    assert 'hx-swap-oob="delete"' in content
    assert not Dot.objects.filter(id=dot.id).exists()


@pytest.mark.django_db
def test_dot_delete_endpoint_rejects_wrong_ownership_token(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/delete/",
        {"ownership_token": "not-the-right-token"},
    )

    assert response.status_code == 403
    assert Dot.objects.filter(id=dot.id).exists()


@pytest.mark.django_db
def test_dot_delete_endpoint_allows_user_with_owner_relation_without_ownership_token(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/delete/",
        {},
    )

    assert response.status_code == 200
    hx_trigger = json.loads(response["HX-Trigger"])
    assert hx_trigger == {"dotDeleted": {"dotId": dot.id}}
    content = response.content.decode()
    assert f'id="signal-dot-{dot.id}"' in content
    assert 'hx-swap-oob="delete"' in content
    assert not Dot.objects.filter(id=dot.id).exists()


@pytest.mark.django_db
def test_dot_user_with_owner_relation_can_edit_without_ownership_token(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
            "feeling": ["happy"],
            "action_sentiment": ["I need help"],
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    assert response.content == b""

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["deep_red"].id
    }
    assert dot.owner_user == jerry_with_explicit_teams


@pytest.mark.django_db
def test_dot_editor_get_calls_visible_for_user_once(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=22, y=74, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with patch(
        "app.models.Team.objects.visible_for_user",
        wraps=Team.objects.visible_for_user,
    ) as visible_for_user:
        response = client.get(f"/dot/{dot.id}/edit/")

    assert response.status_code == 200
    assert visible_for_user.call_count == 1


@pytest.mark.django_db
def test_dot_editor_post_calls_visible_for_user_once(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with patch(
        "app.models.Team.objects.visible_for_user",
        wraps=Team.objects.visible_for_user,
    ) as visible_for_user:
        response = client.post(
            f"/dot/{dot.id}/edit/",
            {
                "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
                "include_name": "on",
            },
        )

    assert response.status_code == 200
    assert visible_for_user.call_count == 1


@pytest.mark.django_db
def test_dot_editor_post_rolls_back_team_changes_when_save_fails(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    client.force_login(jerry_with_explicit_teams)

    dot = Dot.objects.create(x=28, y=52, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with patch.object(Dot, "save", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            client.post(
                f"/dot/{dot.id}/edit/",
                {
                    "team_ids": [str(minimum_team_hierarchy["deep_red"].id)],
                    "feeling": ["happy"],
                    "action_sentiment": ["I need help"],
                    "include_name": "on",
                },
            )

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["blue"].id
    }


@pytest.mark.django_db
def test_dot_edit_post_dotUpdated_payload_includes_published_label_html_not_label_parts(
    client, jerry_with_explicit_teams, minimum_team_hierarchy
):
    """The dotUpdated HX-Trigger payload must include publishedLabelHtml (server-rendered)
    and must not include labelParts or labelGroups — those are internal rendering
    details the JS handler no longer needs."""
    client.force_login(jerry_with_explicit_teams)
    dot = Dot.objects.create(x=50, y=50, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    response = client.post(
        f"/dot/{dot.id}/edit/",
        {
            "team_ids": [str(minimum_team_hierarchy["blue"].id)],
            "include_name": "on",
        },
    )

    assert response.status_code == 200
    trigger = json.loads(response.headers["HX-Trigger"])
    payload = trigger["dotUpdated"]
    assert "publishedLabelHtml" in payload
    assert "labelParts" not in payload
    assert "labelGroups" not in payload
