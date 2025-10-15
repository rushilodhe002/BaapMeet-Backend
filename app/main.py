from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware

from .database import engine, Base
from .routers import auth as auth_router
from .routers import users as users_router
from .routers import meetings as meetings_router
from .routers import config as config_router
from .routers import logs as logs_router
from . import ws as ws_module


def create_app() -> FastAPI:
    app = FastAPI(title="BaapMeet Backend", version="1.0.0")

    # CORS (adjust origins as needed)
    # Explicitly allow production frontend origins and enable credentials.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://main.d12345.amplifyapp.com",  # TODO: replace with your Amplify domain
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,
    )

    # Respect X-Forwarded-* headers from ALB/Nginx for correct scheme/host/ip
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    # Routers
    app.include_router(auth_router.router)
    app.include_router(users_router.router)
    app.include_router(meetings_router.router)
    app.include_router(config_router.router)
    app.include_router(logs_router.router)
    app.include_router(ws_module.router)

    @app.on_event("startup")
    def on_startup():
        # Auto-create tables at startup
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
