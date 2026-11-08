from django.db import connection
from ninja import NinjaAPI

from accounts.api import router as accounts_router
from access.api import router as access_router
from certifications.api import router as certifications_router
from scheduling.api import router as scheduling_router

api = NinjaAPI(title="SiteFlow API", version="0.1.0")


@api.get("/health")
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return {"status": "ok", "database": "ok"}

    except Exception:
        return {"status": "degraded", "database": "down"}
    
api.add_router("/" , accounts_router)
api.add_router("/", access_router)
api.add_router("/", certifications_router)
api.add_router("/", scheduling_router)