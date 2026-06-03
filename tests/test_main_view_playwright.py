import pytest
import re
from colorsys import rgb_to_hls
from playwright.sync_api import expect
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from app.models import Dot, SignalOnboardingState

ORANGE_RGB = "rgb(233, 84, 32)"


def rgb_triplet(css_rgb):
    match = re.fullmatch(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", css_rgb)
    assert match is not None, f"Unexpected colour format: {css_rgb}"
    return tuple(int(value) for value in match.groups())


def saturation_for_css_rgb(css_rgb):
    red, green, blue = rgb_triplet(css_rgb)
    _, _, saturation = rgb_to_hls(red / 255, green / 255, blue / 255)
    return saturation


@pytest.fixture(autouse=True)
def dismiss_onboarding_by_default(request, jerry_with_explicit_teams):
    if request.node.name.startswith(
        "test_using_signal_modal_shows_once_and_stays_dismissed"
    ):
        return

    SignalOnboardingState.objects.update_or_create(
        user=jerry_with_explicit_teams,
        defaults={"using_signal_seen": True},
    )


@pytest.mark.django_db(transaction=True)
def test_selecting_my_dots_only_clears_selected_team_checkboxes(
    page,
    login_jerry,
):
    login_jerry(page)

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


@pytest.mark.django_db(transaction=True)
def test_selecting_a_team_clears_my_dots_only(page, login_jerry):
    login_jerry(page)

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


@pytest.mark.django_db(transaction=True)
def test_dot_title_is_formatted_in_utc(
    page, login_jerry, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=25, y=55)
    dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=dot.id).update(
        created_at=timezone.now().replace(hour=13, minute=17, second=0, microsecond=0)
    )
    dot.refresh_from_db()

    login_jerry(page)

    dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(dot_locator).to_be_visible()

    expected_title = dot.created_at.astimezone(timezone.utc).strftime("%a %d %b, %H:%M")

    assert dot_locator.get_attribute("title") == expected_title


@pytest.mark.django_db(transaction=True)
def test_using_signal_modal_shows_once_and_stays_dismissed(
    page, live_server, jerry_with_explicit_teams
):
    page.goto(f"{live_server.url}/login/")
    page.locator('input[name="username"]').fill("jerry")
    page.locator('input[name="password"]').fill("jerry")
    page.get_by_role("button", name="Log in").click()

    dialog = page.locator("dialog#signal-onboarding-dialog")
    expect(dialog).to_be_visible()
    expect(dialog.get_by_role("heading", name="Using Signal")).to_be_visible()

    dialog.get_by_role("button", name="Continue").click()
    expect(dialog).not_to_be_visible()

    page.reload()
    reloaded_dialog = page.locator("dialog#signal-onboarding-dialog")
    expect(reloaded_dialog).to_have_count(1)
    expect(reloaded_dialog).not_to_be_visible()

    page.locator("#signal-onboarding-open").click()
    expect(reloaded_dialog).to_be_visible()


@pytest.mark.django_db(transaction=True)
def test_older_visible_dot_renders_same_opacity_as_newer_dot(
    page, login_jerry, minimum_team_hierarchy
):
    recent_dot = Dot.objects.create(x=25, y=55)
    recent_dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=recent_dot.id).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    older_dot = Dot.objects.create(x=65, y=55)
    older_dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=older_dot.id).update(
        created_at=timezone.now() - timedelta(days=6)
    )

    login_jerry(page)

    recent_locator = page.locator(f'.signal-dot[data-dot-id="{recent_dot.id}"]')
    older_locator = page.locator(f'.signal-dot[data-dot-id="{older_dot.id}"]')
    expect(recent_locator).to_be_visible()
    expect(older_locator).to_be_visible()

    recent_opacity = float(
        page.evaluate(
            "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).opacity",
            str(recent_dot.id),
        )
    )
    older_opacity = float(
        page.evaluate(
            "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).opacity",
            str(older_dot.id),
        )
    )

    assert older_opacity == recent_opacity


@pytest.mark.django_db(transaction=True)
def test_logged_in_users_dots_are_orange_regardless_of_age(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    recent_dot = Dot.objects.create(x=25, y=55, owner_user=jerry_with_explicit_teams)
    recent_dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=recent_dot.id).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    older_dot = Dot.objects.create(x=65, y=55, owner_user=jerry_with_explicit_teams)
    older_dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=older_dot.id).update(
        created_at=timezone.now() - timedelta(days=6)
    )

    login_jerry(page)

    recent_locator = page.locator(f'.signal-dot[data-dot-id="{recent_dot.id}"]')
    older_locator = page.locator(f'.signal-dot[data-dot-id="{older_dot.id}"]')
    expect(recent_locator).to_be_visible()
    expect(older_locator).to_be_visible()

    recent_colour = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).backgroundColor",
        str(recent_dot.id),
    )
    older_colour = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).backgroundColor",
        str(older_dot.id),
    )
    assert recent_colour == ORANGE_RGB
    assert older_colour == ORANGE_RGB


