from .log import logger_factory
from .nurse import nurse_handler_factory

l_middleware = [logger_factory, nurse_handler_factory]
