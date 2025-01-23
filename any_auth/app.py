import logging

from logging_bullet_train import set_logger

from any_auth.build_app import build_app
from any_auth.config import Settings
from any_auth.logger_name import LOGGER_NAME

logger = logging.getLogger(__name__)

set_logger(LOGGER_NAME, level=logging.DEBUG)

Settings.probe_required_environment_variables()

app_settings = Settings()  # type: ignore
app = build_app(settings=app_settings)
