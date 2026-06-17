from django.urls import path

from health import views

urlpatterns = [
    path("live", views.live),
    path("ready", views.ready),
]
