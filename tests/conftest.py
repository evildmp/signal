import os

import pytest
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from app.models import SignalOnboardingState, Team, TeamMembership


@pytest.fixture(autouse=True)
def fast_password_hashing(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


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


@pytest.fixture
def login_jerry(live_server, jerry_with_explicit_teams):
    SignalOnboardingState.objects.update_or_create(
        user=jerry_with_explicit_teams,
        defaults={"using_signal_seen": True},
    )

    def _login(page):
        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()
        page.wait_for_url(lambda url: "/login" not in url, wait_until="load")

    return _login


@pytest.fixture
def authenticated_page(page, login_jerry):
    login_jerry(page)
    return page
