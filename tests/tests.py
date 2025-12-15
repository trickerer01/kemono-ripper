# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import functools
from collections.abc import Callable
from unittest import TestCase

from kemono_ripper.api import RequestQueue
from kemono_ripper.config import Config
from kemono_ripper.logger import Log

RUN_CONN_TESTS = 0


def test_prepare(log=False) -> Callable[[], Callable[[], None]]:
    def invoke1(test_func: Callable[[...], None]) -> Callable[[], None]:
        @functools.wraps(test_func)
        def invoke_test(*args, **kwargs) -> None:
            def set_up_test() -> None:
                Log._disabled = not log
                Config._reset()
                RequestQueue._reset()
            set_up_test()
            test_func(*args, **kwargs)
        return invoke_test
    return invoke1


class CmdTests(TestCase):
    @test_prepare()
    def test_config_integrity(self):
        assert all(hasattr(Config, _) for _ in Config.NAMESPACE_VARS_REMAP.values())
        print(f'{self._testMethodName} passed')

#
#
#########################################
