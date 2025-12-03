# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import asyncio
import random
from collections import deque

from .defs import CONNECT_REQUEST_DELAY


class RequestQueue:
    """
    Request delayed queue wrapper
    """
    _queue = deque[str]()
    _ready = True
    _lock = asyncio.Lock()

    @staticmethod
    def _reset() -> None:
        RequestQueue._ready = True
        RequestQueue._queue.clear()

    @staticmethod
    async def _set_ready() -> None:
        await asyncio.sleep(random.uniform(CONNECT_REQUEST_DELAY, CONNECT_REQUEST_DELAY + 0.75))
        RequestQueue._ready = True

    @staticmethod
    async def until_ready(url: str) -> None:
        """Pauses request until base delay passes (since last request)"""
        async with RequestQueue._lock:
            RequestQueue._queue.append(url)
        while RequestQueue._ready is False or RequestQueue._queue[0] != url:
            await asyncio.sleep(0.2)
        async with RequestQueue._lock:
            RequestQueue._queue.popleft()
            RequestQueue._ready = False
            asyncio.get_running_loop().create_task(RequestQueue._set_ready())

#
#
#########################################
