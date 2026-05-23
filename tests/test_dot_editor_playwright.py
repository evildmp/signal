import pytest
from playwright.sync_api import expect, sync_playwright

from app.models import Dot


@pytest.mark.django_db(transaction=True)
def test_clicking_dot_opens_editor_dialog_over_grid(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=35, y=65, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        clicked_dot = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
        expect(clicked_dot).to_be_visible()
        clicked_dot.click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()
        expect(dialog).to_have_attribute("open", "")
        expect(dialog).not_to_contain_text(dot.claim_token)

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_dot_editor_dialog_has_cancel_button_and_no_close_button(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=55, y=35, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role("button", name="Cancel")).to_be_visible()
        expect(dialog.get_by_role("button", name="Close")).to_have_count(0)

        dialog.get_by_role("button", name="Cancel").click()
        expect(dialog).not_to_be_visible()

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_dot_editor_dialog_does_not_autofocus_private(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=57, y=43, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()
        private_checkbox = dialog.get_by_label("Private")
        expect(private_checkbox).not_to_be_focused()

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_dot_editor_dialog_closes_on_escape(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=45, y=45, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_clicking_dot_opens_dialog_without_creating_new_dot(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=50, y=50, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        target_dot = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
        expect(target_dot).to_be_visible()

        dots = page.locator(".signal-dot")
        initial_count = dots.count()

        target_dot.click()

        expect(page.locator("dialog#dot-editor-dialog")).to_be_visible()
        expect(dots).to_have_count(initial_count)

        browser.close()


@pytest.mark.django_db(transaction=True)
def test_saving_team_selection_in_dialog_updates_dot(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=40, y=60, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()

        dialog.get_by_label("Deep red").check()
        dialog.get_by_label("Blue").uncheck()
        dialog.get_by_role("button", name="Save").click()

        expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)

        browser.close()

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["deep_red"].id
    }


@pytest.mark.django_db(transaction=True)
def test_unchecking_all_teams_auto_selects_private(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=63, y=26, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()

        private_checkbox = dialog.get_by_label("Private")
        blue_checkbox = dialog.get_by_label("Blue")

        expect(blue_checkbox).to_be_checked()
        expect(private_checkbox).not_to_be_checked()

        blue_checkbox.uncheck()
        expect(private_checkbox).to_be_checked()

        dialog.get_by_role("button", name="Save").click()
        expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)

        browser.close()

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == set()


@pytest.mark.django_db(transaction=True)
def test_deleting_owned_dot_removes_it_from_the_grid(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=63, y=26)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.evaluate(
            "([dotId, token]) => localStorage.setItem('dotTokens', JSON.stringify({[dotId]: token}))",
            [str(dot.id), str(dot.ownership_token)],
        )
        page.reload()

        dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
        expect(dot_locator).to_be_visible()
        dot_locator.click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role("button", name="Delete")).to_be_visible()

        dialog.get_by_role("button", name="Delete").click()

        expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)
        expect(page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')).to_have_count(0)

        browser.close()

    assert not Dot.objects.filter(id=dot.id).exists()


@pytest.mark.django_db(transaction=True)
def test_saving_dot_updates_published_label_without_reload(
    live_server, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=63, y=26)
    dot.teams.add(minimum_team_hierarchy["blue"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server.url}/login/")
        page.locator('input[name="username"]').fill("jerry")
        page.locator('input[name="password"]').fill("jerry")
        page.get_by_role("button", name="Log in").click()

        page.evaluate(
            "([dotId, token]) => localStorage.setItem('dotTokens', JSON.stringify({[dotId]: token}))",
            [str(dot.id), str(dot.ownership_token)],
        )
        page.reload()

        dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
        dot_locator.click()

        dialog = page.locator("dialog#dot-editor-dialog")
        expect(dialog).to_be_visible()
        dialog.get_by_text("happy", exact=True).click()
        dialog.get_by_label("Show my name").check()
        dialog.get_by_role("button", name="Save").click()

        label = page.locator(f'.signal-dot-published-label[data-dot-id="{dot.id}"]')
        expect(label).to_be_visible()
        expect(label).to_contain_text("jerry")
        expect(label).to_contain_text("happy")

        browser.close()
