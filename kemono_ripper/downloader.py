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
from asyncio import Lock as AsyncLock
from asyncio import Semaphore
from asyncio.queues import Queue as AsyncQueue
from asyncio.tasks import as_completed, gather, sleep
from collections import defaultdict, deque
from collections.abc import Callable, Iterable, Sequence
from typing import Final, Protocol

from yarl import URL

from .analyzer import is_link_extension_supported, is_link_native, is_link_supported
from .api import (
    DownloadFlags,
    DownloadMode,
    DownloadResult,
    Kemono,
    KemonoErrorCodes,
    Mem,
    PostInfo,
    PostLinkInfo,
    State,
    URLProbeResult,
)
from .cache import Cache
from .config import Config, ExternalURLHandlerConfig
from .defs import (
    POST_DONE_FILE_NAME_DEFAULT,
    POST_TAGS_PER_POST_INFO_NAME_DEFAULT,
    UTF8,
    PathURLJSONEncoder,
    SupportedExternalWebsites,
)
from .download_direct import DirectLinkDownloader
from .filters import any_filter_matching_post_link, make_post_link_filters
from .logger import Log

try:
    import mediafire_download as handler_mediafire
except ImportError:
    handler_mediafire = None
try:
    import mega_download as handler_mega
except ImportError:
    handler_mega = None

__all__ = ('KemonoDownloader',)


# external downloaders
class ExternalURLHandler(Protocol):
    _semaphore: Semaphore

    @staticmethod
    async def run(url: URL, config: ExternalURLHandlerConfig) -> list[pathlib.Path | None]: ...

    @staticmethod
    def name() -> str: ...

    @staticmethod
    def app_name() -> str: ...


class DirectLinkHandler:
    _semaphore: Semaphore  # unused

    @staticmethod
    async def run(url: URL, config: ExternalURLHandlerConfig) -> list[pathlib.Path | None]:
        async with DirectLinkDownloader([str(url)], config) as direct_downloader:
            return await direct_downloader.run()

    @staticmethod
    def name() -> str:
        return 'DirectLink'

    @staticmethod
    def app_name() -> str:
        return '<direct-download>'


class UnknownLinkHandler(DirectLinkHandler):
    @staticmethod
    def name() -> str:
        return 'UnknownDirectLink'

    @staticmethod
    def app_name() -> str:
        return '<unknown-direct-download>'

    @staticmethod
    async def probe(url: URL, config: ExternalURLHandlerConfig, probe_func: Callable[[str], bool]) -> URLProbeResult:
        async with DirectLinkDownloader([str(url)], config) as direct_downloader:
            return await direct_downloader.probe(probe_func)


class MegaURLHandler:
    _semaphore: Semaphore = Semaphore(1)

    @staticmethod
    async def run(url: URL, config: ExternalURLHandlerConfig) -> list[pathlib.Path | None]:
        async with MegaURLHandler._semaphore:
            return await handler_mega.MegaDownloader([str(url)], config).run()

    @staticmethod
    def name() -> str:
        return 'Mega'

    @staticmethod
    def app_name() -> str:
        return handler_mega.APP_NAME


class MediafireURLHandler:
    _semaphore: Semaphore = Semaphore(1)

    @staticmethod
    async def run(url: URL, config: ExternalURLHandlerConfig) -> list[pathlib.Path | None]:
        async with MediafireURLHandler._semaphore:
            return await handler_mediafire.MediafireDownloader([str(url)], config).run()

    @staticmethod
    def name() -> str:
        return 'Mediafire'

    @staticmethod
    def app_name() -> str:
        return handler_mediafire.APP_NAME


