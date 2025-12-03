# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import datetime
import time
from collections.abc import Sized

START_TIME = datetime.datetime.now()


def get_time_seconds(timespan: str) -> int:
    """Converts time from **[hh:][mm:]ss** format to **seconds**"""
    return sum(int(part) * pow(60, idx) for idx, part in enumerate(reversed(timespan.split(':'))))


def format_time(seconds: int) -> str:
    """Formats time from seconds to: **hh:mm:ss**"""
    mm, ss = divmod(seconds, 60)
    hh, mm = divmod(mm, 60)
    return f'{hh:02d}:{mm:02d}:{ss:02d}'


def get_elapsed_time_i() -> int:
    """Returns time since launch in **seconds**"""
    return (datetime.datetime.now() - START_TIME).seconds


def get_elapsed_time_s() -> str:
    """Returns time since launch in format: **hh:mm:ss**"""
    return format_time(get_elapsed_time_i())


def get_local_time_i() -> int:
    """Returns **local** time since epoch in **seconds**"""
    return int(datetime.datetime.now().timestamp()) + time.localtime().tm_gmtoff


def get_local_time_s(*, offset=0) -> str:
    """Returns **local** time **[+offset]** in 24hr format: **hh:mm:ss**"""
    return format_time((get_local_time_i() + offset) % 86400)


def calculate_eta(container: Sized, request_delay: float) -> int:
    return int(2.0 + (request_delay + 0.2 + 0.02) * len(container))


def time_now_fmt(fmt: str) -> str:
    """datetime.now().strftime() wrapper"""
    return datetime.datetime.now().strftime(fmt)


def datetime_str_nfull() -> str:
    """
    date in format yyyy-mm-dd_hh_mm_ss
    usable in file names
    """
    return time_now_fmt('%Y-%m-%d_%H_%M_%S')

#
#
#########################################
