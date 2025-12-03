# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import random
import urllib.parse

from fake_useragent import FakeUserAgent

__all__ = ('UAManager',)

USER_AGENT_DEFAULT = 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Goanna/6.7 Firefox/102.0 PaleMoon/33.3.1'
UA_GENERATOR = FakeUserAgent(browsers=('Firefox',), platforms=('desktop',), fallback=USER_AGENT_DEFAULT)
# noinspection PyProtectedMember
USER_AGENTS = list(set(_['useragent'] for _ in UA_GENERATOR._filter_useragents()))
SEED_BASE = int(random.randint(0, len(USER_AGENTS)))


class UAManager:
    def __init__(self) -> None:
        raise RuntimeError(f'{self.__class__.__name__} class should never be instanced!')

    @staticmethod
    def _addr_to_int(addr: str, seed: int) -> int:
        return int(urllib.parse.urlparse(addr).netloc.replace('.', '').replace(':', '')) + seed + SEED_BASE

    @staticmethod
    def _generate(addr: str, seed: int) -> str:
        idx = UAManager._addr_to_int(addr, seed) % len(USER_AGENTS)
        ua = USER_AGENTS[idx]
        return ua

    @staticmethod
    def select_useragent(addr: str | None) -> str:
        prox_addr = addr or 'http://127.0.0.1:0'
        prox_seed = 0
        ua = UAManager._generate(prox_addr, prox_seed)
        return ua

#
#
#########################################
