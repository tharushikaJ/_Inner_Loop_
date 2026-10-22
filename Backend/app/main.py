from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes.admin_routes import router as admin_router
from .routes.auth_routes import router as auth_router
from .routes.dashboard_routes import router as dashboard_router
from .routes.meeting_routes import router as meeting_router
from .routes.notification_routes import router as notification_router
from .routes.project_routes import router as project_router
from .routes.report_routes import router as report_router
from .routes.room_routes import router as room_router
from .routes.task_routes import router as task_router
from .routes.user_routes import router as user_router

app = FastAPI(title="InnerLoop API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(meeting_router)
app.include_router(notification_router)
app.include_router(room_router)
app.include_router(report_router)
app.include_router(user_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "innerloop-backend"}
