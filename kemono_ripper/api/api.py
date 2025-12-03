# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import pathlib
import random
from asyncio import sleep

from aiohttp import ClientConnectorError, ClientResponse, ClientResponseError, ClientSession, ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector

from kemono_ripper.util import UAManager

from .actions import APIAction, GetCreatorPostAction, GetCreatorPostsAction, GetCreatorsAction, GetFreePostAction
from .defs import CONNECT_RETRY_DELAY, POSTS_PER_PAGE, DownloadMode, Mem
from .exceptions import RequestError, ValidationError
from .filters import Filter
from .logging import Log, set_logger
from .options import KemonoOptions
from .request_queue import RequestQueue
from .types import APIResponse, APIService, Creator, FreePost, ListedPost, ScannedPost

__all__ = ('Kemono',)


class Kemono:
    def __init__(self, options: KemonoOptions) -> None:
        # globals
        set_logger(options['logger'])
        # locals
        self._session: ClientSession | None = None
        # options
        self._dest_base: pathlib.Path = options['dest_base']
        self._retries: int = options['retries']
        self._max_jobs = options['max_jobs']
        self._api_address = options['api_address']
        self._service = options['service']
        self._timeout: ClientTimeout = options['timeout']
        self._nodelay: bool = options['nodelay']
        self._proxy: str = options['proxy']
        self._extra_headers: list[tuple[str, str]] = options['extra_headers']
        self._extra_cookies: list[tuple[str, str]] = options['extra_cookies']
        self._filters: tuple[Filter, ...] = options['filters']
        self._download_mode: DownloadMode = options['download_mode']
        # ensure correct args
        assert Log
        assert next(reversed(self._dest_base.parents)).is_dir()
        assert isinstance(self._download_mode, DownloadMode)
        assert self._api_address
        assert self._service
        assert self._max_jobs > 0

    async def __aenter__(self) -> Kemono:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def api_address(self) -> str:
        return self._api_address

    def _make_session(self) -> ClientSession:
        if self._session is not None:
            raise ValidationError('make_session should only be called once!')
        use_proxy = bool(self._proxy)
        if use_proxy:
            connector = ProxyConnector.from_url(self._proxy, limit=self._max_jobs)
        else:
            connector = TCPConnector(limit=self._max_jobs)
        session = ClientSession(connector=connector, read_bufsize=Mem.MB, timeout=self._timeout)
        new_useragent = UAManager.select_useragent(self._proxy if use_proxy else None)
        Log.trace(f'[{"P" if use_proxy else "NP"}] Selected user-agent \'{new_useragent}\'...')
        session.headers.update({'User-Agent': new_useragent, 'Content-Type': 'application/json', 'Accept': 'text/css'})
        if self._extra_headers:
            for hk, hv in self._extra_headers:
                session.headers.update({hk: hv})
        if self._extra_cookies:
            for ck, cv in self._extra_cookies:
                session.cookie_jar.update_cookies({ck: cv})
        return session

    async def _wrap_request(self, action: APIAction) -> APIResponse:
        assert self._session is not None
        if self._nodelay is False:
            await RequestQueue.until_ready(str(action.get_url()))
        response = await self._session.request(**action.as_api_request_data())
        response_content = await response.content.read()
        return await action.process_response_content(response_content)

    async def _query_api(self, action: APIAction) -> APIResponse:
        if self._session is None:
            self._session = self._make_session()

        retries = 0
        response: ClientResponse | None = None
        while retries <= self._retries:
            response = None
            try:
                Log.trace(f'Sending API request: {action!s}')
                result = await self._wrap_request(action)
                return result
            except Exception as e:
                if response is not None and '404.' in str(response.url):
                    Log.error('ERROR: 404')
                    assert False
                else:
                    Log.error(f'[{retries + 1:d}] fetch_html exception status '
                              f'{f"{response.status:d}" if response is not None else "???"}: '
                              f'\'{e.message if isinstance(e, ClientResponseError) else str(e)}\'')
                if isinstance(e, RequestError):
                    raise
                if not isinstance(e, ClientConnectorError):
                    retries += 1
                if retries <= self._retries:
                    await sleep(random.uniform(*CONNECT_RETRY_DELAY))
                continue

        if retries > self._retries:
            Log.error('Unable to connect. Aborting')
        elif response is None:
            Log.error('ERROR: Failed to receive any data')
        raise ConnectionError

    async def _download(self) -> pathlib.Path:
        return self._dest_base

    async def list_creators(self) -> list[Creator]:
        creators: list[Creator] = await self._query_api(GetCreatorsAction(self._api_address))
        return creators

    async def list_posts(self, creator_id: int) -> list[ListedPost]:
        all_posts: list[ListedPost] = []
        offset = 0
        while len(all_posts) % POSTS_PER_PAGE == 0:
            posts: list[ListedPost] = await self._query_api(GetCreatorPostsAction(self._api_address, self._service, creator_id, offset))
            all_posts.extend(posts)
            offset += POSTS_PER_PAGE
        return all_posts

    async def scan_post(self, post_id: int, creator_id: int, service: APIService | None = None) -> ScannedPost:
        service = service or self._service
        if not creator_id:
            post: FreePost = await self._query_api(GetFreePostAction(self._api_address, service, post_id))
            creator_id = int(post['artist_id'])
        post: ScannedPost = await self._query_api(GetCreatorPostAction(self._api_address, service, creator_id, post_id))
        return post

#
#
#########################################
