from django.urls import path

from .views import home, create_dot, dot_edit

urlpatterns = [
    path('', home, name='home'),
    path('dot/create/', create_dot, name='create_dot'),
    path('dot/<str:identifier>/edit/', dot_edit, name='dot_edit'),
]
