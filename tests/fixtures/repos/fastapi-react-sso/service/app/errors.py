"""One error envelope for every API error: {"error": {code, message, request_id}}."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.logging_setup import request_id


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "request_id": request_id.get()}}
    return JSONResponse(status_code=status, content=body)


async def handle_api_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return error_response(exc.status, exc.code, exc.message)
