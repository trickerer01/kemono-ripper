# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import json
import pathlib
import random
import re
from asyncio import Lock as AsyncLock
from asyncio import Semaphore
from asyncio.queues import Queue as AsyncQueue
from asyncio.tasks import as_completed, gather, sleep
from collections import defaultdict, deque
from collections.abc import Iterable, Sequence
from typing import Final, Protocol

from bs4 import BeautifulSoup
from yarl import URL

from .api import (
    APIAddress,
    DownloadMode,
    DownloadResult,
    DownloadStatus,
    Kemono,
    KemonoErrorCodes,
    Mem,
    PostDownloadInfo,
    PostLinkDownloadInfo,
    ScannedPost,
    ScannedPostPost,
    State,
)
from .config import Config, ExternalURLHandlerConfig, MegaConfig
from .defs import FILE_NAME_FULL_MAX_LEN, POST_TAGS_PER_POST_INFO_DEFAULT, SITE_MEGA, UTF8, PathURLJSONEncoder
from .filters import (
    LSPostFilter,
    PostDateImportedFilter,
    PostDatePublishedFilter,
    PostIdFilter,
    PostLinkExtFilter,
    PostLinkFilter,
    any_filter_matching_ls_post,
    any_filter_matching_post_link,
)
from .formatter import get_path_formatter
from .logger import Log
from .util import sanitize_path

try:
    import mega_download as handler_mega
except ImportError:
    handler_mega = None

__all__ = ('KemonoDownloader',)

SUPPORTED_TAGS = (
    ('a', 'href'),
    ('img', 'src'),
)


# external downloaders
class ExternalURLHandler(Protocol):
    _semaphore: Semaphore

    @staticmethod
    async def run(url: str, config: ExternalURLHandlerConfig) -> list[pathlib.Path]: ...

    @staticmethod
    def name() -> str: ...

    @staticmethod
    def app_name() -> str: ...


class MegaURLHandler:
    _semaphore: Semaphore = Semaphore(1)

    @staticmethod
    async def run(url: str, config: ExternalURLHandlerConfig) -> list[pathlib.Path]:
        async with MegaURLHandler._semaphore:
            return await handler_mega.MegaDownloader([url], config).run()

    @staticmethod
    def name() -> str:
        return 'Mega'

    @staticmethod
    def app_name() -> str:
        return handler_mega.APP_NAME


class ExternalURLDownloader:
    def __init__(self, url: URL) -> None:
        self._url = url

    @property
    def _handler(self) -> ExternalURLHandler:
        return EXTERNAL_URL_HANDLERS[self._url.host]

    def valid(self) -> bool:
        return self._url.host in EXTERNAL_URL_HANDLERS

    def name(self) -> str:
        return self._handler.name() if self.valid() else 'None'

    def app_name(self) -> str:
        return self._handler.app_name() if self.valid() else 'Unknown'

    async def download(self, *, plink_id: str, url: str, config: ExternalURLHandlerConfig) -> list[pathlib.Path]:
        try:
            assert self.valid()
            mresults = await self._handler.run(url, config) if self.valid() else []
            Log.info(f'{plink_id} \'{self.app_name()}\' has successfully handled {self._url.human_repr()} ({len(mresults)} files)')
            return mresults
        except Exception:
            import traceback
            Log.error(f'{traceback.format_exc()}\n{plink_id} \'{self.app_name()}\' FAILED to handle {self._url.human_repr()}!')
            return []


def register_external_downloader(host: str, handler: ExternalURLHandler) -> None:
    EXTERNAL_URL_HANDLERS[host] = handler


EXTERNAL_URL_HANDLERS: dict[str, ExternalURLHandler] = {}


# end external downloaders


