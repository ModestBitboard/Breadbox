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

from datetime import datetime, timezone
import hmac
import hashlib
import base64
import json
import secrets

from breadbox.core.config import Config
from breadbox.core.responses import respond
from breadbox.core.logger import log

rate_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=Config.rate_limits.rules,
    enabled=Config.rate_limits.enabled
)

groups = {
    "users": 1,
    "contributors": 2,
    "admin": 3
}

# Tool for generating and verifying signed URLs
class HMACSigner:
    def __init__(self, key: bytes = None):
        if key:
            if len(key) < 64:
                log.warning(
                    "It is advised to use a key the same size as the hashing algorithm's output"
                    "in order to achieve the most security."
                )
            self.key = key
        else:
            self.key = secrets.token_bytes(64)

    def generate(self, obj: dict) -> str:
        """
        Produces an HMAC signature based off a dictionary of information.
        :param obj: The dictionary to derive the signature from.
        :return: The signature in url-safe Base64 format, with any '=' omitted.
        """
        # Format the dictionary in JSON
        plaintext = json.dumps(obj, sort_keys=True).encode('utf-8')

        # Generate the signature
        signature = hmac.new(self.key, plaintext, hashlib.sha512).digest()

        # Format the signature in URL-safe Base64.
        urlsafe_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

        return urlsafe_signature

    def verify(self, obj: dict, sig: str) -> bool:
        """
        Generates a new signature and compares it to the supplied one.
        :param obj: The dictionary to derive the signature from.
        :param sig: The signature to compare the results to.
        :return: True if the signatures match, otherwise false.
        """
        provided_signature = self.generate(obj)
        return hmac.compare_digest(provided_signature, sig)


# Middleware for managing security
class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, *args, user_handler: Callable[[str,], tuple[str, int],] = None, signed_url_key: bytes = None, **kwargs):
        self.user_handler = user_handler
        self.hmac_signer = HMACSigner(key=signed_url_key)

        super().__init__(*args, **kwargs)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith(Config.advanced.protected_prefixes):
            if 'signUrl' in request.query_params.keys():
                if resp := await self.api_key_auth(request, self.generate_signed_url):
                    return resp

                return respond('no_api_key')

            elif resp := await self.signature_auth(request, call_next):
                return resp
            elif resp := await self.api_key_auth(request, call_next):
                return resp

            return respond('auth_required')

        response = await call_next(request)
        return response

    async def generate_signed_url(self, request: Request) -> JSONResponse:
        if request.method != 'GET':
            return respond('signed_url_method')

        expires = int(datetime.now().timestamp()) + (Config.signed_urls.duration * 60)

        signature = self.hmac_signer.generate({
            "expires": expires,
            "ip": request.client.host,
            "url": request.url.path
        })

        return JSONResponse({
            "url": "%s?signature=%s&expires=%i" % (request.url.path, signature, expires),
            "expires_at": datetime.fromtimestamp(expires, tz=timezone.utc).isoformat(timespec='seconds'),
            "current_time": datetime.now(tz=timezone.utc).isoformat(timespec='seconds')
        })

    async def api_key_auth(self, request: Request, call_next: RequestResponseEndpoint) -> Optional[Response]:
        """
        Utilizes API keys for authentication
        """

        if Config.advanced.auth_header and (api_key := request.headers.get(Config.advanced.auth_header)):
            pass
        elif Config.advanced.auth_cookie and (api_key := request.cookies.get(Config.advanced.auth_cookie)):
            pass
        else:
            return None

        # Read
        if request.method in ('GET', 'HEAD',):
            permission_group = Config.permissions.read

        # Read only
        elif Config.advanced.read_only:
            return respond('read_only')

        # Write
        elif request.method in ('PUT', 'PATCH', 'POST',):
            permission_group = Config.permissions.write

        # Delete
        elif request.method in ('DELETE',):
            permission_group = Config.permissions.delete

        # Other
        else:
            permission_group = Config.permissions.other

        # If the permission is special, do special things.
        if permission_group == 'everyone':
            return await call_next(request)
        elif permission_group == 'nobody':
            return respond('disabled_feature')

        # Check if API key is valid and has the right permissions
        username, auth_level = self.user_handler(api_key)
        if not username and not auth_level:
            return respond('invalid_api_key')

        if not permission_group in groups.keys():
            raise ValueError("Unknown permission group: '%s'" % permission_group)

        if auth_level < groups[permission_group]:
            return respond('insufficient_permissions')

        log.info(f"{username}@{request.client.host} -> [{request.method}] {request.url}")
        return await call_next(request)

    async def signature_auth(self, request: Request, call_next: RequestResponseEndpoint) -> Optional[Response]:
        """
        Utilizes signed URLs for authentication
        """

        if not request.query_params.get('signature'):
            return None

        if request.method != 'GET':
            return respond('signed_url_method')

        signature = request.query_params.get('signature')
        expires = request.query_params.get('expires')

        if not expires and expires.isnumeric():
            return respond('url_signature_mismatch')

        expires = int(expires)

        if not self.hmac_signer.verify({
            "expires": expires,
            "ip": request.client.host,
            "url": request.url.path
        }, signature):
            return respond('url_signature_mismatch')

        now = int(datetime.now().timestamp())
        max_expires = now + (Config.signed_urls.duration * 60)

        if expires > max_expires:
            return respond('expires_too_late')

        if now > expires:
            return respond(
                'expired_url',
                expires_at=datetime.fromtimestamp(expires, tz=timezone.utc).isoformat(timespec='seconds'),
                current_time=datetime.fromtimestamp(now, tz=timezone.utc).isoformat(timespec='seconds')
            )

        response = await call_next(request)
        return response
