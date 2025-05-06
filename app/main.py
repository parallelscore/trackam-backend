import time
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.middleware import register_middlewares
from app.api.models.model_init import create_all_tables
from app.api.routes.server_metrics import ServerMetrics

from app.api.routes.user import UserRouter
from app.api.routes.login import LoginRouter
from app.api.routes.rider import RiderRouter
from app.api.routes.profile import ProfileRouter
from app.api.routes.customer import CustomerRouter
from app.api.routes.register import RegisterRouter
from app.api.routes.delivery import DeliveryRouter
from app.api.routes.analytics import AnalyticsRouter
from app.api.routes.websocket import WebSocketRouter

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

    # Mount static files directory
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)  # Create the directory if it doesn't exist
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Add dashboard route
    @app.get("/dashboard", include_in_schema=False)
    async def get_metrics_dashboard():
        dashboard_path = Path(__file__).parent / "static" / "metrics-dashboard.html"
        return FileResponse(str(dashboard_path))

    server_metrics_router = ServerMetrics(app).router

    user_router = UserRouter().router_manager.router
    login_router = LoginRouter().router_manager.router
    rider_router = RiderRouter().router_manager.router
    profile_router = ProfileRouter().router_manager.router
    register_router = RegisterRouter().router_manager.router
    delivery_router = DeliveryRouter().router_manager.router
    customer_router = CustomerRouter().router_manager.router
    analytic_router = AnalyticsRouter().router_manager.router
    websocket_router = WebSocketRouter().router_manager.router

    # Register the routers
    app.include_router(server_metrics_router)

    app.include_router(user_router, prefix=settings.API_V1_STR)
    app.include_router(login_router, prefix=settings.API_V1_STR)
    app.include_router(rider_router, prefix=settings.API_V1_STR)
    app.include_router(profile_router, prefix=settings.API_V1_STR)
    app.include_router(register_router, prefix=settings.API_V1_STR)
    app.include_router(delivery_router, prefix=settings.API_V1_STR)
    app.include_router(analytic_router, prefix=settings.API_V1_STR)
    app.include_router(customer_router, prefix=settings.API_V1_STR)
    app.include_router(websocket_router, prefix=settings.API_V1_STR)

    # Include WebSocket router
    app.include_router(websocket_router, prefix=settings.API_V1_STR)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)  # pragma: no cover