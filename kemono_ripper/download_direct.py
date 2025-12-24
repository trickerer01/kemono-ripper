# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import os
import pathlib
import random
import sys
from asyncio import create_task, gather, sleep

from aiofile import async_open
from aiohttp import ClientConnectorError, ClientPayloadError, ClientResponse, ClientSession, ClientTimeout, TCPConnector
from aiohttp_socks import ProxyConnector
from yarl import URL

from .api import DownloadMode, Mem, RequestQueue
from .config import ExternalURLHandlerConfig
from .defs import SupportedExternalWebsites
from .logger import Log
from .util import UAManager

__all__ = ('DirectLinkDownloader',)

CLIENT_CONNECTOR_ERRORS = (ClientPayloadError, ClientConnectorError)


class DirectLinkDownloader:
    def __init__(self, links: list[str], options: ExternalURLHandlerConfig) -> None:
        # args
        self._links = links
        # locals
        self._session: ClientSession | None = None
        self._user_agent: str = ''
        # options
        self._dest_base: pathlib.Path = options.dest_base
        self._retries: int = options.retries
        self._max_jobs = options.max_jobs
        self._timeout: ClientTimeout = options.timeout
        self._nodelay: bool = options.nodelay
        self._proxy: str = options.proxy
        self._extra_headers: list[tuple[str, str]] = options.extra_headers
        self._extra_cookies: list[tuple[str, str]] = options.extra_cookies
        self._download_mode: str = options.download_mode

    async def __aenter__(self) -> DirectLinkDownloader:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _make_session(self) -> ClientSession:
        use_proxy = bool(self._proxy)
        if use_proxy:
            connector = ProxyConnector.from_url(self._proxy, limit=self._max_jobs)
        else:
            connector = TCPConnector(limit=self._max_jobs)
        session = ClientSession(connector=connector, read_bufsize=Mem.MB, timeout=self._timeout)
        self._user_agent = UAManager.select_useragent(self._proxy if use_proxy else None)
        session.headers.update({'User-Agent': self._user_agent})
        if self._extra_headers:
            for hk, hv in self._extra_headers:
                session.headers.update({hk: hv})
        if self._extra_cookies:
            for ck, cv in self._extra_cookies:
                session.cookie_jar.update_cookies({ck: cv})
        return session

    async def _wrap_request(self, url: URL, try_num: int, **kwargs) -> ClientResponse:
        assert self._session is not None
        if self._nodelay is False:
            await RequestQueue.until_ready(str(url))
        Log.trace(f'[{try_num + 1:d}] Sending request: GET => {url!s}')
        response = await self._session.request('GET', url, **kwargs)
        return response

    async def _download(self, url: URL, output_path: pathlib.Path) -> pathlib.Path:
        if self._download_mode != DownloadMode.FULL:
            if self._download_mode == DownloadMode.TOUCH:
                output_path.touch(exist_ok=True)
            return output_path

        if self._session is None:
            self._session = self._make_session()

        local_path = '/'.join(('...', *output_path.parts[-3:]))
        if not output_path.suffix and output_path.parent.is_dir():
            with os.scandir(output_path.parent.as_posix()) as dir_iter:
                for dir_entry in dir_iter:
                    if dir_entry.is_file():
                        dpath = pathlib.Path(dir_entry.path)
                        if dpath.with_suffix('').name == output_path.name:
                            output_path = dpath
                            local_path_old = local_path
                            local_path = '/'.join(('...', *output_path.parts[-3:]))
                            Log.warn(f'[DirectDownload] File at {url!s} has no extension. Storing to a similarly named file found:'
                                     f' \'{local_path_old}\' -> \'{local_path}\'')
                            break

        try_num = 0
        bytes_written = 0
        while try_num <= self._retries:
            r: ClientResponse | None = None
            try:
                file_size = output_path.stat().st_size if output_path.is_file() else 0
                hkwargs: dict[str, dict[str, str]] = {'headers': {'Range': f'bytes={file_size:d}-'} if file_size > 0 else {}}
                async with await self._wrap_request(url, try_num=try_num, **hkwargs) as r:
                    if not output_path.suffix:
                        content_type = r.content_type
                        if content_type.startswith(('video/', 'image/')):
                            suffix = f'.{content_type[content_type.find("/") + 1:]}'
                            output_path = output_path.with_suffix(suffix)
                            local_path = f'{local_path}{suffix}'
                    content_len: int = r.content_length or 0
                    content_range_s = str(r.headers.get('Content-Range', '/')).split('/', 1)
                    content_range = int(content_range_s[1]) if len(content_range_s) > 1 and content_range_s[1].isnumeric() else 1
                    if (content_len in (0, file_size) or r.status == 416) and file_size >= content_range:
                        Log.warn(f'{local_path} is already completed, size: {file_size:d} ({file_size / Mem.MB:.2f} Mb)')
                        return output_path
                    if r.status == 404:
                        Log.error(f'Got 404 for {url!s}...!')
                        raise FileNotFoundError
                    r.raise_for_status()
                    assert content_len > 0, f'Content length is {r.content_length!s} for {url!s}! Retrying...'
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    start_str = f' <continuing at {file_size:d}>' if file_size else ''
                    total_str = f' / {(file_size + content_len) / Mem.MB:.2f}' if file_size else ''
                    Log.info(f'[DirectDownload] Saving{start_str} {url.name}'
                             f' {content_len / Mem.MB:.2f}{total_str} Mb to {local_path}')
                    async with async_open(output_path, 'ab') as output_file:
                        if content_len > 16 * Mem.KB:
                            try_num = 0  # reset try count if we can still download
                        async for chunk in r.content.iter_chunked(128 * Mem.KB):
                            await output_file.write(chunk)
                            bytes_written += len(chunk)
                return output_path
            except Exception as e:
                Log.error(f'{local_path}: {sys.exc_info()[0]}: {sys.exc_info()[1]}')
                if (r is None or r.status != 403) and not isinstance(e, CLIENT_CONNECTOR_ERRORS):
                    try_num += 1
                    Log.error(f'{local_path}: error #{try_num:d}...')
                if r is not None and not r.closed:
                    r.close()
                if try_num <= self._retries:
                    await sleep(random.uniform(4., 8.))
                continue

        Log.error(f'Unable to connect. Aborting {local_path}')
        return pathlib.Path()

    @staticmethod
    def is_link_supported(url: URL) -> bool:
        if url.is_absolute():
            if url.host == SupportedExternalWebsites.Catbox:
                return bool(url.suffix)
            if url.host == SupportedExternalWebsites.WebmShare:
                return bool(url.path)
            if url.host == SupportedExternalWebsites.Dropbox and url.suffix:
                return DirectLinkDownloader.validate_link(url, SupportedExternalWebsites.Dropbox)
        return False

    @staticmethod
    def validate_link(url: URL, link_type: SupportedExternalWebsites) -> bool:
        if link_type == SupportedExternalWebsites.Dropbox and url.suffix:
            if 'scl' in url.parts:
                return 'rlkey' in url.query
            return True
        return False

    @staticmethod
    def normalize_link(url: URL) -> URL:
        if url.host == SupportedExternalWebsites.WebmShare:
            if 'download-webm' not in url.path:
                return url.with_path('') / 'download-webm' / url.parts[-1]
        if url.host == SupportedExternalWebsites.Dropbox:
            if (url.query.get('dl') or '0') == '0':
                return url.extend_query(dl=1)
        return url

    async def run(self) -> list[pathlib.Path]:
        tasks = []
        for link in self._links:
            url = URL(link)
            tasks .append(create_task(self._download(url, self._dest_base / url.name)))

        results: tuple[pathlib.Path | BaseException, ...] = await gather(*tasks)
        Log.info(f'Downloaded {len([c for c in results if isinstance(c, pathlib.Path)])} / {len(tasks)} files')
        return list(results)

#
#
#########################################