class KemonoDownloader:
    def __init__(self, kemono: Kemono, posts: Sequence[ScannedPost]) -> None:
        self._kemono: Final[Kemono] = kemono
        self._post_info: Final[dict[str, PostDownloadInfo]] = {}

        self._post_filters: list[LSPostFilter | None] = [
            PostIdFilter(Config.filter_post_ids) if Config.filter_post_ids else None,
            PostDateImportedFilter(Config.filter_post_imported) if Config.filter_post_imported else None,
            PostDatePublishedFilter(Config.filter_post_published) if Config.filter_post_published else None,
        ]
        self._post_link_filters: list[PostLinkFilter | None] = [
            PostLinkExtFilter(Config.filter_extensions) if Config.filter_extensions else None,
        ]

        self._queue_produce: deque[PostDownloadInfo] = deque()
        self._queue_consume: AsyncQueue[PostDownloadInfo] = AsyncQueue(Config.max_jobs)
        self._post_link_download_semaphore: Semaphore = Semaphore(Config.max_jobs)

        self._downloaded_count: dict[str, int] = defaultdict(int)
        self._already_exist_count: dict[str, int] = defaultdict(int)
        self._skipped_count: dict[str, int] = defaultdict(int)
        self._404_count: dict[str, int] = defaultdict(int)
        self._external_count: dict[str, int] = defaultdict(int)
        self._unsupported_count: dict[str, int] = defaultdict(int)

        self._downloads_active: dict[PostDownloadInfo, list[PostLinkDownloadInfo]] = defaultdict(list[PostLinkDownloadInfo])
        self._writes_active: dict[PostDownloadInfo, list[PostLinkDownloadInfo]] = defaultdict(list[PostLinkDownloadInfo])
        self._failed_items: dict[PostDownloadInfo, list[PostLinkDownloadInfo]] = defaultdict(list[PostLinkDownloadInfo])

        self._sequence_lock: Final[AsyncLock] = AsyncLock()
        self._active_downloads_lock: Final[AsyncLock] = AsyncLock()
        self._active_writes_lock: Final[AsyncLock] = AsyncLock()

        self._orig_count: Final[int] = self._gather_post_download_info(posts)
        self._queue_produce.extend(post for _, post in self._post_info.items())

        if handler_mega:
            register_external_downloader(SITE_MEGA, MegaURLHandler())

    async def __aenter__(self) -> KemonoDownloader:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return

    async def _at_post_link_start(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> None:
        async with self._active_downloads_lock:
            self._downloads_active[post].append(plink)
        Log.trace(f'[queue] [{post.creator_id}:{post.post_id}] \'{plink.name}\' added to active')

    async def _at_post_link_finish(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> None:
        async with self._active_downloads_lock:
            if plink in self._downloads_active[post]:
                self._downloads_active[post].remove(plink)
                Log.trace(f'[queue] [{post.creator_id}:{post.post_id}] \'{plink.name}\' removed from active')
            post.completed.append(plink)
            result = plink.status.result
            if result == DownloadResult.FAIL_ALREADY_EXISTS:
                self._already_exist_count[post.post_id] += 1
            elif result in (DownloadResult.FAIL_SKIPPED, DownloadResult.FAIL_FILTERED_OUTER):
                self._skipped_count[post.post_id] += 1
            elif result == DownloadResult.FAIL_NOT_FOUND:
                self._404_count[post.post_id] += 1
            elif result == DownloadResult.FAIL_RETRIES:
                self._failed_items[post].append(plink)
            elif result == DownloadResult.SUCCESS:
                self._downloaded_count[post.post_id] += 1
            elif result == DownloadResult.HANDLED_EXTERNALLY:
                self._external_count[post.post_id] += 1
            elif result == DownloadResult.FAIL_UNSUPPORTED:
                self._unsupported_count[post.post_id] += 1

    async def _at_post_start(self, post: PostDownloadInfo) -> None:
        async with self._active_downloads_lock:
            self._downloads_active[post] = []
        Log.info(f'Processing post [{post.creator_id}:{post.post_id}] \'{post.original_post["post"]["title"]}\'...')

    async def _at_post_finish(self, post: PostDownloadInfo) -> None:
        pid = f'[{post.creator_id}:{post.post_id}] \'{post.original_post["post"]["title"]}\''
        async with self._active_downloads_lock:
            assert post in self._downloads_active
            results = [plink.status.result for _, plink in post.links.items()]
            assert not any(_ == DownloadResult.UNKNOWN for _ in results)
            success = len([_ for _ in results if _ == DownloadResult.SUCCESS])
            fail_404 = len([_ for _ in results if _ == DownloadResult.FAIL_NOT_FOUND])
            fail_tries = len([_ for _ in results if _ == DownloadResult.FAIL_RETRIES])
            exists = len([_ for _ in results if _ == DownloadResult.FAIL_ALREADY_EXISTS])
            skipped = len([_ for _ in results if _ == DownloadResult.FAIL_SKIPPED])
            filtered = len([_ for _ in results if _ == DownloadResult.FAIL_FILTERED_OUTER])
            unsupported = len([_ for _ in results if _ == DownloadResult.FAIL_UNSUPPORTED])
            external = len([_ for _ in results if _ == DownloadResult.HANDLED_EXTERNALLY])
            if len(results) > unsupported:
                Log.info(f'[queue] post {pid}: Done: {len(post.links):d} links: {success:d} downloaded, {fail_tries:d} failed,'
                         f' {skipped:d} skipped, {filtered:d} filtered out, {exists:d} already exists, {fail_404:d} not found,'
                         f' {unsupported:d} unsupported, {external:d} handled externally')
            else:
                links_str = '\n'.join(plink.url.human_repr() for _, plink in post.links.items())
                Log.info(f'[queue] post {pid}: None of {len(post.links):d} links are supported:\n{links_str}')

            self._downloads_active.pop(post)
            Log.trace(f'[queue] post {post.post_id} \'{post.original_post["post"]["title"]}\' removed from active')

    async def _download_post(self, post: PostDownloadInfo) -> None:
        async def download_post_link_wrapper(plink) -> None:
            async with self._post_link_download_semaphore:
                return await self._download_post_link(post, plink)

        post.status.state = State.DOWNLOADING

        Log.trace(f'[{post.creator_id}:{post.post_id}] Saving info to {post.local_path}/{POST_TAGS_PER_POST_INFO_DEFAULT}')
        post.dest.mkdir(parents=True, exist_ok=True)
        with open(post.dest / POST_TAGS_PER_POST_INFO_DEFAULT, 'wt', encoding=UTF8, newline='\n', errors='replace') as outfile_tags:
            json.dump(post, outfile_tags, ensure_ascii=False, indent=Config.indent, cls=PathURLJSONEncoder)
            outfile_tags.write('\n')

        tasks = [download_post_link_wrapper(plink) for _, plink in post.links.items()]
        _ = await gather(*tasks)

    async def _download_post_link(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> None:
        await self._at_post_link_start(post, plink)
        plink_id = f'[{post.creator_id}:{post.post_id}] \'{plink.name}\''
        plink.status.state = State.SCANNING
        url_str = plink.url.human_repr()
        handler_ex = ExternalURLDownloader(plink.url)
        if handler_ex.valid():
            Log.info(f'{plink_id}: {handler_ex.name()} url detected, using \'{handler_ex.app_name()}\' to handle {url_str}')
            mresults = await handler_ex.download(plink_id=plink_id, url=url_str, config=MegaConfig(Config, dest_base=plink.path))
            succ_count = len([_.is_file() for _ in mresults])
            Log.info(f'{plink_id}: {handler_ex.app_name()} handled {url_str} with {succ_count:d} / {len(mresults):d} success')
            dresult = DownloadResult.HANDLED_EXTERNALLY
        elif not self.is_link_supported(plink.url):
            Log.warn(f'{plink_id}: Skipping unsupported link format {url_str}...')
            dresult = DownloadResult.FAIL_UNSUPPORTED
        else:
            Log.info(f'{plink_id} Processing {url_str} => {plink.local_path}')
            plink.status.state = State.DOWNLOADING
            await self.add_to_writes(post, plink, True)
            ec = await self._kemono.download_url(post, plink)
            await self.remove_from_writes(post, plink, True)
            if plink.path.is_file():
                file_size = plink.path.stat().st_size
                if file_size != plink.status.expected_size:
                    Log.error(f'Bytes written mismatch for {plink.local_path}'
                              f' (size {file_size:d} vs expected {plink.status.expected_size:d})')
                    Log.warn(f'{plink_id}: Failed: {ec!s}')
                else:
                    Log.info(f'{plink_id}: Completed, {plink.local_path}, size: {file_size / Mem.MB:.2f} MB')
            elif Config.download_mode != DownloadMode.SKIP:
                Log.warn(f'{plink_id}: Failed: {ec!s}')
            dresult = (
                DownloadResult.SUCCESS if ec == KemonoErrorCodes.ESUCCESS
                else DownloadResult.FAIL_ALREADY_EXISTS if ec == KemonoErrorCodes.EEXISTS
                else DownloadResult.FAIL_RETRIES
            )
        plink.status.result = dresult
        plink.status.state = State.FAILED if ((1 << plink.status.result) & DownloadResult.RESULT_MASK_CRITICAL) else State.DONE
        await self._at_post_link_finish(post, plink)

    async def _prod(self) -> None:
        while True:
            async with self._sequence_lock:
                if self.can_fetch_next() is False:
                    break
                qfull = self._queue_consume.full()
            if qfull is False:
                if post := await self._try_fetch_next():
                    post.status.state = State.QUEUED
                    await self._queue_consume.put(post)
            else:
                await sleep(0.2)

    async def _cons(self) -> None:
        while True:
            async with self._sequence_lock:
                can_fetch = self.can_fetch_next()
                qsize = self._queue_consume.qsize()
            if can_fetch is False and qsize == 0:
                break
            async with self._active_downloads_lock:
                dsize = len(self._downloads_active)
            if qsize > 0 and dsize < Config.max_jobs:
                post = await self._queue_consume.get()
                await self._at_post_start(post)
                await self._download_post(post)
                await self._at_post_finish(post)
                self._queue_consume.task_done()
            else:
                await sleep(0.35)

    async def _after_download(self) -> None:
        newline = '\n'
        downloaded_count = sum(self._downloaded_count.values())
        already_exist_count = sum(self._already_exist_count.values())
        skipped_count = sum(self._skipped_count.values())
        not_found_count = sum(self._404_count.values())
        external_count = sum(self._external_count.values())
        unsupported_count = sum(self._unsupported_count.values())
        Log.info(f'\nDone. {downloaded_count:d} / {self._orig_count:d} post links downloaded, '
                 f'{already_exist_count:d} already existed, {skipped_count:d} skipped, {not_found_count:d} not found, '
                 f'{unsupported_count:d} unsupported, {external_count:d} handled externally')
        if len(self._queue_produce) > 0:
            Log.fatal(f'total queue is still at {len(self._queue_produce):d} != 0!')
        if len(self._writes_active) > 0:
            Log.fatal(f'active writes count is still at {len(self._writes_active):d} != 0!')
        if len(self._failed_items) > 0:
            fitems = ['\n'.join([f'{post.original_post["post"]["service"]}:{post.creator_id}:{post.post_id}'
                                 f' {plink.url.human_repr()} => {plink.local_path}'
                                 for plink in plinks]) for post, plinks in self._failed_items.items()]
            Log.fatal(f'\nFailed items:\n{newline.join(fitems)}')

    async def run(self) -> None:
        for cv in as_completed([self._prod(), *(self._cons() for _ in range(Config.max_jobs))]):
            await cv
        await self._queue_consume.join()
        await self._after_download()

    async def is_writing(self, post: PostDownloadInfo) -> bool:
        async with self._active_writes_lock:
            return post in self._writes_active

    async def add_to_writes(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo, safe=False) -> None:
        async with self._active_writes_lock:
            if safe is False or post not in self._writes_active or plink not in self._writes_active[post]:
                self._writes_active[post].append(plink)

    async def remove_from_writes(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo, safe=False) -> None:
        async with self._active_writes_lock:
            if safe is False or post in self._writes_active:
                if plink in self._writes_active[post]:
                    self._writes_active[post].remove(plink)
                if not self._writes_active[post]:
                    self._writes_active.pop(post)

    def can_fetch_next(self) -> bool:
        return bool(self._queue_produce)

    def get_workload_size(self) -> int:
        return len(self._queue_produce) + self._queue_consume.qsize() + len(self._downloads_active)

    async def _try_fetch_next(self) -> PostDownloadInfo | None:
        async with self._sequence_lock:
            if self._queue_produce:
                return self._queue_produce.popleft()
        return None

    def _gather_post_download_info(self, scanned_posts: Iterable[ScannedPost]) -> int:
        def next_file_name(name_base: str) -> str:
            next_file_name.last_post_idx = getattr(next_file_name, 'last_post_idx', 0)
            if next_file_name.last_post_idx != spost_idx:
                next_file_name.last_post_idx = spost_idx
                next_file_name.name_idx = 0
            next_file_name.name_idx = getattr(next_file_name, 'name_idx', 0) + 1
            return f'{next_file_name.name_idx:02d}_{name_base}'

        def next_api_address() -> URL:
            next_api_address.name_idx = (getattr(next_api_address, 'name_idx', random.randint(1, 99)) + random.randint(1, 99)) % 3 + 1
            return URL(f'https://n{next_api_address.name_idx:d}.{self._kemono.api_address}')

        post_strings: list[str] = []
        for spost_idx, spost in enumerate(scanned_posts):  # noqa B007  # stupid ruff
            post: ScannedPostPost = spost['post']
            pid = post['id']
            user = post['user']
            title = post['title']

            if spfilter := any_filter_matching_ls_post(spost, self._post_filters):
                Log.warn(f'[{user}:{pid}] {title}: post was filtered out by {spfilter!s}. Skipped!')
                continue

            links_dict: dict[URL, str] = {}

            if previews := spost['previews']:
                for preview in previews:
                    if preview['type'] == 'thumbnail':
                        purl = URL(preview['path'])
                        links_dict.update({purl: preview['name']})
                    elif preview['type'] == 'embed':
                        purl = URL(preview['url'])
                        links_dict.update({purl: preview['subject'] or 'Untitled'})
                    else:
                        Log.warn(f'[{user}:{pid}] {title}: unsupported preview type \'{preview["type"]}\'!')

            if attachments := post['attachments']:
                for attachment in attachments:
                    aurl = URL(attachment['path'])
                    links_dict.update({aurl: attachment['name']})

            content = post['content']
            if content and len(content) >= 40:
                link_idx = len(links_dict)
                bs = BeautifulSoup(content, 'html.parser')
                for tag_type, tag_name in SUPPORTED_TAGS:
                    bs_tags = bs.find_all(tag_type)
                    check_mega_keys = tag_type == 'a'
                    keys_mega: list[str] = [
                        re.search(r'([#!]?\w{28,})', _.string).group(1) for _ in bs.find_all(text=re.compile(r'\W{2,}[#!]?\w{28,}'))
                    ] if check_mega_keys else []
                    key_idx = 0
                    for bs_tag in bs_tags:
                        url = URL(bs_tag[tag_name])
                        url_purged = url.with_query('')
                        if url_purged not in links_dict:
                            if not url.is_absolute():
                                link_name = f'unnamed_{link_idx:02d}' if url == url_purged else self.extract_link_name(url)
                            elif self.is_link_supported(url_purged):
                                link_name = self.extract_link_name(url)
                            else:
                                link_idx += 1
                                link_name = f'unnamed_{link_idx:02d}'
                                if key_idx < len(keys_mega) and url.host == SITE_MEGA and '#' not in url_purged.path:
                                    key = keys_mega[key_idx]
                                    url_purged = url_purged.with_fragment(key[1 if '#' in key else 0:])
                                    key_idx += 1
                            links_dict.update({url_purged: link_name})

            if file := post['file']:
                furl = URL(file['path'])
                links_dict.update({furl: file['name']})

            if videos := spost.get('videos'):
                for video in videos:
                    vurl = URL(video['path'])
                    links_dict.update({vurl: video['name']})

            post_tags = spost['post']['tags']
            post_dest_base = get_path_formatter(Config.path_format).format(post)
            post_dest = Config.dest_base.joinpath(post_dest_base)

            links: dict[str, PostLinkDownloadInfo] = {}
            for link_base, name in links_dict.items():
                if link_base.host in APIAddress.__args__ or not link_base.is_absolute():
                    link_full = next_api_address().with_path(f'data{link_base.path}')
                else:
                    link_full = link_base
                if not pathlib.Path(name).suffix:
                    name = f'{name}{link_base.suffix}'

                name_append = name
                lpath = post_dest.joinpath(sanitize_path(next_file_name(name_append)))
                while (lplen := len(lpath.as_posix())) > FILE_NAME_FULL_MAX_LEN and len(name_append) > 15:
                    Log.warn(f'[{user}:{pid}]: file path \'{lpath.as_posix()}\' length is {lplen:d} > {FILE_NAME_FULL_MAX_LEN:d}...')
                    name_append = f'{name_append[:len(name_append) // 2]}{link_base.suffix}'
                    lpath = post_dest.joinpath(sanitize_path(next_file_name(name_append)))
                if (lplen := len(lpath.as_posix())) > FILE_NAME_FULL_MAX_LEN:
                    raise OSError(f'[{user}:{pid}]: file path \'{lpath.as_posix()}\' length is {lplen:d} > {FILE_NAME_FULL_MAX_LEN:d}!')

                plink = PostLinkDownloadInfo(name, link_full, lpath, DownloadStatus())

                if plfilter := any_filter_matching_post_link(plink, self._post_link_filters):
                    Log.warn(f'[{user}:{pid}] {title}: file \'{name}\' was filtered out by {plfilter!s}. Skipped!')
                    continue

                links[name] = plink

            self._post_info[pid] = PostDownloadInfo(pid, user, user, post_tags, post_dest, spost, links, [], DownloadStatus())

            links_str = '\n'.join(f' {pldi.url.human_repr()} => {pldi.local_path}' for title, pldi in links.items())
            post_strings.append(f'Post [{user}:{pid}] \'{title}\': {len(links):d} links:\n{links_str}')

        Log.info('\n'.join(post_strings))
        return sum(len(_.links) for _ in self._post_info.values())

    @staticmethod
    def extract_link_name(url: URL) -> str:
        return url.query.getone('f', url.name)

    @staticmethod
    def is_link_supported(url: URL) -> bool:
        return '.'.join(url.host.split('.')[-2:]) in APIAddress.__args__

#
#
#########################################
