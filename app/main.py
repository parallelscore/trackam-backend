import time
import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.core.middleware import register_middlewares
from app.api.models.model_init import create_all_tables
from app.api.routes.server_metrics import ServerMetrics

from app.api.routes.user import UserRouter
from app.api.routes.login import LoginRouter
from app.api.routes.profile import ProfileRouter
from app.api.routes.register import RegisterRouter
from app.api.routes.delivery import DeliveryRouter
from app.api.routes.analytics import AnalyticsRouter

def create_app() -> FastAPI:

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
    )
    app.state.start_time = time.time()
    app.state.requests_processed = 0

    # Initialize database
    create_all_tables()

    # Register middleware
    register_middlewares(app)

    server_metrics_router = ServerMetrics(app).router

    user_router = UserRouter().router_manager.router
    login_router = LoginRouter().router_manager.router
    profile_router = ProfileRouter().router_manager.router
    register_router = RegisterRouter().router_manager.router
    delivery_router = DeliveryRouter().router_manager.router
    analytic_router = AnalyticsRouter().router_manager.router

    # Register the routers
    app.include_router(server_metrics_router)

    app.include_router(user_router, prefix=settings.API_V1_STR)
    app.include_router(login_router, prefix=settings.API_V1_STR)
    app.include_router(profile_router, prefix=settings.API_V1_STR)
    app.include_router(register_router, prefix=settings.API_V1_STR)
    app.include_router(delivery_router, prefix=settings.API_V1_STR)
    app.include_router(analytic_router, prefix=settings.API_V1_STR)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)  # pragma: no cover
