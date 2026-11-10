"""OIDC bearer-token validation and role checks."""

import logging
import time

import httpx
import jwt
from fastapi import Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app import settings
from app.errors import ApiError, error_response
from app.roles import has_role, roles_for_groups

log = logging.getLogger("team_insights.auth")
_jwks_cache: dict[str, object] = {"keys": None, "fetched_at": 0.0}
JWKS_TTL_SECONDS = 300


def signing_keys() -> jwt.PyJWKSet:
    now = time.time()
    if _jwks_cache["keys"] is None or now - float(_jwks_cache["fetched_at"]) > JWKS_TTL_SECONDS:
        config = httpx.get(f"{settings.OIDC_ISSUER}/.well-known/openid-configuration").json()
        _jwks_cache["keys"] = jwt.PyJWKSet.from_dict(httpx.get(config["jwks_uri"]).json())
        _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]  # type: ignore[return-value]


def validate_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    key = signing_keys()[header["kid"]]
    return jwt.decode(
        token,
        key.key,
        algorithms=["RS256"],
        audience=settings.OIDC_AUDIENCE,
        issuer=settings.OIDC_ISSUER,
    )


class TokenValidationMiddleware(BaseHTTPMiddleware):
    """Every /api request needs a valid bearer token from the identity provider."""

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return error_response(401, "unauthenticated", "Sign in first.")
        try:
            claims = validate_token(auth.split(" ", 1)[1])
        except (jwt.PyJWTError, KeyError) as exc:
            log.info("rejected token: %s", type(exc).__name__)
            return error_response(401, "invalid_token", "The access token isn't valid.")
        request.state.user = claims["sub"]
        request.state.roles = roles_for_groups(claims.get("groups", []))
        return await call_next(request)


def require_role(role: str):
    def check(request: Request) -> str:
        if not has_role(request.state.roles, role):
            raise ApiError(403, "forbidden", f"This needs the {role} role.")
        return request.state.user

    return Depends(check)
