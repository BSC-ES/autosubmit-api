"""Maps domain exceptions to HTTP responses."""

from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from autosubmit_api.exceptions import NotFoundError, ValidationError
from autosubmit_api.logger import logger


def _error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        content={"error": True, "error_message": message},
        status_code=status_code,
    )


def _format_request_validation_error(exc: RequestValidationError) -> str:
    """
    Builds a message from a request validation error.
    """
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"][1:]) or "request"
        detail = error["msg"].removeprefix("Value error, ")
        messages.append(f"Invalid value for '{location}': {detail}")

    return "; ".join(messages) or "Invalid request."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(_format_request_validation_error(exc), status_code=422)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(str(exc), status_code=404)

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return _error_response(str(exc), status_code=400)

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(
        request: Request, exc: FastAPIHTTPException
    ) -> JSONResponse:
        return _error_response(exc.detail, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled exception while processing the request", exc_info=True)
        return _error_response("An unexpected error occurred.", status_code=500)
