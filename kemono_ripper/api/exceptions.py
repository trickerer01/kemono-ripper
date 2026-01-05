# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from enum import IntEnum


class KemonoErrorCodes(IntEnum):
    ESUCCESS = 0
    EEXISTS = 1
    ENOTFOUND = -1
    ECONNECT = -2
    ESIZE = -3

    def __str__(self) -> str:
        return f'{self.name} ({self.value:d})'


KEMONO_ERROR_DESCRIPTION: dict[KemonoErrorCodes, tuple[str, str]] = {
    KemonoErrorCodes.ESUCCESS: ('ESUCCESS', 'Operation completed successfully'),
    KemonoErrorCodes.EEXISTS: ('EEXISTS', 'File already exists'),
    KemonoErrorCodes.ENOTFOUND: ('ENOTFOUND', 'No post, creator or file exists at pointed URL'),
    KemonoErrorCodes.ECONNECT: ('ECONNECT', 'General connection error'),
    KemonoErrorCodes.ESIZE: ('ESIZE', 'Downloaded file size mismatch'),
}


class KemonoAPIError(Exception):
    """Generic kemono API error"""


class ValidationError(KemonoAPIError):
    """Error in validation stage"""


class KemonoArgumentError(KemonoAPIError):
    """Invalid cmdline input"""


class RequestError(KemonoAPIError):
    def __init__(self, msg_or_code: str | int | KemonoErrorCodes) -> None:
        if isinstance(msg_or_code, (int, KemonoErrorCodes)):
            self.code = msg_or_code
            assert self.code in KEMONO_ERROR_DESCRIPTION
            self.message = KEMONO_ERROR_DESCRIPTION[self.code][1]
        else:
            self.code = -255
            self.message = str(msg_or_code)

    def __str__(self) -> str:
        return f'[{self.code!s}] {self.message}'

    __repr__ = __str__

#
#
#########################################