class ExternalURLDownloader:
    def __init__(self, url: URL) -> None:
        self._url = url
        self._probed = False

    @property
    def _handler(self) -> ExternalURLHandler:
        return EXTERNAL_URL_HANDLERS.get(self._url.host, UnknownLinkHandler())

    def valid(self) -> bool:
        return self._url.host in EXTERNAL_URL_HANDLERS

    def name(self) -> str:
        return self._handler.name()

    def app_name(self) -> str:
        return self._handler.app_name()

    async def probe(self, plink_id: str, url: URL, config: ExternalURLHandlerConfig, probe_func: Callable[[str], bool]) -> URLProbeResult:
        dhandler = UnknownLinkHandler()
        try:
            presult = await dhandler.probe(url, config, probe_func)
            assert presult.suffix and presult.size > 0
            Log.info(f'{plink_id} \'{dhandler.app_name()}\' has successfully probed {self._url!s}: {presult!s}')
            self._probed = True
            return presult
        except Exception:
            import traceback
            Log.warn(f'{traceback.format_exc(limit=0)}\n{plink_id} \'{dhandler.app_name()}\': probe of {self._url!s} has failed!')

    async def download(self, plink_id: str, url: URL, config: ExternalURLHandlerConfig) -> list[pathlib.Path | None]:
        try:
            assert self.valid() or self._probed
            mresults = await self._handler.run(url, config)
            Log.info(f'{plink_id} \'{self.app_name()}\' has successfully handled {self._url!s} ({len(mresults)} files)')
            return mresults
        except Exception:
            import traceback
            Log.error(f'{traceback.format_exc()}\n{plink_id} \'{self.app_name()}\' FAILED to handle {self._url!s}!')
            return []


def register_external_downloader(host: SupportedExternalWebsites, handler: ExternalURLHandler) -> None:
    EXTERNAL_URL_HANDLERS[host] = handler


EXTERNAL_URL_HANDLERS: dict[str, ExternalURLHandler] = {}


# end external downloaders


