import re

import pytest
from django.test import override_settings
from django.utils.html import escape
from playwright.sync_api import expect

from app.models import Dot, Team


def extract_dot_id_from_create_response(content):
    match = re.search(r'data-dot-id="(\d+)"', content)
    assert match is not None, "create_dot response did not include data-dot-id"
    return int(match.group(1))


@pytest.mark.django_db
def test_dot_ownership_token_is_generated_on_creation():
    dot = Dot.objects.create(x=10, y=20)

    assert dot.ownership_token is not None


@pytest.mark.django_db
def test_dot_claim_token_is_generated_on_creation():
    dot = Dot.objects.create(x=10, y=20)

    assert dot.claim_token is not None
    assert isinstance(dot.claim_token, str)
    assert len(dot.claim_token) > 0


@pytest.mark.django_db
def test_dot_ownership_token_is_unique():
    first = Dot.objects.create(x=10, y=20)
    second = Dot.objects.create(x=30, y=40)

    assert first.ownership_token != second.ownership_token


@pytest.mark.django_db
def test_create_dot_endpoint_publishes_to_user_explicit_teams(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)

    response = client.post(
        "/dot/create/",
        {"x": "42", "y": "73"},
    )

    assert response.status_code == 200

    content = response.content.decode()
    dot_id = extract_dot_id_from_create_response(content)
    dot = Dot.objects.get(id=dot_id)
    assert dot.x == 42
    assert dot.y == 73

    explicit_team_names = sorted(
        Team.objects.explicit_for_user(jerry_with_explicit_teams).values_list(
            "name", flat=True
        )
    )
    dot_team_names = sorted(dot.teams.values_list("name", flat=True))
    assert dot_team_names == explicit_team_names

    # Notification mentions the explicit teams
    for team_name in explicit_team_names:
        assert team_name in content


@pytest.mark.django_db
def test_create_dot_response_includes_home_dot_attributes(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)

    response = client.post(
        "/dot/create/",
        {"x": "42", "y": "73"},
    )

    assert response.status_code == 200
    content = response.content.decode()
    dot_id = extract_dot_id_from_create_response(content)
    dot = Dot.objects.get(id=dot_id)

    # Keep inline create-dot output aligned with home-view dot wiring.
    assert f'data-dot-id="{dot.id}"' in content
    assert 'class="signal-dot' in content
    assert 'data-owned-by-user="1"' in content
    assert f'hx-get="/dot/{dot.id}/edit/"' in content


@pytest.mark.django_db
def test_create_dot_response_escapes_team_names_in_notification(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)

    explicit_team = Team.objects.explicit_for_user(jerry_with_explicit_teams).first()
    explicit_team.name = 'Blue <script>alert("x")</script> & team'
    explicit_team.save(update_fields=["name"])

    response = client.post(
        "/dot/create/",
        {"x": "42", "y": "73"},
    )

    assert response.status_code == 200
    content = response.content.decode()

    escaped_name = escape(explicit_team.name)
    assert escaped_name in content
    assert explicit_team.name not in content


@pytest.mark.django_db
def test_create_dot_requires_login(client):
    response = client.post(
        "/dot/create/",
        {"x": "42", "y": "73"},
    )

    assert response.status_code == 302
    assert response.url.startswith("/login/")


@pytest.mark.django_db
def test_create_dot_rejects_invalid_coordinates(client, jerry_with_explicit_teams):
    client.force_login(jerry_with_explicit_teams)

    before_count = Dot.objects.count()

    response = client.post(
        "/dot/create/",
        {"x": "150", "y": "-1"},
    )

    assert response.status_code == 400
    assert Dot.objects.count() == before_count


@pytest.mark.django_db
def test_move_dot_endpoint_updates_coordinates(client, jerry_with_explicit_teams):
    client.force_login(jerry_with_explicit_teams)
    dot = Dot.objects.create(x=10, y=20)

    response = client.post(
        f"/dot/{dot.id}/move/",
        {"x": "72", "y": "64", "ownership_token": str(dot.ownership_token)},
    )

    assert response.status_code == 200
    dot.refresh_from_db()
    assert dot.x == 72
    assert dot.y == 64


@pytest.mark.django_db
def test_move_dot_endpoint_rejects_invalid_coordinates(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)
    dot = Dot.objects.create(x=10, y=20)

    response = client.post(
        f"/dot/{dot.id}/move/",
        {"x": "999", "y": "-2", "ownership_token": str(dot.ownership_token)},
    )

    assert response.status_code == 400
    dot.refresh_from_db()
    assert dot.x == 10
    assert dot.y == 20


