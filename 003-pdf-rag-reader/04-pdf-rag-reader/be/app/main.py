"""FastAPI application factory. Run with uvicorn app.main:create_app --factory."""
import logging
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from app.services.ingestion_service import IngestionService
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app.config import Settings
from app.api.chat import router as chat_router
from app.services.chat_service import ChatService
from app.errors import APIError
from app.api.documents import router as documents_router
from app.storage.repositories import ChatRepository, DocumentRepository

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal['ok'] = 'ok'



def error_response(status: int, code: str, message: str, headers=None):
    return JSONResponse(
        status_code=status,
        content={'error': {'code': code, 'message': message}},
        headers=headers,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(app.state.ingestion.recover)
        yield

    app = FastAPI(title='PDF RAG API', docs_url='/api-docs', redoc_url=None, lifespan=lifespan)
    app.state.settings = settings if settings is not None else Settings()
    app.state.documents = DocumentRepository(app.state.settings.data_dir)
    app.state.ingestion = IngestionService(app.state.settings, app.state.documents)
    app.state.chat_history = ChatRepository(app.state.settings.data_dir)

    app.state.chat = ChatService(app.state.settings, app.state.documents, app.state.chat_history)

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

    app.include_router(documents_router)
    app.include_router(chat_router)
    return app
