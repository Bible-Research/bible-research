from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'notes', views.NoteViewSet, basename='note')
router.register(
    r'notes/(?P<note_pk>[^/.]+)/comments',
    views.CommentViewSet,
    basename='comment',
)

urlpatterns = [
    path('', include(router.urls)),
]
