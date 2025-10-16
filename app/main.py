from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import auth as auth_router
from .routers import users as users_router
from .routers import meetings as meetings_router
from .routers import config as config_router
from .routers import logs as logs_router
from .routers import health as health_router
from . import ws as ws_module


def create_app() -> FastAPI:
    app = FastAPI(title="BaapMeet Backend", version="1.0.0")

    # CORS (adjust origins as needed)
    # CORS: allow cross-origin requests from any frontend. We use header tokens
    # (no cookies), so credentials are not required; this enables Access-Control-Allow-Origin: *
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=".*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )

    # Routers
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(meetings_router.router)
    app.include_router(config_router.router)
    app.include_router(logs_router.router)
    app.include_router(ws_module.router)
    app.include_router(health_router.router)

    @app.on_event("startup")
    def on_startup():
        # Auto-create tables at startup
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