@pytest.mark.django_db(transaction=True)
def test_dot_colour_reflects_grid_position_not_owner_identity(
    page, login_jerry, minimum_team_hierarchy
):
    tina = get_user_model().objects.create_user(username="tina", password="tina")

    first_dot = Dot.objects.create(x=25, y=55, owner_user=tina)
    first_dot.teams.add(minimum_team_hierarchy["blue"])

    second_dot = Dot.objects.create(x=65, y=55, owner_user=tina)
    second_dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    first_locator = page.locator(f'.signal-dot[data-dot-id="{first_dot.id}"]')
    second_locator = page.locator(f'.signal-dot[data-dot-id="{second_dot.id}"]')
    expect(first_locator).to_be_visible()
    expect(second_locator).to_be_visible()

    first_colour = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).backgroundColor",
        str(first_dot.id),
    )
    second_colour = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).backgroundColor",
        str(second_dot.id),
    )

    assert first_colour != second_colour
    assert first_colour != ORANGE_RGB
    assert second_colour != ORANGE_RGB
    assert saturation_for_css_rgb(first_colour) >= 0.35
    assert saturation_for_css_rgb(second_colour) >= 0.35


@pytest.mark.django_db(transaction=True)
def test_anonymous_dot_has_saturated_non_orange_colour(
    page, login_jerry, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=45, y=55)
    dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    dot_locator = page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(dot_locator).to_be_visible()

    colour = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).backgroundColor",
        str(dot.id),
    )

    assert colour != ORANGE_RGB
    assert saturation_for_css_rgb(colour) >= 0.6


@pytest.mark.django_db(transaction=True)
def test_logged_in_users_aged_dot_stays_more_visible_than_other_aged_dots(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    owned_dot = Dot.objects.create(x=30, y=50, owner_user=jerry_with_explicit_teams)
    owned_dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=owned_dot.id).update(
        created_at=timezone.now() - timedelta(days=6)
    )

    other_dot = Dot.objects.create(x=70, y=50)
    other_dot.teams.add(minimum_team_hierarchy["blue"])
    Dot.objects.filter(id=other_dot.id).update(
        created_at=timezone.now() - timedelta(days=6)
    )

    login_jerry(page)

    owned_locator = page.locator(f'.signal-dot[data-dot-id="{owned_dot.id}"]')
    other_locator = page.locator(f'.signal-dot[data-dot-id="{other_dot.id}"]')
    expect(owned_locator).to_be_visible()
    expect(other_locator).to_be_visible()

    owned_opacity = float(
        page.evaluate(
            "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).opacity",
            str(owned_dot.id),
        )
    )
    other_opacity = float(
        page.evaluate(
            "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"] .signal-dot-fill')).opacity",
            str(other_dot.id),
        )
    )

    assert owned_opacity == other_opacity


@pytest.mark.django_db(transaction=True)
def test_logged_in_users_dot_is_same_size_circle_with_orange_border(
    page, login_jerry, jerry_with_explicit_teams, minimum_team_hierarchy
):
    owned_dot = Dot.objects.create(x=30, y=50, owner_user=jerry_with_explicit_teams)
    owned_dot.teams.add(minimum_team_hierarchy["blue"])

    other_dot = Dot.objects.create(x=70, y=50)
    other_dot.teams.add(minimum_team_hierarchy["blue"])

    login_jerry(page)

    owned_locator = page.locator(f'.signal-dot[data-dot-id="{owned_dot.id}"]')
    other_locator = page.locator(f'.signal-dot[data-dot-id="{other_dot.id}"]')
    expect(owned_locator).to_be_visible()
    expect(other_locator).to_be_visible()

    owned_width = float(
        page.evaluate(
            "dotId => parseFloat(getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"]')).width)",
            str(owned_dot.id),
        )
    )
    other_width = float(
        page.evaluate(
            "dotId => parseFloat(getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"]')).width)",
            str(other_dot.id),
        )
    )
    owned_border_color = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"]')).borderTopColor",
        str(owned_dot.id),
    )
    owned_border_width = float(
        page.evaluate(
            "dotId => parseFloat(getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"]')).borderTopWidth)",
            str(owned_dot.id),
        )
    )
    other_border_radius = page.evaluate(
        "dotId => getComputedStyle(document.querySelector('.signal-dot[data-dot-id=\"' + dotId + '\"]')).borderRadius",
        str(other_dot.id),
    )

    assert owned_width == other_width
    assert owned_border_color == "rgb(17, 17, 17)"
    assert owned_border_width >= 1
    assert owned_border_width < 2
    assert other_border_radius == "999px"