class KemonoDownloader:
    def __init__(self, kemono: Kemono, post_infos: Sequence[PostInfo]) -> None:
        self._kemono: Final[Kemono] = kemono
        self._post_info: Final[dict[str, PostInfo]] = {}
        self._post_link_filters = make_post_link_filters()

        self._queue_produce: deque[PostInfo] = deque()
        self._queue_consume: AsyncQueue[PostInfo] = AsyncQueue(Config.max_jobs)
        self._post_link_download_semaphore: Semaphore = Semaphore(Config.max_jobs)

        self._downloaded_count: dict[str, int] = defaultdict(int)
        self._already_exist_count: dict[str, int] = defaultdict(int)
        self._skipped_count: dict[str, int] = defaultdict(int)
        self._404_count: dict[str, int] = defaultdict(int)
        self._external_count: dict[str, int] = defaultdict(int)
        self._unsupported_count: dict[str, int] = defaultdict(int)
        self._partial_count: dict[str, int] = defaultdict(int)

        self._downloads_active: dict[PostInfo, list[PostLinkInfo]] = defaultdict(list[PostLinkInfo])
        self._writes_active: dict[PostInfo, list[PostLinkInfo]] = defaultdict(list[PostLinkInfo])
        self._failed_items: dict[PostInfo, list[PostLinkInfo]] = defaultdict(list[PostLinkInfo])

        self._sequence_lock: Final[AsyncLock] = AsyncLock()
        self._active_downloads_lock: Final[AsyncLock] = AsyncLock()
        self._active_writes_lock: Final[AsyncLock] = AsyncLock()

        self._orig_count: Final[int] = self._prepare_post_download_info(post_infos)

        self._queue_produce.extend(post for _, post in self._post_info.items())

        register_external_downloader(SupportedExternalWebsites.Catbox, DirectLinkHandler())
        register_external_downloader(SupportedExternalWebsites.WebmShare, DirectLinkHandler())
        register_external_downloader(SupportedExternalWebsites.Dropbox, DirectLinkHandler())
        if handler_mega:
            register_external_downloader(SupportedExternalWebsites.Mega, MegaURLHandler())
        if handler_mediafire:
            register_external_downloader(SupportedExternalWebsites.Mediafire, MediafireURLHandler())

    async def __aenter__(self) -> KemonoDownloader:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return

    async def _at_post_link_start(self, post: PostInfo, plink: PostLinkInfo) -> None:
        async with self._active_downloads_lock:
            self._downloads_active[post].append(plink)
        Log.trace(f'[queue] [{post.creator_id}:{post.post_id}] \'{plink.name}\' added to active')

    async def _at_post_link_finish(self, post: PostInfo, plink: PostLinkInfo, result: DownloadResult) -> None:
        plink.status.result = result
        plink.status.state = State.FAILED if ((1 << plink.status.result) & DownloadResult.RESULT_MASK_CRITICAL) else State.DONE
        if plink.status.result in (DownloadResult.SUCCESS, DownloadResult.FAIL_ALREADY_EXISTS):
            plink.status.flags |= DownloadFlags.COMPLETED
            await Cache.update_post_link_info_cache(plink)
        async with self._active_downloads_lock:
            if plink in self._downloads_active[post]:
                self._downloads_active[post].remove(plink)
                Log.trace(f'[queue] [{post.creator_id}:{post.post_id}] \'{plink.name}\' removed from active')
            if result == DownloadResult.FAIL_ALREADY_EXISTS:
                self._already_exist_count[post.post_id] += 1
            elif result in (DownloadResult.FAIL_SKIPPED, DownloadResult.FAIL_FILTERED_OUT):
                self._skipped_count[post.post_id] += 1
            elif result == DownloadResult.FAIL_NOT_FOUND:
                self._404_count[post.post_id] += 1
            elif result == DownloadResult.FAIL_RETRIES:
                self._failed_items[post].append(plink)
            elif result == DownloadResult.SUCCESS:
                self._downloaded_count[post.post_id] += 1
            elif result == DownloadResult.FAIL_UNSUPPORTED:
                self._unsupported_count[post.post_id] += 1
            elif result == DownloadResult.SUCCESS_PARTIAL:
                self._partial_count[post.post_id] += 1
            if plink.status.flags & DownloadFlags.EXTERNAL_LINK:
                self._external_count[post.post_id] += 1

    async def _at_post_start(self, post: PostInfo) -> None:
        async with self._active_downloads_lock:
            self._downloads_active[post] = []
        Log.info(f'Processing post [{post.creator_id}:{post.post_id}] \'{post.title}\'...')

    async def _at_post_finish(self, post: PostInfo) -> None:
        pid = f'[{post.creator_id}:{post.post_id}] \'{post.title}\''
        async with self._active_downloads_lock:
            assert post in self._downloads_active
            results = [_.status.result for _ in post.links]
            assert not any(_ == DownloadResult.UNKNOWN for _ in results)
            success = len([_ for _ in results if _ == DownloadResult.SUCCESS])
            fail_404 = len([_ for _ in results if _ == DownloadResult.FAIL_NOT_FOUND])
            fail_tries = len([_ for _ in results if _ == DownloadResult.FAIL_RETRIES])
            exists = len([_ for _ in results if _ == DownloadResult.FAIL_ALREADY_EXISTS])
            skipped = len([_ for _ in results if _ == DownloadResult.FAIL_SKIPPED])
            filtered = len([_ for _ in results if _ == DownloadResult.FAIL_FILTERED_OUT])
            unsupported = len([_ for _ in results if _ == DownloadResult.FAIL_UNSUPPORTED])
            partial = len([_ for _ in results if _ == DownloadResult.SUCCESS_PARTIAL])
            external = len([_ for _ in post.links if _.status.flags & DownloadFlags.EXTERNAL_LINK])
            if len(results) > unsupported or not results:
                Log.info(f'[queue] post {pid}: Done: {len(post.links) - external:d}+{external:d} links:'
                         f' {success:d} downloaded, {fail_tries:d} failed, {skipped:d} skipped,'
                         f' {filtered:d} filtered out, {exists:d} already exists, {fail_404:d} not found,'
                         f' {unsupported:d} unsupported, {partial:d} partial success (external)')
            else:
                links_str = '\n'.join(str(_.url) for _ in post.links)
                Log.info(f'[queue] post {pid}: None of {len(post.links):d} links are supported:\n{links_str}')

            if unsupported == 0 and success + exists == len(results):
                post.status.flags |= DownloadFlags.COMPLETED
                await Cache.update_post_info_cache(post)

            self._downloads_active.pop(post)
            post.dest.mkdir(parents=True, exist_ok=True)
            post.dest.joinpath(POST_DONE_FILE_NAME_DEFAULT).touch(exist_ok=True)

            Log.trace(f'[queue] post {post.post_id} \'{post.title}\' removed from active')
            if (num_left := len(self._downloads_active)) < Config.max_jobs - 1 and len(self._queue_produce) == 0:
                msgs = (
                    f'{num_left:d} posts in queue:',
                    *(f'[{_.creator_id}:{_.post_id}] \'{_.title}\'' for _ in self._downloads_active),
                )
                for msg in msgs:
                    Log.debug(msg)

    async def _download_post(self, post: PostInfo) -> None:
        async def download_post_link_wrapper(plink: PostLinkInfo) -> None:
            async with self._post_link_download_semaphore:
                return await self._download_post_link(post, plink)

        post.status.state = State.DOWNLOADING
        Log.trace(f'[{post.creator_id}:{post.post_id}] Saving info to {post.local_path}/{POST_TAGS_PER_POST_INFO_NAME_DEFAULT}')
        post.dest.mkdir(parents=True, exist_ok=True)
        with open(post.dest / POST_TAGS_PER_POST_INFO_NAME_DEFAULT, 'wt', encoding=UTF8, newline='\n', errors='replace') as outfile_tags:
            json.dump(post, outfile_tags, ensure_ascii=False, indent=Config.indent, cls=PathURLJSONEncoder)
            outfile_tags.write('\n')
        tasks = [download_post_link_wrapper(_) for _ in post.links]
        _ = await gather(*tasks)
        post.status.state = State.DONE

    async def _download_post_link(self, post: PostInfo, plink: PostLinkInfo) -> None:
        await self._at_post_link_start(post, plink)
        plink_id = f'[{post.creator_id}:{post.post_id}] \'{plink.name}\''
        plink.status.state = State.SCANNING
        url = plink.url
        url_str = str(url)
        link_native = is_link_native(url)
        link_skipped = bool(
            (Config.skip_external and not link_native) or
            (Config.skip_completed and (plink.status.flags & DownloadFlags.COMPLETED)),
        )
        link_supported = is_link_supported(url)
        handler_ex = ExternalURLDownloader(url)
        handler_config = ExternalURLHandlerConfig(Config, url.host, dest_base=plink.path)
        handler_valid = handler_ex.valid()
        if (not handler_valid and not link_supported and not link_skipped and Config.probe_unknown_links
           and is_link_extension_supported(url.suffix)):
            handler_config.proxy = ''  # assume unknown link is reachable always
            presult = await handler_ex.probe(plink_id, url, handler_config, is_link_extension_supported)
            if presult.suffix and presult.size > 0:
                handler_valid = True

        if link_skipped:
            Log.warn(f'{plink_id}: Skipping link {url_str} due to \'--skip-{"external" if not link_native else "completed"}\' flag!')
            dresult = DownloadResult.FAIL_SKIPPED
        elif plfilter := any_filter_matching_post_link(plink, self._post_link_filters):
            Log.warn(f'{plink_id}: Link {url_str} was filtered out by {plfilter!s}. Skipped!')
            dresult = DownloadResult.FAIL_FILTERED_OUT
        elif handler_valid:
            Log.info(f'{plink_id}: {handler_ex.name()} url detected, using \'{handler_ex.app_name()}\' to handle {url_str}')
            plink.status.state = State.DOWNLOADING
            mresults = await handler_ex.download(plink_id, url, handler_config)
            succ_count = len([isinstance(_, pathlib.Path) and _.is_file() for _ in mresults])
            Log.info(f'{plink_id}: {handler_ex.app_name()} handled {url_str} with {succ_count:d} / {len(mresults):d} success')
            dresult = (
                DownloadResult.SUCCESS if succ_count == len(mresults)
                else DownloadResult.SUCCESS_PARTIAL if succ_count
                else DownloadResult.FAIL_RETRIES
            )
        elif link_supported:
            Log.info(f'{plink_id}: Processing {url_str} => {plink.local_path}')
            plink.status.state = State.DOWNLOADING
            await self.add_to_writes(post, plink, True)
            ec = await self._kemono.download_url(post, plink)
            await self.remove_from_writes(post, plink, True)
            if plink.path.is_file():
                file_size = plink.path.stat().st_size
                if file_size != plink.status.size:
                    Log.error(f'Bytes written mismatch for {plink.local_path}'
                              f' (size {file_size:d} vs expected {plink.status.size:d})')
                    ec = ec or KemonoErrorCodes.ENOTFOUND
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
        else:
            Log.warn(f'{plink_id}: Skipping unsupported link {url_str}...')
            dresult = DownloadResult.FAIL_UNSUPPORTED
        await self._at_post_link_finish(post, plink, dresult)

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
        partial_count = sum(self._partial_count.values())
        Log.info(f'\nDone. {len(self._post_info):d} posts: '
                 f'{downloaded_count:d} / {self._orig_count - external_count:d}+{external_count:d} post links downloaded, '
                 f'{already_exist_count:d} already existed, {skipped_count:d} skipped, {not_found_count:d} not found, '
                 f'{unsupported_count:d} unsupported, {partial_count:d} partial success (external)')
        if len(self._queue_produce) > 0:
            Log.fatal(f'total queue is still at {len(self._queue_produce):d} != 0!')
        if len(self._writes_active) > 0:
            Log.fatal(f'active writes count is still at {len(self._writes_active):d} != 0!')
        if len(self._failed_items) > 0:
            fitems = ['\n'.join([f'{post.service}:{post.creator_id}:{post.post_id}'
                                 f' {plink.url!s} => {plink.local_path}'
                                 for plink in plinks]) for post, plinks in self._failed_items.items()]
            Log.fatal(f'\nFailed items:\n{newline.join(fitems)}')

    async def run(self) -> None:
        for cv in as_completed([self._prod(), *(self._cons() for _ in range(Config.max_jobs))]):
            await cv
        await self._queue_consume.join()
        await self._after_download()

    async def is_writing(self, post: PostInfo) -> bool:
        async with self._active_writes_lock:
            return post in self._writes_active

    async def add_to_writes(self, post: PostInfo, plink: PostLinkInfo, safe=False) -> None:
        async with self._active_writes_lock:
            if safe is False or post not in self._writes_active or plink not in self._writes_active[post]:
                self._writes_active[post].append(plink)

    async def remove_from_writes(self, post: PostInfo, plink: PostLinkInfo, safe=False) -> None:
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

    async def _try_fetch_next(self) -> PostInfo | None:
        async with self._sequence_lock:
            if self._queue_produce:
                return self._queue_produce.popleft()
        return None

    def _prepare_post_download_info(self, post_infos: Iterable[PostInfo]) -> int:
        post_strings: list[str] = []
        for post_info in post_infos:
            pid = post_info.post_id
            user = post_info.creator_id
            title = post_info.title
            links = post_info.links
            self._post_info[pid] = post_info

            links_str = '\n'.join(f' {_.url!s} => {_.local_path}' for _ in links)
            post_strings.append(f'Post [{user}:{pid}] \'{title}\': {len(links):d} links:\n{links_str}')

        post_msgs = (f'{len(post_strings):d} posts in queue:', *post_strings)
        for post_msg in post_msgs:
            Log.info(post_msg)
        return sum(len(_.links) for _ in self._post_info.values())

#
#
#########################################
