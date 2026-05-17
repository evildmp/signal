def test_visiting_application_presents_login_dialog(client):
    response = client.get("/", follow=True)

    assert response.status_code == 200
    assert any(url.startswith("/login/") for url, _ in response.redirect_chain)
    assert b"Log in" in response.content


def test_can_log_in_as_jerry_with_password_jerry(client, django_user_model):
    django_user_model.objects.create_user(username="jerry", password="jerry")

    response = client.post(
        "/login/",
        {"username": "jerry", "password": "jerry"},
        follow=True,
    )

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == "/"
    assert response.wsgi_request.user.is_authenticated
