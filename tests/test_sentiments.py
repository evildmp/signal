import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from app.models import ACTION_SENTIMENTS, Dot, FEELINGS



@pytest.mark.django_db
def test_action_sentiment_option_list_includes_expected_items():
    assert "I wish I could talk to someone" in ACTION_SENTIMENTS
    assert "I need help" in ACTION_SENTIMENTS
    assert "I would love to talk about this" in ACTION_SENTIMENTS
    assert "I would like people to know" in ACTION_SENTIMENTS
    assert "I don't know how to talk about this" in ACTION_SENTIMENTS
    assert "I hope I can talk to someone who has experienced the same thing" in ACTION_SENTIMENTS
    assert "I would be really happy to share my news" in ACTION_SENTIMENTS


@pytest.mark.django_db
def test_dot_feeling_can_have_single_value():
    dot = Dot.objects.create(x=50, y=50, feeling=[FEELINGS[0]])
    assert dot.feeling == [FEELINGS[0]]


@pytest.mark.django_db
def test_dot_feeling_can_have_multiple_values():
    dot = Dot.objects.create(x=50, y=50, feeling=FEELINGS[:3])
    assert dot.feeling == FEELINGS[:3]


@pytest.mark.django_db
def test_dot_feeling_defaults_to_empty_list():
    dot = Dot.objects.create(x=50, y=50)
    assert dot.feeling == []


@pytest.mark.django_db
def test_dot_rejects_invalid_feeling_values():
    dot = Dot(x=50, y=50, feeling=["Not in list"])

    with pytest.raises(ValidationError):
        dot.full_clean()


@pytest.mark.django_db
def test_dot_feeling_free_text_defaults_to_empty():
    dot = Dot.objects.create(x=50, y=50)
    assert dot.feeling_free_text == ""


@pytest.mark.django_db
def test_dot_can_have_feeling_free_text():
    dot = Dot.objects.create(x=50, y=50)
    dot.feeling_free_text = "Something indescribable"
    dot.save()
    dot.refresh_from_db()
    assert dot.feeling_free_text == "Something indescribable"


@pytest.mark.django_db
def test_dot_action_sentiment_can_have_single_value():
    dot = Dot.objects.create(x=50, y=50, action_sentiment=[ACTION_SENTIMENTS[0]])
    assert dot.action_sentiment == [ACTION_SENTIMENTS[0]]


@pytest.mark.django_db
def test_dot_action_sentiment_defaults_to_empty_list():
    dot = Dot.objects.create(x=50, y=50)
    assert dot.action_sentiment == []


@pytest.mark.django_db
def test_dot_rejects_invalid_action_sentiment_values():
    dot = Dot(x=50, y=50, action_sentiment=["Not in list"])

    with pytest.raises(ValidationError):
        dot.full_clean()


@pytest.mark.django_db
def test_dot_action_sentiment_free_text_defaults_to_empty():
    dot = Dot.objects.create(x=50, y=50)
    assert dot.action_sentiment_free_text == ""


@pytest.mark.django_db
def test_dot_can_have_action_sentiment_free_text():
    dot = Dot.objects.create(x=50, y=50)
    dot.action_sentiment_free_text = "I need a coffee"
    dot.save()
    dot.refresh_from_db()
    assert dot.action_sentiment_free_text == "I need a coffee"


@pytest.mark.django_db
def test_dot_owner_user_defaults_to_null():
    dot = Dot.objects.create(x=50, y=50)
    assert dot.owner_user is None


@pytest.mark.django_db
def test_dot_can_set_owner_user():
    user = get_user_model().objects.create_user(username="alice", password="alice")
    dot = Dot.objects.create(x=50, y=50)
    dot.owner_user = user
    dot.save()
    dot.refresh_from_db()
    assert dot.owner_user == user
