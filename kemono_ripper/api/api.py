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
import sys
from asyncio import sleep
from collections.abc import Iterable

from aiofile import async_open
from aiohttp import ClientConnectorError, ClientPayloadError, ClientResponse, ClientSession, ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector
from yarl import URL

from kemono_ripper.util import UAManager

from .actions import APIDownloadAction, APIFetchAction, GetCreatorPostAction, GetCreatorPostsAction, GetCreatorsAction, GetFreePostAction
from .defs import CONNECT_RETRY_DELAY, MAX_JOBS, POSTS_PER_PAGE, DownloadMode, Mem
from .exceptions import KemonoErrorCodes, RequestError, ValidationError
from .filters import Filter
from .logging import Log, set_logger
from .options import KemonoOptions
from .request_queue import RequestQueue
from .types import APIAddress, APIResponse, APIService, Creator, FreePost, ListedPost, PostPageScanResult, ScannedPost

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
        assert Log, 'Logger is not initialized!'
        assert next(reversed(self._dest_base.parents)).is_dir(), f'Inavlid base destination folder \'{self._dest_base!s}\'!'
        assert isinstance(self._download_mode, DownloadMode), f'Invalid download mode \'{self._download_mode!s}\'!'
        assert self._api_address in APIAddress.__args__, f'Invalid API address \'{self._api_address!s}\'!'
        assert self._service in APIService.__args__, f'Invalid service \'{self._service!s}\'!'
        assert self._retries >= 0, f'Invalid retries value \'{self._retries!s}\'!'
        assert 0 < self._max_jobs <= MAX_JOBS, f'Invalid max jobs value \'{self._max_jobs!s}\', must be 1..{MAX_JOBS:d}!'

    async def __aenter__(self) -> Kemono:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @property
    def api_address(self) -> APIAddress:
        return self._api_address

    @property
    def api_service(self) -> APIService:
        return self._service

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

    async def _wrap_fetch_request(self, action: APIFetchAction) -> APIResponse:
        assert self._session is not None
        if self._nodelay is False:
            await RequestQueue.until_ready(str(action.get_url()))
        response = await self._session.request(**action.as_api_request_data())
        response_content = await response.content.read()
        return await action.process_response_content(response_content)

    async def _query_api(self, action: APIFetchAction) -> APIResponse:
        if self._session is None:
            self._session = self._make_session()

        retries = 0
        while retries <= self._retries:
            try:
                Log.trace(f'Sending API request: {action!s}')
                result = await self._wrap_fetch_request(action)
                return result
            except Exception as e:
                if isinstance(e, RequestError):
                    raise
                if not isinstance(e, ClientConnectorError):
                    retries += 1
                if retries <= self._retries:
                    await sleep(random.uniform(*CONNECT_RETRY_DELAY))
                continue

        if retries > self._retries:
            Log.error('Unable to connect. Aborting')
        raise ConnectionError

    async def _wrap_download_request(self, action: APIDownloadAction, **kwargs) -> ClientResponse:
        assert self._session is not None
        if self._nodelay is False:
            await RequestQueue.until_ready(str(action.get_url()))
        response = await self._session.request(**action.as_api_request_data(), **kwargs)
        return response

    async def _download(self, action: APIDownloadAction, file_path: pathlib.Path) -> tuple[int, KemonoErrorCodes]:
        if self._session is None:
            self._session = self._make_session()

        retries = 0
        bytes_written = 0
        while retries <= self._retries:
            r: ClientResponse | None = None
            try:
                file_size = file_path.stat().st_size if file_path.is_file() else 0
                hkwargs: dict[str, dict[str, str]] = {'headers': {'Range': f'bytes={file_size:d}-'} if file_size > 0 else {}}
                async with await self._wrap_download_request(action, **hkwargs) as r:
                    if r.status == 404:
                        Log.error(f'Got 404 for {action.get_url().human_repr()}...!')
                        # retries = self._retries
                        raise RequestError(KemonoErrorCodes.KEMONO_ERROR_CODE_GENERIC)
                    content_len: int = r.content_length or 0
                    assert content_len > 0, f'Content length is {r.content_length!s} for {action.get_url().human_repr()}! Retrying...'
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    async with async_open(file_path, mode='wb') as output_file:
                        async for chunk in r.content.iter_chunked(128 * Mem.KB):
                            await output_file.write(chunk)
                            bytes_written += len(chunk)
                return bytes_written, KemonoErrorCodes.ESUCCESS
            except Exception as e:
                Log.error(f'{file_path.name}: {sys.exc_info()[0]}: {sys.exc_info()[1]}')
                if (r is None or r.status != 403) and not isinstance(e, (ClientPayloadError, ClientConnectorError)):
                    retries += 1
                    local_path = '/'.join(file_path.parts[-3:])
                    Log.error(f'{local_path}: error #{retries:d}...')
                if r is not None and not r.closed:
                    r.close()
                if retries <= self._retries:
                    await sleep(random.uniform(*CONNECT_RETRY_DELAY))
                continue

        if retries > self._retries:
            Log.error('Unable to connect. Aborting')
        raise ConnectionError

    async def _scan_post(self, link: PostPageScanResult) -> ScannedPost:
        assert link.service
        assert link.post_id
        creator_id = link.creator_id
        if not creator_id:
            post: FreePost = await self._query_api(GetFreePostAction(self._api_address, link.service, link.post_id))
            creator_id = int(post['artist_id'])
        post: ScannedPost = await self._query_api(GetCreatorPostAction(self._api_address, link.service, creator_id, link.post_id))
        return post

    async def scan_posts(self, links: Iterable[PostPageScanResult]) -> list[ScannedPost]:
        scanned_posts: list[ScannedPost] = []
        for link in links:
            scanned_post = await self._scan_post(link)
            scanned_posts.append(scanned_post)
        return scanned_posts

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

    async def download_url(self, url: URL, file_path: pathlib.Path) -> tuple[int, KemonoErrorCodes]:
        result = await self._download(APIDownloadAction(url), file_path)
        return result

#
#
#########################################
