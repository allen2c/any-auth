import logging
import uuid

import fastapi
import fastapi.exception_handlers
import fastapi.exceptions

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: fastapi.Request, exc: fastapi.exceptions.RequestValidationError
) -> fastapi.responses.Response:
    rand_id = str(uuid.uuid4()).split("-")[0]

    # Log a general warning about the validation error for the request path
    logger.warning(
        f"[{rand_id}] Validation error on request to '{request.url.path}'. "
        + f"Method: '{request.method}', Headers: '{request.headers}'"
    )

    # Log each individual error detail in its own warning line
    for error in exc.errors():
        loc = " -> ".join(str(item) for item in error.get("loc", []))
        msg = error.get("msg", "Unknown error")
        error_type = error.get("type", "Unknown type")
        input_info = f", input: {error.get('input')}" if "input" in error else ""
        logger.warning(
            f"[{rand_id}] Error detail - "
            + f"at '{loc}': {msg} (type: {error_type}{input_info})"
        )

    # Log the request body separately, if available
    try:
        body = await request.body()
        body_str = body.decode("utf-8")
    except Exception:
        body_str = "unavailable"
    logger.warning(f"[{rand_id}] Request payload: {body_str}")

    # Return the default 422 response to the client
    return await fastapi.exception_handlers.request_validation_exception_handler(
        request, exc
    )
