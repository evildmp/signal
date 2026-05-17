import pytest
from django.core.management import call_command
from playwright.sync_api import expect, sync_playwright


@pytest.mark.django_db(transaction=True)
def test_selecting_my_dots_only_clears_selected_team_checkboxes(live_server):
    call_command("seed_initial_data")

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
    call_command("seed_initial_data")

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
