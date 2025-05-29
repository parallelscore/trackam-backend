# app/api/routes/base_router.py
from fastapi import APIRouter, status, WebSocket
from typing import Callable, List, Optional
import re

from app.utils.logging_util import setup_logger


class RouterManager:
    """
    A router manager class that encapsulates common functionalities for FastAPI routers.

    This class provides:
      - A generic method to add HTTP routes (GET, POST, etc.)
      - A method to add WebSocket routes
      - Unified exception handling
      - Logging for errors and standard operations

    Attributes
    ----------
    router : APIRouter
        The FastAPI router instance.
    logger : logging.Logger
        The logger instance for logging information and errors.
    """

    def __init__(self):
        self.router = APIRouter()
        self.logger = setup_logger(__name__)

    def add_route(
            self,
            path: str,
            handler_method: Callable,
            methods: List[str] = None,
            tags: Optional[List[str]] = None,
            status_code: Optional[int] = status.HTTP_200_OK,
            route_type: str = "http"
    ):
        """
        Adds a route to the APIRouter with unified exception handling.

        Parameters
        ----------
        path : str
            The path for the API endpoint (e.g., "/items").
        handler_method : Callable
            The async function that will handle the request.
        methods : List[str], optional
            A list of HTTP methods (e.g. ["GET", "POST"]). Defaults to ["POST"].
            Ignored for WebSocket routes.
        tags : List[str], optional
            Tags for categorizing the API route. Defaults to an empty list.
        status_code : int, optional
            The HTTP status code returned on success. Defaults to 200 (OK).
            Ignored for WebSocket routes.
        route_type : str, optional
            The type of route: "http" or "websocket". Defaults to "http".
        """
        if methods is None:
            methods = ["POST"]  # Default method if none provided
        if tags is None:
            tags = []

        if route_type.lower() == "websocket":
            self._add_websocket_route(path, handler_method, tags)
        else:
            self._add_http_route(path, handler_method, methods, tags, status_code)

    def _add_http_route(
            self,
            path: str,
            handler_method: Callable,
            methods: List[str],
            tags: List[str],
            status_code: int
    ):
        """
        Add an HTTP route to the router.
        """
        self.router.add_api_route(
            path=path,
            endpoint=handler_method,
            methods=methods,
            tags=tags,
            status_code=status_code
        )
        self.logger.info(f"Added HTTP route: {methods} {path}")

    def _add_websocket_route(
            self,
            path: str,
            handler_method: Callable,
            tags: List[str]
    ):
        """
        Add a WebSocket route to the router.
        """
        # Extract path parameters from the path using regex
        path_params = re.findall(r'\{(\w+)\}', path)

        # Create a wrapper function that properly handles the WebSocket connection
        # and passes the correct parameters to the handler method
        if len(path_params) == 0:
            # No path parameters
            async def websocket_endpoint(websocket: WebSocket):
                await handler_method(websocket)
        elif len(path_params) == 1:
            # One path parameter (most common case - like {tracking_id})
            param_name = path_params[0]
            if param_name == 'tracking_id':
                async def websocket_endpoint(websocket: WebSocket, tracking_id: str):
                    await handler_method(websocket, tracking_id)
            else:
                # Generic single parameter
                async def websocket_endpoint(websocket: WebSocket, path_param: str):
                    await handler_method(websocket, path_param)
        else:
            # Multiple path parameters - use **kwargs approach
            async def websocket_endpoint(websocket: WebSocket, **path_params_dict):
                # Convert path_params_dict to positional arguments in the order they appear in the path
                ordered_params = [path_params_dict[param] for param in path_params]
                await handler_method(websocket, *ordered_params)

        # Add the WebSocket route
        self.router.add_websocket_route(
            path=path,
            endpoint=websocket_endpoint
        )

        # Log the route addition
        if tags:
            self.logger.info(f"Added WebSocket route: {path} (tags: {', '.join(tags)})")
        else:
            self.logger.info(f"Added WebSocket route: {path}")

    def add_websocket(
            self,
            path: str,
            handler_method: Callable,
            tags: Optional[List[str]] = None
    ):
        """
        Convenience method to add a WebSocket route.

        Parameters
        ----------
        path : str
            The path for the WebSocket endpoint (e.g., "/ws/delivery/{tracking_id}").
        handler_method : Callable
            The async function that will handle the WebSocket connection.
            Should accept websocket as first parameter, followed by any path parameters.
        tags : List[str], optional
            Tags for categorizing the WebSocket route. Defaults to an empty list.
        """
        if tags is None:
            tags = []

        self.add_route(
            path=path,
            handler_method=handler_method,
            tags=tags,
            route_type="websocket"
        )