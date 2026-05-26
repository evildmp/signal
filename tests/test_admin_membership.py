import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from app.models import Team, TeamMembership


def _user_change_payload(admin_change_response):
    form = admin_change_response.context["adminform"].form
    payload = {}

    for field_name, field in form.fields.items():
        if hasattr(field.widget, "widgets"):
            raw_value = form.initial.get(field_name, field.initial)
            if isinstance(raw_value, (list, tuple)):
                values = raw_value
            elif raw_value is None:
                values = [None] * len(field.widget.widgets)
            else:
                values = field.widget.decompress(raw_value)

            for index, part in enumerate(values):
                payload[f"{field_name}_{index}"] = "" if part is None else str(part)
            continue

        value = form[field_name].value()

        if value is None:
            payload[field_name] = ""
            continue

        if isinstance(value, bool):
            if value:
                payload[field_name] = "on"
            continue

        if hasattr(value, "all"):
            payload[field_name] = [str(item.pk) for item in value.all()]
            continue

        if isinstance(value, (list, tuple, set)):
            payload[field_name] = [str(item) for item in value]
            continue

        payload[field_name] = str(value)

    return payload


@pytest.mark.django_db
def test_team_admin_allows_adding_user_membership(admin_client):
    team = Team.objects.create(name="Blue")
    user = get_user_model().objects.create_user(username="jerry", password="jerry")

    response = admin_client.post(
        reverse("admin:app_team_change", args=[team.id]),
        {
            "name": team.name,
            "parent": "",
            "memberships-TOTAL_FORMS": "1",
            "memberships-INITIAL_FORMS": "0",
            "memberships-MIN_NUM_FORMS": "0",
            "memberships-MAX_NUM_FORMS": "1000",
            "memberships-0-id": "",
            "memberships-0-user": str(user.id),
            "_save": "Save",
        },
    )

    assert response.status_code in (200, 302)
    assert TeamMembership.objects.filter(team=team, user=user).exists()


@pytest.mark.django_db
def test_team_admin_allows_removing_user_membership(admin_client):
    team = Team.objects.create(name="Blue")
    user = get_user_model().objects.create_user(username="jerry", password="jerry")
    membership = TeamMembership.objects.create(team=team, user=user)

    response = admin_client.post(
        reverse("admin:app_team_change", args=[team.id]),
        {
            "name": team.name,
            "parent": "",
            "memberships-TOTAL_FORMS": "1",
            "memberships-INITIAL_FORMS": "1",
            "memberships-MIN_NUM_FORMS": "0",
            "memberships-MAX_NUM_FORMS": "1000",
            "memberships-0-id": str(membership.id),
            "memberships-0-user": str(user.id),
            "memberships-0-DELETE": "on",
            "_save": "Save",
        },
    )

    assert response.status_code in (200, 302)
    assert not TeamMembership.objects.filter(id=membership.id).exists()


@pytest.mark.django_db
def test_user_admin_allows_adding_team_membership(admin_client):
    user = get_user_model().objects.create_user(username="jerry", password="jerry")
    team = Team.objects.create(name="Blue")
    change_url = reverse("admin:auth_user_change", args=[user.id])

    get_response = admin_client.get(change_url)
    assert get_response.status_code == 200
    payload = _user_change_payload(get_response)
    payload.update(
        {
            "team_memberships-TOTAL_FORMS": "1",
            "team_memberships-INITIAL_FORMS": "0",
            "team_memberships-MIN_NUM_FORMS": "0",
            "team_memberships-MAX_NUM_FORMS": "1000",
            "team_memberships-0-id": "",
            "team_memberships-0-team": str(team.id),
            "_save": "Save",
        }
    )

    response = admin_client.post(change_url, payload)

    assert response.status_code in (200, 302)
    assert TeamMembership.objects.filter(team=team, user=user).exists()


@pytest.mark.django_db
def test_user_admin_allows_removing_team_membership(admin_client):
    user = get_user_model().objects.create_user(username="jerry", password="jerry")
    team = Team.objects.create(name="Blue")
    membership = TeamMembership.objects.create(team=team, user=user)
    change_url = reverse("admin:auth_user_change", args=[user.id])

    get_response = admin_client.get(change_url)
    assert get_response.status_code == 200
    payload = _user_change_payload(get_response)
    payload.update(
        {
            "team_memberships-TOTAL_FORMS": "1",
            "team_memberships-INITIAL_FORMS": "1",
            "team_memberships-MIN_NUM_FORMS": "0",
            "team_memberships-MAX_NUM_FORMS": "1000",
            "team_memberships-0-id": str(membership.id),
            "team_memberships-0-team": str(team.id),
            "team_memberships-0-DELETE": "on",
            "_save": "Save",
        }
    )

    response = admin_client.post(change_url, payload)

    assert response.status_code in (200, 302)
    assert not TeamMembership.objects.filter(id=membership.id).exists()
