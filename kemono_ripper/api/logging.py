# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from typing import Protocol

__all__ = ('Log', 'Logger', 'set_logger')


class Logger(Protocol):
    @staticmethod
    def log(text: str) -> None: ...
    @staticmethod
    def fatal(text: str) -> None: ...
    @staticmethod
    def error(text: str) -> None: ...
    @staticmethod
    def warn(text: str) -> None: ...
    @staticmethod
    def info(text: str) -> None: ...
    @staticmethod
    def debug(text: str) -> None: ...
    @staticmethod
    def trace(text: str) -> None: ...


class Log:
    logger = Logger

    @staticmethod
    def fatal(text: str) -> None:
        Log.logger.fatal(text)

    @staticmethod
    def error(text: str) -> None:
        Log.logger.error(text)

    @staticmethod
    def warn(text: str) -> None:
        Log.logger.warn(text)

    @staticmethod
    def info(text: str) -> None:
        Log.logger.info(text)

    @staticmethod
    def debug(text: str) -> None:
        Log.logger.debug(text)

    @staticmethod
    def trace(text: str) -> None:
        Log.logger.trace(text)


def set_logger(logger: Logger) -> None:
    Log.logger = logger

#
#
#########################################
