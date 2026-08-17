import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import account, admin, auth, billing, consumer, meter, portal, reading, services, tenants, territory, users, vee
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(tenants.router)
app.include_router(services.router)
app.include_router(territory.router)
app.include_router(account.router)
app.include_router(meter.router)
app.include_router(consumer.router)
app.include_router(reading.router)
app.include_router(vee.router)
app.include_router(billing.router)
app.include_router(portal.router)
app.include_router(users.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
