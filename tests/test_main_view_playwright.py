import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from playwright.sync_api import expect, sync_playwright

from app.models import Team, TeamMembership


def create_jerry_with_minimum_team_tree():
    organisation = Team.objects.create(name="Organisation")
    colours = Team.objects.create(name="Colours", parent=organisation)
    blue = Team.objects.create(name="Blue", parent=colours)
    red = Team.objects.create(name="Red", parent=colours)
    deep_red = Team.objects.create(name="Deep red", parent=red)

    jerry = get_user_model().objects.create_user(username="jerry", password="jerry")
    TeamMembership.objects.create(user=jerry, team=blue)
    TeamMembership.objects.create(user=jerry, team=deep_red)


@pytest.mark.django_db(transaction=True)
def test_selecting_my_dots_only_clears_selected_team_checkboxes(live_server):
    create_jerry_with_minimum_team_tree()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        blue = page.get_by_label("Blue")
        deep_red = page.get_by_label("Deep red")
        my_dots_only = page.get_by_label("My dots only")

        expect(blue).to_be_checked()
        expect(deep_red).to_be_checked()
        expect(my_dots_only).not_to_be_checked()

        my_dots_only.check()

        expect(my_dots_only).to_be_checked()
        expect(blue).not_to_be_checked()
        expect(deep_red).not_to_be_checked()

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_selecting_a_team_clears_my_dots_only(live_server):
    create_jerry_with_minimum_team_tree()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        blue = page.get_by_label("Blue")
        deep_red = page.get_by_label("Deep red")
        my_dots_only = page.get_by_label("My dots only")

        my_dots_only.check()

        expect(my_dots_only).to_be_checked()
        expect(blue).not_to_be_checked()
        expect(deep_red).not_to_be_checked()

        blue.check()

        expect(blue).to_be_checked()
        expect(my_dots_only).not_to_be_checked()

        browser.close()
