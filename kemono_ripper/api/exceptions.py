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
    EINTERNAL = -1
    EARGS = -2
    EAGAIN = -3
    ERATELIMIT = -4
    EFAILED = -5
    ETOOMANY = -6
    ERANGE = -7
    EEXPIRED = -8
    ENOENT = -9
    ECIRCULAR = -10
    EACCESS = -11
    EEXIST = -12
    EINCOMPLETE = -13
    EKEY = -14
    ESID = -15
    EBLOCKED = -16
    EOVERQUOTA = -17
    ETEMPUNAVAIL = -18
    ETOOMANYCONNECTIONS = -19
    EWRITE = -20
    EREAD = -21
    EAPPKEY = -22
    KEMONO_ERROR_CODE_GENERIC = -255

    def __str__(self) -> str:
        return f'{self.name} ({self.value:d})'


KEMONO_ERROR_DESCRIPTION: dict[KemonoErrorCodes, tuple[str, str]] = {
    KemonoErrorCodes.ESUCCESS: ('ESUCCESS', 'Opration completed successfully'),
    KemonoErrorCodes.EINTERNAL: ('EINTERNAL',
                                 ('An internal error has occurred. Please submit a bug report, '
                                  'detailing the exact circumstances in which this error occurred')),
    KemonoErrorCodes.EARGS: ('EARGS', 'You have passed invalid arguments to this command'),
    KemonoErrorCodes.EAGAIN: ('EAGAIN',
                              ('A temporary congestion or server malfunction prevented your request from being processed. '
                               'No data was altered. Retry')),
    KemonoErrorCodes.ERATELIMIT: ('ERATELIMIT',
                                  ('You have exceeded your command weight per time quota. Please wait a few seconds, then try again '
                                   '(this should never happen in sane real-life applications)')),
    KemonoErrorCodes.EFAILED: ('EFAILED', 'The upload failed. Please restart it from scratch'),
    KemonoErrorCodes.ETOOMANY: ('ETOOMANY', 'Too many concurrent IP addresses are accessing this upload target URL'),
    KemonoErrorCodes.ERANGE: ('ERANGE', 'The upload file packet is out of range or not starting and ending on a chunk boundary'),
    KemonoErrorCodes.EEXPIRED: ('EEXPIRED', 'The upload target URL you are trying to access has expired. Please request a fresh one'),
    KemonoErrorCodes.ENOENT: ('ENOENT', 'Object (typically, node or user) not found'),
    KemonoErrorCodes.ECIRCULAR: ('ECIRCULAR', 'Circular linkage attempted'),
    KemonoErrorCodes.EACCESS: ('EACCESS', 'Access violation (e.g., trying to write to a read-only share)'),
    KemonoErrorCodes.EEXIST: ('EEXIST', 'Trying to create an object that already exists'),
    KemonoErrorCodes.EINCOMPLETE: ('EINCOMPLETE', 'Trying to access an incomplete resource'),
    KemonoErrorCodes.EKEY: ('EKEY', 'A decryption operation failed (never returned by the API)'),
    KemonoErrorCodes.ESID: ('ESID', 'Invalid or expired user session, please relogin'),
    KemonoErrorCodes.EBLOCKED: ('EBLOCKED', 'User blocked'),
    KemonoErrorCodes.EOVERQUOTA: ('EOVERQUOTA', 'Request over quota'),
    KemonoErrorCodes.ETEMPUNAVAIL: ('ETEMPUNAVAIL', 'Resource temporarily not available, please try again later'),
    KemonoErrorCodes.ETOOMANYCONNECTIONS: ('ETOOMANYCONNECTIONS', 'many connections on this resource'),
    KemonoErrorCodes.EWRITE: ('EWRITE', 'Write failed'),
    KemonoErrorCodes.EREAD: ('EREAD', 'Read failed'),
    KemonoErrorCodes.EAPPKEY: ('EAPPKEY', 'Invalid application key; request not processed'),
    # fallback
    KemonoErrorCodes.KEMONO_ERROR_CODE_GENERIC: ('EGENERIC', 'Unknown error'),
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
            if self.code in KEMONO_ERROR_DESCRIPTION:
                err_name, err_desc = KEMONO_ERROR_DESCRIPTION[self.code]
            else:
                err = KEMONO_ERROR_DESCRIPTION[KemonoErrorCodes.KEMONO_ERROR_CODE_GENERIC]
                err_name = err[0]
                err_desc = err[1] % (self.code if isinstance(self.code, int) else self.code.value)
            self.message = f'{err_name}, {err_desc}'
        else:
            self.code = KemonoErrorCodes.KEMONO_ERROR_CODE_GENERIC
            self.message = str(msg_or_code)

    def __str__(self) -> str:
        return self.message

    __repr__ = __str__

#
#
#########################################
