# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import AbstractEventLoop, create_task, gather, get_running_loop
from collections.abc import Callable

from aiohttp import ClientSession

from .logging import Log

__all__ = ('ClientSessionMgr',)

default_exc_handler: Callable[[AbstractEventLoop, dict], None] | None = None


class ClientSessionPair:
    def __init__(self, psession: ClientSession | None = None, npsession: ClientSession | None = None) -> None:
        assert (psession is None) is (npsession is None)
        self.psession = psession
        self.npsession = npsession

    async def close(self) -> None:
        if bool(self):
            tasks = [create_task(_.close()) for _ in (self.psession, self.npsession)]
            await gather(*tasks)

    def __bool__(self) -> bool:
        return all(bool(_) for _ in (self.psession, self.npsession))


class ClientSessionMgr:
    def __init__(self) -> None:
        global default_exc_handler
        self._sessions = ClientSessionPair()
        default_exc_handler = get_running_loop().get_exception_handler()
        get_running_loop().set_exception_handler(ClientSessionMgr.ignore_unclosed_session_exc_handler)

    async def close(self) -> None:
        return await self._sessions.close()

    def ensure_sessions(self, make_session: Callable[[bool], ClientSession]) -> None:
        if not bool(self._sessions):
            self._sessions = ClientSessionPair(make_session(True), make_session(False))

    def get(self, use_proxy: bool) -> ClientSession:
        assert bool(self._sessions)
        if use_proxy:
            return self._sessions.psession
        else:
            return self._sessions.npsession

    @staticmethod
    def ignore_unclosed_session_exc_handler(selfloop: AbstractEventLoop, context: dict) -> None:
        message = context.get('message')
        if message not in ('Event loop is closed',):
            default_exc_handler(selfloop, context)
        else:
            Log.trace(f'{message} exception ignored...')

#
#
#########################################