@pytest.mark.django_db
def test_move_dot_endpoint_rejects_wrong_ownership_token(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)
    dot = Dot.objects.create(x=10, y=20)

    response = client.post(
        f"/dot/{dot.id}/move/",
        {"x": "50", "y": "50", "ownership_token": "not-the-right-token"},
    )

    assert response.status_code == 403
    dot.refresh_from_db()
    assert dot.x == 10
    assert dot.y == 20


@pytest.mark.django_db
def test_move_dot_endpoint_allows_user_with_owner_relation_without_ownership_token(
    client, jerry_with_explicit_teams
):
    client.force_login(jerry_with_explicit_teams)
    dot = Dot.objects.create(x=10, y=20, owner_user=jerry_with_explicit_teams)

    response = client.post(f"/dot/{dot.id}/move/", {"x": "72", "y": "64"})

    assert response.status_code == 200
    dot.refresh_from_db()
    assert dot.x == 72
    assert dot.y == 64


@pytest.mark.django_db(transaction=True)
def test_clicking_grid_places_a_dot_and_shows_notification(
    authenticated_page,
):
    grid = authenticated_page.locator(".signal-grid")
    expect(grid).to_be_visible()

    initial_dot_count = authenticated_page.locator(".signal-dot").count()

    # Click near the top-left corner
    bounding_box = grid.bounding_box()
    authenticated_page.mouse.click(
        bounding_box["x"] + bounding_box["width"] * 0.1,
        bounding_box["y"] + bounding_box["height"] * 0.1,
    )

    expect(authenticated_page.locator(".signal-dot")).to_have_count(initial_dot_count + 1)

    label = authenticated_page.locator(".signal-dot-label")
    expect(label).to_be_visible()
    expect(label).to_contain_text("Blue")
    expect(label).to_contain_text("Deep red")

    # Label near top-left should go to the right of the dot
    class_attr = label.get_attribute("class")
    assert "signal-dot-label--x-right" in class_attr


@pytest.mark.django_db(transaction=True)
def test_newly_created_dot_gets_claimed_styling_from_ownership_token(
    authenticated_page,
):
    grid = authenticated_page.locator(".signal-grid")
    expect(grid).to_be_visible()

    initial_dot_count = authenticated_page.locator(".signal-dot").count()
    bounding_box = grid.bounding_box()
    authenticated_page.mouse.click(
        bounding_box["x"] + bounding_box["width"] * 0.4,
        bounding_box["y"] + bounding_box["height"] * 0.6,
    )

    expect(authenticated_page.locator(".signal-dot")).to_have_count(initial_dot_count + 1)

    new_dot = authenticated_page.locator(".signal-dot").last
    expect(new_dot).to_have_class(re.compile(r"\bsignal-dot--claimed\b"))

    border_color = authenticated_page.evaluate(
        "el => getComputedStyle(el).borderTopColor",
        new_dot.element_handle(),
    )
    assert border_color == "rgb(17, 17, 17)"


@pytest.mark.django_db(transaction=True)
def test_label_positions_near_edges(authenticated_page):
    """Labels near grid edges should flip position to stay visible."""

    grid = authenticated_page.locator(".signal-grid")
    expect(grid).to_be_visible()
    bb = grid.bounding_box()

    # Click near bottom-right -> label should be to the left of the dot
    authenticated_page.mouse.click(bb["x"] + bb["width"] * 0.95, bb["y"] + bb["height"] * 0.95)
    label = authenticated_page.locator(".signal-dot-label").last
    expect(label).to_be_visible()
    class_attr = label.get_attribute("class")
    assert "signal-dot-label--x-left" in class_attr


@pytest.mark.django_db(transaction=True)
def test_label_is_entirely_below_dot_when_dot_is_at_top_of_grid(
    authenticated_page,
):
    """When a dot is placed at the very top of the grid, every part of the
    label must be below (greater screen y than) the bottom of the dot."""

    grid = authenticated_page.locator(".signal-grid")
    expect(grid).to_be_visible()
    bb = grid.bounding_box()

    initial_count = authenticated_page.locator(".signal-dot").count()

    # Click at 50% x, 2px from the top edge -> y coordinate near 100
    authenticated_page.mouse.click(bb["x"] + bb["width"] * 0.5, bb["y"] + 2)

    # Wait for the new dot and label to appear
    expect(authenticated_page.locator(".signal-dot")).to_have_count(initial_count + 1)

    dot = authenticated_page.locator(".signal-dot").last
    label = authenticated_page.locator(".signal-dot-label").last

    expect(label).to_be_visible()

    dot_bb = dot.bounding_box()
    label_bb = label.bounding_box()

    # The top of the label must be at or below the bottom of the dot
    assert label_bb["y"] >= dot_bb["y"] + dot_bb["height"], (
        f"Label top ({label_bb['y']:.1f}) is above dot bottom "
        f"({dot_bb['y'] + dot_bb['height']:.1f}) - label overlaps or is above the dot"
    )


