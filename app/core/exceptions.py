from typing import Callable, TypeVar, Awaitable, cast
import logging
from functools import wraps
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import NoResultFound, MultipleResultsFound, IntegrityError

logger = logging.getLogger(__name__)

ExcT = TypeVar('ExcT', bound=Exception)

def log_exception(
    func: Callable[[Request, ExcT], Awaitable[JSONResponse]]
) -> Callable[[Request, ExcT], Awaitable[JSONResponse]]:
    @wraps(func)
    async def wrapper(request: Request, exc: ExcT) -> JSONResponse:
        error_details = {
            "path": request.url.path,
            "method": request.method,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "handler": func.__name__,
        }

        if isinstance(exc, IntegrityError) and hasattr(exc, 'orig') and exc.orig is not None:
            error_details['orig_error'] = str(exc.orig)

        logger.error(
            f"Exception occurred: {exc.__class__.__name__} - {str(exc)}",
            extra=error_details
        )
        return await func(request, exc)
    return cast(Callable[[Request, ExcT], Awaitable[JSONResponse]], wrapper)

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(NoResultFound)
    @log_exception
    async def no_result_found_handler(_: Request, __: NoResultFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Resource not found"})

    @app.exception_handler(MultipleResultsFound)
    @log_exception
    async def multiple_results_handler(_: Request, __: MultipleResultsFound) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": "Multiple records found when only one was expected"})

    @app.exception_handler(IntegrityError)
    @log_exception
    async def integrity_error_handler(_: Request, exc: IntegrityError) -> JSONResponse:
        if "duplicate key" in str(exc.orig) or "UNIQUE constraint failed" in str(exc.orig):
            return JSONResponse(status_code=409, content={"detail": "Record already exists"})

        return JSONResponse(status_code=409, content={"detail": "Database integrity error"})
