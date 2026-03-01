from django.urls import path
from .views import register_user, current_user

urlpatterns = [
    path('register/', register_user, name='user-register'),
    path('me/', current_user, name='current-user'),
]
