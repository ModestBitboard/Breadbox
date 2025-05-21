#
# User types:
#     everyone      - Everyone, including people who aren't logged in, but excluding blocked IPs.
#     users         - Someone with an account with the default auth level (1)
#     contributors  - Someone with an account with a higher auth level (2)
#     admin         - The site admin's account, which has the highest auth level (3)
#     nobody        - That feature may as well not exist and will return HTTP 403 to everyone, including admins
#
# Permission types:
#     read  - Can make GET requests to the /api endpoint
#     write - Can make POST, PUT, and PATCH requests to the /api endpoint
#     delete - Can perform DELETE requests
#
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from typing import Callable, Optional

from breadbox.core.config import Config
from breadbox.core.responses import respond
from breadbox.core.logger import log

rate_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=Config.rate_limits.rules,
    enabled=Config.rate_limits.enabled
)

query_params_blacklist = []

if Config.advanced.auth_query:
    query_params_blacklist.append(Config.advanced.auth_query)

class PermissionMiddleware(BaseHTTPMiddleware):
    def __init__(self, *args, user_handler: Callable[[str,], tuple[str, int]] = None, **kwargs):
        self.user_handler = user_handler
        super().__init__(*args, **kwargs)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith(Config.advanced.protected_prefixes):
            # Read
            if request.method in ('GET', 'HEAD',):
                if resp := self.check_permissions(request, Config.permissions.read):
                    return resp

            # Write
            elif request.method in ('PUT', 'PATCH', 'POST',):
                if Config.advanced.read_only:
                    return respond('read_only')
                elif resp := self.check_permissions(request, Config.permissions.write):
                    return resp

            # Delete
            elif request.method in ('DELETE',):
                if Config.advanced.read_only:
                    return respond('read_only')
                elif resp := self.check_permissions(request, Config.permissions.delete):
                    return resp

            # Other
            else:
                if resp := self.check_permissions(request, Config.permissions.other):
                    return resp

        response = await call_next(request)
        return response

    def check_permissions(self, request: Request, permission_group: str) -> Optional[JSONResponse]:
        if permission_group == 'everyone':
            return None

        elif permission_group == 'nobody':
            return respond('disabled_feature')

        if Config.advanced.auth_header and (api_key := request.headers.get(Config.advanced.auth_header)):
            pass
        elif Config.advanced.auth_cookie and (api_key := request.cookies.get(Config.advanced.auth_cookie)):
            pass
        elif Config.advanced.auth_query and (api_key := request.query_params.get(Config.advanced.auth_query)):
            pass
        else:
            return respond('no_api_key')

        username, auth_level = self.user_handler(api_key)
        if not username and not auth_level:
            return respond('invalid_api_key')

        if permission_group == 'users':
            if auth_level >= 1:
                pass
            else:
                return respond('insufficient_permissions')

        elif permission_group == 'contributors':
            if auth_level >= 2:
                pass
            else:
                return respond('insufficient_permissions')

        elif permission_group == 'admin':
            if auth_level == 3:
                pass
            else:
                return respond('insufficient_permissions')

        else:
            raise ValueError("Unknown permission group: '%s'" % permission_group)

        log.info(f"{username}@{request.client.host} -> [{request.method}] {request.url.remove_query_params(query_params_blacklist)}")
        return None
