from django.urls import path

from .views import (
    home,
    create_dot,
    delete_dot,
    dot_claim,
    dot_edit,
    move_dot,
    dismiss_signal_onboarding,
)

urlpatterns = [
    path("", home, name="home"),
    path("dot/create/", create_dot, name="create_dot"),
    path("dot/<int:dot_id>/move/", move_dot, name="move_dot"),
    path("dot/<int:dot_id>/delete/", delete_dot, name="delete_dot"),
    path("dot/<int:dot_id>/claim/", dot_claim, name="dot_claim"),
    path("dot/<int:dot_id>/edit/", dot_edit, name="dot_edit"),
    path(
        "onboarding/signal/dismiss/",
        dismiss_signal_onboarding,
        name="dismiss_signal_onboarding",
    ),
]
