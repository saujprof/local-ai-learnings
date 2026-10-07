"""FastAPI application factory. Run with uvicorn app.main:create_app --factory."""
import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.config import Settings

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal['ok'] = 'ok'


class APIError(Exception):
    """Expected application error with a safe public message."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str, headers=None):
    return JSONResponse(
        status_code=status,
        content={'error': {'code': code, 'message': message}},
        headers=headers,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title='PDF RAG API', docs_url='/api-docs', redoc_url=None)
    app.state.settings = settings if settings is not None else Settings()

    @app.exception_handler(APIError)
    async def application_error(_request: Request, exc: APIError):
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError):
        return error_response(422, 'validation_error', 'Request validation failed. Check the request fields.')

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        codes = {404: 'not_found', 405: 'method_not_allowed'}
        return error_response(exc.status_code, codes.get(exc.status_code, 'http_error'),
                              str(exc.detail), exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, exc: Exception):
        logger.error('Unhandled API error', exc_info=exc)
        return error_response(500, 'internal_error', 'An unexpected error occurred.')

    @app.get('/health', response_model=HealthResponse, tags=['health'])
    async def health():
        # Liveness only: external services are introduced in later units.
        return HealthResponse()

    return app
