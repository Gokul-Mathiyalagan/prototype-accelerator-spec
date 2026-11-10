"""App wiring: logging, request IDs, token validation, routes and the built web app."""

from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import settings
from app.api import teams
from app.auth import TokenValidationMiddleware
from app.errors import ApiError, handle_api_error
from app.logging_setup import configure_logging, new_request_id
from app.seed import seed

configure_logging()
app = FastAPI(title="Team Insights API", version="0.4.0")
app.add_middleware(TokenValidationMiddleware)
app.add_exception_handler(ApiError, handle_api_error)
app.include_router(teams.router)

WEB_DIST = Path(__file__).resolve().parent.parent / "static"


@app.middleware("http")
async def request_ids(request: Request, call_next):
    rid = new_request_id(request.headers.get("x-request-id"))
    response = await call_next(request)
    response.headers["x-request-id"] = rid
    return response


@app.on_event("startup")
def startup() -> None:
    seed()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


if settings.AUTH_MODE == "mock":

    @app.post("/auth/token")
    def mock_sign_in(body: dict) -> dict:
        """Local runs only: forward a username to the mock IdP and return its token."""
        reply = httpx.post(f"{settings.OIDC_ISSUER}/token", json=body, timeout=10)
        reply.raise_for_status()
        return reply.json()


if WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        return FileResponse(WEB_DIST / "index.html")
