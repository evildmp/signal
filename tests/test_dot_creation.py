import re
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from playwright.sync_api import expect, sync_playwright

from app.models import Dot, Team, TeamMembership


def create_user_with_explicit_teams(username="jerry", team_names=("Blue", "Deep red")):
    user = get_user_model().objects.create_user(username=username, password=username)
    teams = [Team.objects.create(name=name) for name in team_names]
    TeamMembership.objects.bulk_create(
        [TeamMembership(user=user, team=team) for team in teams]
    )
    return user, teams


def create_minimum_team_tree_for_jerry():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    blue = Team.objects.create(name="Blue", parent=colours)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)
    return blue, deep_red


@pytest.mark.django_db
def test_dot_claim_token_is_generated_on_creation():
    dot = Dot.objects.create(x=10, y=20)

    assert dot.claim_token is not None
    assert isinstance(dot.claim_token, uuid.UUID)


@pytest.mark.django_db
def test_dot_claim_token_is_unique():
    first = Dot.objects.create(x=10, y=20)
    second = Dot.objects.create(x=30, y=40)

    assert first.claim_token != second.claim_token


@pytest.mark.django_db
def test_create_dot_endpoint_publishes_to_user_explicit_teams(client):
    jerry, _ = create_user_with_explicit_teams()
    client.force_login(jerry)

    response = client.post(
        "/dot/create/",
        {"x": "42", "y": "73"},
    )

    assert response.status_code == 200

    dot = Dot.objects.latest("created_at")
    assert dot.x == 42
    assert dot.y == 73

    explicit_team_names = sorted(
        Team.objects.explicit_for_user(jerry).values_list("name", flat=True)
    )
    dot_team_names = sorted(dot.teams.values_list("name", flat=True))
    assert dot_team_names == explicit_team_names

    # Notification mentions the explicit teams
    content = response.content.decode()
    for team_name in explicit_team_names:
        assert team_name in content


@pytest.mark.django_db
def test_create_dot_requires_login(client):
    response = client.post(
        "/dot/create/",
        {"x": "42", "y": "73"},
    )

    assert response.status_code == 302
    assert response.url.startswith("/login/")


@pytest.mark.django_db
def test_create_dot_rejects_invalid_coordinates(client):
    jerry, _ = create_user_with_explicit_teams()
    client.force_login(jerry)

    before_count = Dot.objects.count()

    response = client.post(
        "/dot/create/",
        {"x": "150", "y": "-1"},
    )

    assert response.status_code == 400
    assert Dot.objects.count() == before_count


@pytest.mark.django_db(transaction=True)
def test_clicking_grid_places_a_dot_and_shows_notification(live_server):
    blue, deep_red = create_minimum_team_tree_for_jerry()
    jerry = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=jerry, team=blue)
    TeamMembership.objects.create(user=jerry, team=deep_red)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        grid = page.locator(".signal-grid")
        expect(grid).to_be_visible()

        initial_dot_count = page.locator(".signal-dot").count()

        # Click near the top-left corner
        bounding_box = grid.bounding_box()
        page.mouse.click(
            bounding_box["x"] + bounding_box["width"] * 0.1,
            bounding_box["y"] + bounding_box["height"] * 0.1
        )

        expect(page.locator(".signal-dot")).to_have_count(initial_dot_count + 1)

        label = page.locator(".signal-dot-label")
        expect(label).to_be_visible()
        expect(label).to_contain_text("Blue")
        expect(label).to_contain_text("Deep red")

        # Label near top-left should go to the right of the dot
        class_attr = label.get_attribute("class")
        assert "signal-dot-label--x-right" in class_attr

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_label_positions_near_edges(live_server):
    """Labels near grid edges should flip position to stay visible."""
    blue, deep_red = create_minimum_team_tree_for_jerry()
    jerry = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=jerry, team=blue)
    TeamMembership.objects.create(user=jerry, team=deep_red)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        grid = page.locator(".signal-grid")
        expect(grid).to_be_visible()
        bb = grid.bounding_box()

        # Click near bottom-right → label should be to the left of the dot
        page.mouse.click(
            bb["x"] + bb["width"] * 0.95,
            bb["y"] + bb["height"] * 0.95
        )
        label = page.locator(".signal-dot-label").last
        expect(label).to_be_visible()
        class_attr = label.get_attribute("class")
        assert "signal-dot-label--x-left" in class_attr

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_label_is_entirely_below_dot_when_dot_is_at_top_of_grid(live_server):
    """When a dot is placed at the very top of the grid, every part of the
    label must be below (greater screen y than) the bottom of the dot."""
    blue, deep_red = create_minimum_team_tree_for_jerry()
    jerry = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=jerry, team=blue)
    TeamMembership.objects.create(user=jerry, team=deep_red)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        grid = page.locator(".signal-grid")
        expect(grid).to_be_visible()
        bb = grid.bounding_box()

        # Click at 50% x, 2px from the top edge → y coordinate near 100
        page.mouse.click(
            bb["x"] + bb["width"] * 0.5,
            bb["y"] + 2
        )

        # Wait for the new dot and label to appear
        initial_count = page.locator(".signal-dot").count()
        expect(page.locator(".signal-dot")).to_have_count(initial_count)

        dot = page.locator(".signal-dot").last
        label = page.locator(".signal-dot-label").last

        expect(label).to_be_visible()

        dot_bb = dot.bounding_box()
        label_bb = label.bounding_box()

        # The top of the label must be at or below the bottom of the dot
        assert label_bb["y"] >= dot_bb["y"] + dot_bb["height"], (
            f"Label top ({label_bb['y']:.1f}) is above dot bottom "
            f"({dot_bb['y'] + dot_bb['height']:.1f}) — label overlaps or is above the dot"
        )

        browser.close()