@pytest.mark.django_db(transaction=True)
def test_dragging_dot_moves_it_without_creating_new_dot(
    authenticated_page, minimum_team_hierarchy
):
    # Create a dot via the browser so the ownership token is stored in localStorage.
    grid = authenticated_page.locator(".signal-grid")
    bb = grid.bounding_box()
    authenticated_page.mouse.click(bb["x"] + bb["width"] * 0.25, bb["y"] + bb["height"] * 0.75)
    expect(authenticated_page.locator(".signal-dot")).to_have_count(1)

    dot_locator = authenticated_page.locator(".signal-dot").first
    dot_id = dot_locator.get_attribute("data-dot-id")

    token_before_refresh = authenticated_page.evaluate(
        "(id) => JSON.parse(localStorage.getItem('dotTokens') || '{}')[id] || null",
        dot_id,
    )
    assert token_before_refresh is not None

    authenticated_page.reload()
    expect(authenticated_page.locator(".signal-dot")).to_have_count(1)

    initial_dots = authenticated_page.locator(".signal-dot").count()

    dot_box = dot_locator.bounding_box()
    authenticated_page.mouse.move(
        dot_box["x"] + dot_box["width"] / 2, dot_box["y"] + dot_box["height"] / 2
    )
    authenticated_page.mouse.down()
    authenticated_page.mouse.move(dot_box["x"] + 120, dot_box["y"] - 90)
    authenticated_page.mouse.up()

    expect(authenticated_page.locator(".signal-dot")).to_have_count(initial_dots)

    from app.models import Dot as DotModel

    moved_dot = DotModel.objects.get(id=int(dot_id))
    assert moved_dot.x != 25 or moved_dot.y != 75  # position should have changed


@pytest.mark.django_db(transaction=True)
def test_dragging_not_owned_dot_does_nothing(
    authenticated_page, minimum_team_hierarchy
):
    dot = Dot.objects.create(x=25, y=75)
    dot.teams.add(minimum_team_hierarchy["blue"])

    authenticated_page.reload()

    dot_locator = authenticated_page.locator(f'.signal-dot[data-dot-id="{dot.id}"]')
    expect(dot_locator).to_be_visible()
    initial_dots = authenticated_page.locator(".signal-dot").count()

    token = authenticated_page.evaluate(
        "(id) => JSON.parse(localStorage.getItem('dotTokens') || '{}')[id] || null",
        str(dot.id),
    )
    assert token is None

    style_before = dot_locator.get_attribute("style")
    dot_box = dot_locator.bounding_box()
    authenticated_page.mouse.move(
        dot_box["x"] + dot_box["width"] / 2, dot_box["y"] + dot_box["height"] / 2
    )
    authenticated_page.mouse.down()
    authenticated_page.mouse.move(dot_box["x"] + 120, dot_box["y"] - 90)
    authenticated_page.mouse.up()

    style_after = dot_locator.get_attribute("style")
    assert style_after == style_before
    expect(authenticated_page.locator(".signal-dot")).to_have_count(initial_dots)

    dot.refresh_from_db()
    assert dot.x == 25
    assert dot.y == 75


@pytest.mark.django_db(transaction=True)
def test_dragging_on_grid_background_does_not_create_dot(
    authenticated_page,
):
    grid = authenticated_page.locator(".signal-grid")
    expect(grid).to_be_visible()
    initial_dots = authenticated_page.locator(".signal-dot").count()

    bb = grid.bounding_box()
    start_x = bb["x"] + bb["width"] * 0.2
    start_y = bb["y"] + bb["height"] * 0.7
    end_x = bb["x"] + bb["width"] * 0.8
    end_y = bb["y"] + bb["height"] * 0.3

    authenticated_page.mouse.move(start_x, start_y)
    authenticated_page.mouse.down()
    authenticated_page.mouse.move(end_x, end_y)
    authenticated_page.mouse.up()

    expect(authenticated_page.locator(".signal-dot")).to_have_count(initial_dots)
