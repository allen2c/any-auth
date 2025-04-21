import logging

import fastapi
import fastapi.exception_handlers
import fastapi.exceptions
from logging_bullet_train import set_logger

from any_auth.build_app import build_app
from any_auth.config import Settings
from any_auth.logger_name import LOGGER_NAME
from any_auth.utils.exception_handlers import validation_exception_handler

logger = logging.getLogger(__name__)

set_logger(LOGGER_NAME, level=logging.DEBUG)
set_logger("cachetic", level=logging.DEBUG)

Settings.probe_required_environment_variables()

app_settings = Settings()  # type: ignore
app = build_app(settings=app_settings)

# Add the custom exception handler to your FastAPI app
app.add_exception_handler(
    fastapi.exceptions.RequestValidationError,
    validation_exception_handler,  # type: ignore
)
