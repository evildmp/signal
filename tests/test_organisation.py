import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from app.models import Team, TeamMembership


def create_minimum_org_for_jerry():
    organisation, _ = Team.objects.get_or_create(name="Organisation")
    colours, _ = Team.objects.get_or_create(name="Colours", defaults={"parent": organisation})
    if colours.parent_id != organisation.id:
        colours.parent = organisation
        colours.save(update_fields=["parent"])

    red, _ = Team.objects.get_or_create(name="Red", defaults={"parent": colours})
    if red.parent_id != colours.id:
        red.parent = colours
        red.save(update_fields=["parent"])

    deep_red, _ = Team.objects.get_or_create(name="Deep red", defaults={"parent": red})
    if deep_red.parent_id != red.id:
        deep_red.parent = red
        deep_red.save(update_fields=["parent"])

    blue, _ = Team.objects.get_or_create(name="Blue", defaults={"parent": colours})
    if blue.parent_id != colours.id:
        blue.parent = colours
        blue.save(update_fields=["parent"])

    user, created = get_user_model().objects.get_or_create(username="jerry")
    if created:
        user.set_password("jerry")
        user.save(update_fields=["password"])

    TeamMembership.objects.get_or_create(user=user, team=blue)
    TeamMembership.objects.get_or_create(user=user, team=deep_red)

    return user


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
def test_fixture_setup_creates_hierarchy_users_and_memberships():
    jerry = create_minimum_org_for_jerry()

    assert Team.objects.count() == 5
    assert get_user_model().objects.count() == 1
    assert Team.objects.filter(name="Organisation", parent__isnull=True).exists()
    assert Team.objects.filter(name="Colours", parent__name="Organisation").exists()
    assert Team.objects.filter(name="Red", parent__name="Colours").exists()
    assert Team.objects.filter(name="Deep red", parent__name="Red").exists()
    assert Team.objects.filter(name="Blue", parent__name="Colours").exists()

    explicit_team_names = sorted(
        TeamMembership.objects.filter(user=jerry)
        .select_related("team")
        .values_list("team__name", flat=True)
    )
    assert explicit_team_names == ["Blue", "Deep red"]


@pytest.mark.django_db
def test_fixture_setup_is_idempotent():
    create_minimum_org_for_jerry()
    create_minimum_org_for_jerry()

    assert Team.objects.count() == 5
    assert TeamMembership.objects.count() == 2
    assert get_user_model().objects.count() == 1


@pytest.mark.django_db
def test_deleting_team_reparents_children_to_grandparent():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)

    red.delete()
    deep_red.refresh_from_db()

    assert deep_red.parent == colours


@pytest.mark.django_db
def test_visible_for_user_include_implicit_has_query_budget():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)
    blue = Team.objects.create(name="Blue", parent=colours)

    user = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=user, team=deep_red)
    TeamMembership.objects.create(user=user, team=blue)

    with CaptureQueriesContext(connection) as queries:
        list(Team.objects.visible_for_user(user, include_implicit=True).values_list("id", flat=True))

    # Query budget target for an optimized implementation (no per-team parent-chain queries).
    assert len(queries) <= 3, f"Expected <=3 queries, got {len(queries)}"
