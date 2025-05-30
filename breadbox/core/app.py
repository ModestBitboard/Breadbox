"""
A WSGI server built using FastAPI
"""
from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import (
    get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
)

from slowapi.middleware import SlowAPIMiddleware

from contextlib import asynccontextmanager
from pathlib import Path
import importlib.util

from typing import Callable, Dict, Any

from breadbox.core.logger import log
from breadbox.core.config import Config, CONFIG_PATH
from breadbox.core.security import PermissionMiddleware, rate_limiter
from breadbox.core.archive import ArchiveRouter


# A helpful variable used to determine where the assets directory is.
ASSETS_PATH = Path(__file__).absolute().parent.parent / 'assets'

# Function to control app startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Generate the path to the archive handlers
    routers_dir = Path('./routers')

    app.tags = []

    log.info('Searching for routers in %s' % routers_dir.absolute())

    # Iterate through candidates
    for path in routers_dir.glob('*.py'):

        # Skip if it starts with an underscore
        if path.stem.startswith('_'):
            continue

        # Import the archive plugin
        spec = importlib.util.spec_from_file_location(path.stem, path)
        plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin)

        # Check if it has a router
        if not (hasattr(plugin, 'router') and isinstance(plugin.router, APIRouter)):
            log.warning('Failed to import router from %s' % path)
            continue

        log.info(f'Found router: [bold magenta]{path.stem}[/bold magenta]')

        # Set up tag metadata
        app.tags.append({
            "name": path.stem,
            "description": plugin.__doc__
        })

        if isinstance(plugin.router, ArchiveRouter):
            router_prefix = '/archive/' + path.stem
        else:
            router_prefix = '/' + path.stem

        app.include_router(
            plugin.router,
            prefix=router_prefix,
            tags=[path.stem]
        )

    log.info('Successfully completed automated setup.')
    yield

# Our main application class
class Breadbox(FastAPI):
    def __init__(
            self,
            user_db_handler: Callable[[str,], tuple[str, int]],
            *args,
            **kwargs
    ):
        """
        A self-generating WSGI application built for archives

        :param user_db_handler: Function for handling API keys. Takes in an API key and outputs a username and an auth level. Returns (None, None) if the provided API key is invalid.
        """
        # Aliases for convenience
        self.config = Config
        self.config_path = CONFIG_PATH

        # Check if OpenAPI is disabled in the config
        if Config.advanced.integrated_docs:
            openapi_url = '/openapi.json'
        else:
            openapi_url = None

        # Set up FastAPI application
        super().__init__(
            *args,
            title=Config.app.name,
            summary=Config.app.summary,
            version=Config.app.version,
            docs_url=None,
            redoc_url=None,
            openapi_url=openapi_url,
            lifespan=lifespan,
            **kwargs
        )

        # Initialize some variables
        self.tags = []

        # Install rate limiter
        self.state.limiter = rate_limiter
        # noinspection PyTypeChecker
        self.add_middleware(SlowAPIMiddleware)

        # Install permission middleware
        # noinspection PyTypeChecker
        self.add_middleware(PermissionMiddleware, user_handler=user_db_handler)

        # Mount static directory
        self.mount('/static', StaticFiles(directory=ASSETS_PATH), name="static")

        # Add built-in routes
        self.add_api_route(
            '/favicon.ico',
            self.favicon_redirect,
            methods=['GET'],
            include_in_schema=False
        )

        if Config.advanced.integrated_docs:
            self.add_api_route(
                '/docs',
                self.swagger_ui_html,
                methods=['GET'],
                include_in_schema=False
            )
            self.add_api_route(
                self.swagger_ui_oauth2_redirect_url,
                get_swagger_ui_oauth2_redirect_html,
                methods=['GET'],
                include_in_schema=False
            )

            # Disable rate limiting for Swagger UI
            self.state.limiter.exempt(self.swagger_ui_html)
            self.state.limiter.exempt(get_swagger_ui_oauth2_redirect_html)


    @staticmethod
    def favicon_redirect() -> RedirectResponse:
        return RedirectResponse('/static/favicon.ico')

    def openapi(self) -> Dict[str, Any]:
        if Config.advanced.cache_openapi and self.openapi_schema:
            return self.openapi_schema

        docs = ""

        if Config.app.flair:
            title = Config.app.flair + ' ' + self.title
        else:
            title = self.title

        if Config.rate_limits.enabled:
            docs += "\n## Rate Limiting\
            \nAfter you've passed the maximum number of requests, the server will refuse new connections \
            until enough time has passed.\n| **Requests** | **Duration** |\n|:---:|:---:|"

            for rate in Config.rate_limits.rules:
                requests, duration = rate.split('/')
                docs += "\n| %s | Per %s |" % (requests, duration)

        docs += f"\n## Security\
        \nSome endpoints of this server are secured using an API key.\
        This key can be sent through the following methods:\n"

        if Config.advanced.auth_header:
            docs += f"- Header: `{Config.advanced.auth_header}`\n"

        if Config.advanced.auth_cookie:
            docs += f"- Cookie: `{Config.advanced.auth_cookie}`\n"

        if Config.advanced.auth_query:
            docs += f"- Query Parameter: `{Config.advanced.auth_query}`\n"

        if Config.advanced.read_only:
            docs += "\n> ***Note: The archive is set to Read-only mode. Nobody can make changes at this time.***"
            title += ' (Read-Only)'

        docs += '\n\n---'

        if Config.app.show_watermark:
            docs += '\n\n[<img src="/static/powered-by.png" width="25%"/>](https://github.com/ModestBitboard/Breadbox)'

        openapi_schema = get_openapi(
            title=title,
            version=Config.app.version,
            summary=Config.app.summary,
            description=docs,
            tags=self.tags,
            routes=self.routes,
        )

        if not openapi_schema.get("components"):
            openapi_schema["components"] = {}

        elif not openapi_schema["components"].get("securitySchemes"):
            openapi_schema["components"]["securitySchemes"] = {}

        if not openapi_schema.get("security"):
            openapi_schema["security"] = []


        if Config.advanced.auth_header:
            openapi_schema["components"]["securitySchemes"]["APIKeyHeader"] = {
                "type": "apiKey",
                "in": "header",
                "name": Config.advanced.auth_header
            }
            openapi_schema["security"].append({
                "APIKeyHeader": []
            })

        if Config.advanced.auth_query:
            openapi_schema["components"]["securitySchemes"]["APIKeyQuery"] = {
                "type": "apiKey",
                "in": "query",
                "name": Config.advanced.auth_query
            }
            openapi_schema["security"].append({
                "APIKeyQuery": []
            })

        self.openapi_schema = openapi_schema
        return self.openapi_schema

    # noinspection PyUnusedLocal
    async def swagger_ui_html(self, request: Request):
        return get_swagger_ui_html(
            openapi_url=self.openapi_url,
            title=f"{self.title} - Swagger UI",
            oauth2_redirect_url=self.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
            swagger_favicon_url="/static/favicon.ico"
        )
