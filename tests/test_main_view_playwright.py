import pytest
from playwright.sync_api import expect


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
