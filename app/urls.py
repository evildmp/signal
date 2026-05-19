from django.urls import path

from .views import home, create_dot

urlpatterns = [
    path('', home, name='home'),
    path('dot/create/', create_dot, name='create_dot'),
]
