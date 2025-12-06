# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
import re
from argparse import ArgumentError
from ipaddress import IPv4Address

from aiohttp import ClientTimeout
from yarl import URL

from .api import APIAddress, APIService, PostPageScanResult
from .defs import (
    CONNECT_TIMEOUT_BASE,
    CONNECT_TIMEOUT_SOCKET_READ,
    LOGGING_FLAGS,
    MAX_JOBS_MAX,
    NumRange,
)
from .logger import Log
from .util import build_regex_from_pattern

re_post_page = re.compile(fr'({"|".join(APIAddress.__args__)})/({"|".join(APIService.__args__)})(?:/user/(\d+))?/post/(\w+)')


def valid_kwarg(kwarg: str) -> tuple[str, str]:
    try:
        k, v = tuple(kwarg.split('=', 1))
        return k, v
    except Exception:
        raise ArgumentError


def valid_number(val: str, *, lb: int | float | None = None, ub: int | float | None = None, nonzero=False, rfloat=False) -> int | float:
    try:
        val = float(val) if rfloat else int(val)
        assert lb is None or val >= lb
        assert ub is None or val <= ub
        assert nonzero is False or val != 0
        return val
    except Exception:
        raise ArgumentError


def positive_int(val: str) -> int:
    return valid_number(val, lb=0)


def nonzero_int(val: str) -> int:
    return valid_number(val, nonzero=True)


def positive_nonzero_int(val: str) -> int:
    return valid_number(val, lb=1)


def valid_path(pathstr: str, *, is_file: bool) -> pathlib.Path:
    try:
        newpath = pathlib.Path(pathstr.strip('\'"')).expanduser().absolute()
        assert newpath.is_file() if is_file else next(reversed(newpath.parents)).is_dir()
        return newpath
    except Exception:
        raise ArgumentError


def valid_folder_path(pathstr: str) -> pathlib.Path:
    return valid_path(pathstr, is_file=False)


def valid_file_path(pathstr: str) -> pathlib.Path:
    return valid_path(pathstr, is_file=True)


def valid_proxy(prox: str) -> str:
    from ctypes import c_uint16, sizeof
    try:
        if not prox:
            return prox
        try:
            pt, pv = tuple(prox.split('://', 1))
        except ValueError:
            Log.error('Failed to split proxy type and value/port!')
            raise
        if pt not in {'http', 'socks4', 'socks5', 'socks5h'}:
            Log.error(f'Invalid proxy type: \'{pt}\'!')
            raise ValueError
        try:
            pv, pp = tuple(pv.rsplit(':', 1))
        except ValueError:
            Log.error('Failed to split proxy address and port!')
            raise
        try:
            pup, pvv = tuple(pv.rsplit('@', 1)) if ('@' in pv) else ('', pv)
            if pup:
                pup = f'{pup}@'
        except ValueError:
            Log.error('Failed to split proxy address and port!')
            raise
        try:
            pva = IPv4Address(pvv)
        except ValueError:
            Log.error(f'Invalid proxy ip address value \'{pv}\'!')
            raise
        try:
            ppi = int(pp)
            assert 20 < ppi < 2 ** (8 * sizeof(c_uint16))
        except (ValueError, AssertionError):
            Log.error(f'Invalid proxy port value \'{pp}\'!')
            raise
        return f'{pt}://{pup}{pva!s}:{ppi:d}'
    except Exception:
        raise ArgumentError


def valid_url(url_str: str) -> URL:
    try:
        url = URL(url_str)
        assert url.is_absolute()
        assert url.host in APIAddress.__args__
        return url
    except Exception:
        raise ArgumentError


def valid_post_url(url_str: str, absolute=True) -> PostPageScanResult:
    try:
        url = URL(url_str)
        if absolute:
            assert url.is_absolute()
        if url.is_absolute():
            assert url.host in APIAddress.__args__
        else:
            assert url_str.startswith(APIAddress.__args__)
        post_page_match = re_post_page.search(str(url))
        api_address = post_page_match.group(1)
        service = post_page_match.group(2)
        cid = positive_int(post_page_match.group(3))
        pid = post_page_match.group(4)
        assert pid
        return PostPageScanResult(pid, cid, service, api_address)
    except Exception:
        raise ArgumentError(None, '')


def log_level(level: str) -> int:
    try:
        return int(LOGGING_FLAGS[level], 16)
    except Exception:
        raise ArgumentError


def valid_timeout(timeout: str) -> ClientTimeout:
    try:
        timeout_int = positive_nonzero_int(timeout) if timeout else CONNECT_TIMEOUT_BASE
        return ClientTimeout(total=None, connect=timeout_int, sock_connect=timeout_int, sock_read=float(CONNECT_TIMEOUT_SOCKET_READ))
    except Exception:
        raise ArgumentError


def valid_maxjobs(maxjobs_str: str) -> int:
    return valid_number(maxjobs_str, lb=1, ub=MAX_JOBS_MAX)


def valid_indent(indent_str: str) -> int:
    return valid_number(indent_str, lb=0, ub=4)


def valid_range(range_str: str) -> NumRange:
    try:
        range_str = range_str or f'0-{2 ** 40:d}'
        parts = range_str.split('-', maxsplit=2)
        assert len(parts) == 2
        rmin = valid_number(parts[0], lb=0.0, ub=float(2 ** 40), rfloat=True)
        rmax = valid_number(parts[1], lb=rmin, ub=float(2 ** 40), rfloat=True)
        return NumRange(rmin, rmax)
    except Exception:
        raise ArgumentError


def valid_pattern(pattern_str: str) -> str:
    try:
        _ = build_regex_from_pattern(pattern_str)
        return pattern_str
    except Exception:
        raise ArgumentError

#
#
#########################################
