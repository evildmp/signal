import re

import pytest
from playwright.sync_api import expect
from django.contrib.auth import get_user_model

from app.models import Dot


@pytest.mark.django_db(transaction=True)
def test_clicking_dot_opens_editor_dialog_over_grid(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=35, y=65, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    clicked_dot = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(clicked_dot).to_be_visible()
    clicked_dot.click()

    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_have_attribute("open", "")
    expect(dialog).not_to_contain_text(dot.claim_token)


@pytest.mark.django_db(transaction=True)
def test_clicking_unclaimed_dot_opens_claim_dialog(
    page, login_jerry, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=35, y=65)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

    claim_dialog = page.locator("dialog#dot-claim-dialog")
    expect(claim_dialog).to_be_visible()
    expect(claim_dialog).to_have_attribute("open", "")
    expect(claim_dialog).to_contain_text("Claim or flag for review")
    expect(claim_dialog.get_by_label("Claim token")).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_valid_claim_token_grants_ownership_token_and_opens_editor(
    page, login_jerry, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=35, y=65)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()
    claim_dialog = page.locator("dialog#dot-claim-dialog")
    expect(claim_dialog).to_be_visible()

    claim_dialog.get_by_label("Claim token").fill(dot.claim_token)
    claim_dialog.get_by_role("button", name="Claim").click()

    expect(page.locator("dialog#dot-editor-dialog")).to_be_visible()
    expect(page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')).to_have_attribute(
        "class", re.compile(r"\bsignal-dot--claimed\b")
    )
    stored_token = page.evaluate(
        "dotId => JSON.parse(localStorage.getItem('dotTokens') || '{}')[String(dotId)]",
        str(dot.id),
    )
    assert stored_token == str(dot.ownership_token)


@pytest.mark.django_db(transaction=True)
def test_clicking_dot_with_owner_relation_is_ignored(
    page, login_jerry, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")
    dot = Dot.objects.create(x=35, y=65, owner_user=tina)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

    expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)
    flag_dialog = page.locator("dialog#dot-flag-confirm-dialog")
    expect(flag_dialog).to_be_visible()
    expect(flag_dialog.get_by_role("button", name="Cancel")).to_be_visible()
    expect(flag_dialog.get_by_role("button", name="Flag")).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_dragging_dot_with_owner_relation_does_nothing(
    page, login_jerry, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")
    dot = Dot.objects.create(x=25, y=75, owner_user=tina)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(dot_locator).to_be_visible()
    initial_dots = page.locator(".signal-dot").count()

    style_before = dot_locator.get_attribute("style")
    dot_box = dot_locator.bounding_box()
    page.mouse.move(
        dot_box["x"] + dot_box["width"] / 2,
        dot_box["y"] + dot_box["height"] / 2,
    )
    page.mouse.down()
    page.mouse.move(dot_box["x"] + 120, dot_box["y"] - 90)
    page.mouse.up()

    style_after = dot_locator.get_attribute("style")
    assert style_after == style_before
    expect(page.locator(".signal-dot")).to_have_count(initial_dots)
    expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)
    expect(page.locator("dialog#dot-claim-dialog")).to_have_count(0)

    dot.refresh_from_db()
    assert dot.x == 25
    assert dot.y == 75


@pytest.mark.django_db(transaction=True)
def test_dragging_owned_dot_with_pointer_events_moves_it(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=30, y=70, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(dot_locator).to_be_visible()

    initial_x = page.evaluate(
        """
        (dotId) => document
          .querySelector('.signal-dot[data-dot-id="' + dotId + '"]')
          .style.getPropertyValue('--dot-x')
        """,
        str(dot.id),
    )

    dot_box = dot_locator.bounding_box()
    start_x = dot_box["x"] + dot_box["width"] / 2
    start_y = dot_box["y"] + dot_box["height"] / 2
    end_x = start_x + 90
    end_y = start_y - 80

    page.evaluate(
        """
        ({ dotId, startX, startY, endX, endY }) => {
          const dot = document.querySelector('.signal-dot[data-dot-id="' + dotId + '"]');
          const withCoords = (x, y, buttons) => ({
            bubbles: true,
            cancelable: true,
            pointerId: 1,
            pointerType: 'touch',
            isPrimary: true,
            button: 0,
            buttons: buttons,
            clientX: x,
            clientY: y,
          });

          dot.dispatchEvent(new PointerEvent('pointerdown', withCoords(startX, startY, 1)));
          document.dispatchEvent(new PointerEvent('pointermove', withCoords(endX, endY, 1)));
          document.dispatchEvent(new PointerEvent('pointerup', withCoords(endX, endY, 0)));
        }
        """,
        {
            "dotId": str(dot.id),
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
        },
    )

    dragged_x = page.evaluate(
        """
        (dotId) => document
          .querySelector('.signal-dot[data-dot-id="' + dotId + '"]')
          .style.getPropertyValue('--dot-x')
        """,
        str(dot.id),
    )

    assert dragged_x != initial_x


@pytest.mark.django_db(transaction=True)
def test_dragging_owned_dot_does_not_select_all_grid_labels(
        page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
        draggable_dot = Dot.objects.create(x=52, y=45, owner_user=jerry_with_explicit_teams)
        draggable_dot.teams.add(minimum_team_hierarchy["blue"])

        # Seed additional published labels so drag crosses multiple text nodes.
        label_dot_a = Dot.objects.create(x=30, y=70, owner_user=jerry_with_explicit_teams)
        label_dot_a.teams.add(minimum_team_hierarchy["blue"])
        label_dot_b = Dot.objects.create(x=70, y=20, owner_user=jerry_with_explicit_teams)
        label_dot_b.teams.add(minimum_team_hierarchy["blue"])

        login_jerry(page)

        dot_locator = page.locator(f'.signal-dot[data-dot-id="{draggable_dot.id}"]')
        expect(dot_locator).to_be_visible()

        page.evaluate("() => window.getSelection().removeAllRanges()")

        initial_x = page.evaluate(
                """
                (dotId) => document
                    .querySelector('.signal-dot[data-dot-id="' + dotId + '"]')
                    .style.getPropertyValue('--dot-x')
                """,
                str(draggable_dot.id),
        )

        dot_box = dot_locator.bounding_box()
        start_x = dot_box["x"] + dot_box["width"] / 2
        start_y = dot_box["y"] + dot_box["height"] / 2

        # Drag toward the upper-right edge through the dense label area.
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(start_x + 260, start_y - 190, steps=16)
        assert page.evaluate("() => document.body.classList.contains('signal-dragging')")
        page.mouse.up()
        assert not page.evaluate(
            "() => document.body.classList.contains('signal-dragging')"
        )

        dragged_x = page.evaluate(
                """
                (dotId) => document
                    .querySelector('.signal-dot[data-dot-id="' + dotId + '"]')
                    .style.getPropertyValue('--dot-x')
                """,
                str(draggable_dot.id),
        )
        assert dragged_x != initial_x

        selected_text = page.evaluate("() => window.getSelection().toString()")
        selection_is_collapsed = page.evaluate(
                """
                () => {
                    const selection = window.getSelection();
                    return !selection || selection.isCollapsed;
                }
                """
        )

        assert selection_is_collapsed
        assert selected_text.strip() == ""


@pytest.mark.django_db(transaction=True)
def test_dot_editor_dialog_has_cancel_button_and_no_close_button(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=55, y=35, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("button", name="Cancel")).to_be_visible()
    expect(dialog.get_by_role("button", name="Close")).to_have_count(0)

    dialog.get_by_role("button", name="Cancel").click()
    expect(dialog).not_to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_dot_editor_dialog_does_not_autofocus_private(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=57, y=43, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()
    private_checkbox = dialog.get_by_label("Private")
    expect(private_checkbox).not_to_be_focused()


@pytest.mark.django_db(transaction=True)
def test_dot_editor_dialog_closes_on_escape(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=45, y=45, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_clicking_dot_opens_dialog_without_creating_new_dot(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=50, y=50, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    target_dot = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(target_dot).to_be_visible()

    dots = page.locator(".signal-dot")
    initial_count = dots.count()

    target_dot.click()

    expect(page.locator("dialog#dot-editor-dialog")).to_be_visible()
    expect(dots).to_have_count(initial_count)


@pytest.mark.django_db(transaction=True)
def test_saving_team_selection_in_dialog_updates_dot(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=40, y=60, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()

    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()

    dialog.get_by_label("Deep red").check()
    dialog.get_by_label("Blue").uncheck()
    dialog.get_by_role("button", name="Save").click()

    expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == {
        minimum_team_hierarchy["deep_red"].id
    }


@pytest.mark.django_db(transaction=True)
def test_unchecking_all_teams_auto_selects_private(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=63, y=26, owner_user=jerry_with_explicit_teams)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

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

    dot.refresh_from_db()
    assert set(dot.teams.values_list("id", flat=True)) == set()


@pytest.mark.django_db(transaction=True)
def test_deleting_owned_dot_removes_it_from_the_grid(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=63, y=26)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.evaluate(
        "([dotId, token]) => localStorage.setItem('dotTokens', JSON.stringify({[dotId]: token}))",
        [str(dot.id), str(dot.ownership_token)],
    )
    page.reload(wait_until="domcontentloaded")

    dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(dot_locator).to_be_visible()
    dot_locator.click()

    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("button", name="Delete")).to_be_visible()

    dialog.get_by_role("button", name="Delete").click()

    expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)
    expect(page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')).to_have_count(0)

    assert not Dot.objects.filter(id=dot.id).exists()


@pytest.mark.django_db(transaction=True)
def test_saving_dot_updates_published_label_without_reload(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=63, y=26)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.evaluate(
        "([dotId, token]) => localStorage.setItem('dotTokens', JSON.stringify({[dotId]: token}))",
        [str(dot.id), str(dot.ownership_token)],
    )
    page.reload(wait_until="domcontentloaded")

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


@pytest.mark.django_db(transaction=True)
def test_saving_dot_shows_transient_published_notification(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=51, y=44)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    page.evaluate(
        "([dotId, token]) => localStorage.setItem('dotTokens', JSON.stringify({[dotId]: token}))",
        [str(dot.id), str(dot.ownership_token)],
    )
    page.reload(wait_until="domcontentloaded")

    page.locator(f'.signal-dot[data-dot-id="{dot.id}"]').click()
    dialog = page.locator("dialog#dot-editor-dialog")
    expect(dialog).to_be_visible()

    dialog.get_by_role("button", name="Save").click()
    expect(page.locator("dialog#dot-editor-dialog")).to_have_count(0)

    transient_label = page.locator(".signal-dot-label").last
    expect(transient_label).to_be_visible()
    expect(transient_label).to_contain_text("Published to")
    expect(transient_label).to_contain_text(f"Claim token: {dot.claim_token}")
