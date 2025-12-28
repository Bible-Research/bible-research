from django.urls import path
from . import views

urlpatterns = [
    path('bible/passage/', views.BiblePassageView.as_view(), name='bible-passage'),
    path(
        'bible/translations/',
        views.TranslationListView.as_view(),
        name='translation-list'
    ),
]
