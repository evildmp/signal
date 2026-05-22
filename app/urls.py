from django.urls import path

from .views import home, create_dot, delete_dot, dot_edit, move_dot

urlpatterns = [
    path('', home, name='home'),
    path('dot/create/', create_dot, name='create_dot'),
    path('dot/<str:identifier>/move/', move_dot, name='move_dot'),
    path('dot/<str:identifier>/delete/', delete_dot, name='delete_dot'),
    path('dot/<str:identifier>/edit/', dot_edit, name='dot_edit'),
]
