from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import traceback
import logging

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(f"Unhandled error: {exc}\n{traceback.format_exc()}")
            # Respond with stack trace and error details
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Internal server error",
                    "details": traceback.format_exc(),
                }
            )


def add_error_middleware(app: FastAPI):
    app.add_middleware(ErrorHandlingMiddleware)
