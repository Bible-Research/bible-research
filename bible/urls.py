from django.urls import path
from . import views

urlpatterns = [
    path('bible/', views.BiblePassageView.as_view(), name='bible-passage'),
    path(
        'bible/translations/',
        views.TranslationListView.as_view(),
        name='translation-list'
    ),
    path(
        'bible/timestamps/',
        views.AudioTimestampView.as_view(),
        name='audio-timestamps'
    ),
]
