import logging

from any_auth.logger_name import LOGGER_NAME
from any_auth.version import VERSION

__version__ = VERSION
__logger_name__ = LOGGER_NAME

logger = logging.getLogger(__logger_name__)
