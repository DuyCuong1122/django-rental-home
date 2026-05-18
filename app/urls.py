from django.urls import include, path
from ninja import NinjaAPI

from app.api.auth import auth_router
from app.api.profile import profile_router
from app.api.room import room_router
from app.api.search import search_router
from app.api.appointment import appointment_router

api = NinjaAPI(title="Rental House Platform API", version="1.0.0")

@api.get("/health")
def health_check(request):
    return {"status": "ok"}

api.add_router("/auth", auth_router)
api.add_router("/profile", profile_router)
api.add_router("/rooms", room_router)
api.add_router("/search", search_router)
api.add_router("/appointments", appointment_router)

urlpatterns = [
    path("api/v1/upload/", include("apps.upload.urls")),
    path("api/v1/", api.urls),
]
