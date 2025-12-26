# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json
import pathlib
import re
import sys
from argparse import ArgumentError
from collections.abc import Callable, Coroutine, Iterable, MutableSequence, Sequence

from bs4 import BeautifulSoup

from .api import APIAddress, Creator, Kemono, ListedPost, PostPageScanResult, ScannedPost, ScannedPostPost, ScannedPostProps, SearchedPost
from .config import Config
from .defs import CACHE_SCANNED_NAME_DEFAULT, CREATORS_NAME_DEFAULT, POST_TAGS_NAME_DEFAULT, SITE_MEGA, UTF8, PathURLJSONEncoder
from .downloader import KemonoDownloader
from .filters import any_filter_matching_ls_post, make_lspost_filters
from .logger import Log
from .util import HTTP_PREFIX, HTTPS_PREFIX
from .validators import valid_post_url

__all__ = ('launch',)


def _need_convert_to_scan_result(post: ListedPost | SearchedPost):
    return ('added' not in post and Config.filter_post_imported) or ('tags' not in post and Config.filter_post_tags)


async def _process_list_search_results(kemono: Kemono, results: MutableSequence[ListedPost] | Sequence[SearchedPost]):
    if results and _need_convert_to_scan_result(results[0]):
        Log.warn(f'Warning: post import date filter detected for listed post, will scan {len(results):d} posts for missing info...')
        links = [PostPageScanResult(_['id'], _['user'], _['service'], kemono.api_address) for _ in results]
        sresults = await scan_posts_cached(kemono, links, ls_results=results)
        Log.info(f'Received {len(sresults)} results. Continuing...')
        results[:] = [_['post'] for _ in sresults]

    filters = make_lspost_filters()
    filtered = dict.fromkeys(filters, 0)
    listing: list[str] = []
    for lpost in reversed(results):
        pid = lpost['id']
        user = lpost['user']
        service = lpost['service']
        title = lpost['title']
        lspost: SearchedPost = SearchedPost(**lpost)  # silence linter
        tags: list[str] = lspost.get('tags') or []
        if spfilter := any_filter_matching_ls_post(lpost, filters):
            filtered[spfilter] += 1
            Log.debug(f'[{user}:{pid}] {title}: post was filtered out by {spfilter!s}! Tags were: {tags!s}')
            continue
        url = f'https://{kemono.api_address}/{service}/user/{user}/post/{pid}'
        msg = (f'{url} \'{lpost["title"]}\', file: \'{lpost["file"].get("name", "Unknown") if lpost["file"] else "None"}\','
               f' {len(lpost["attachments"]):d} attachments, tags: \'{", ".join(tags)}\'')
        listing.append(msg)
    [_.close() for _ in filters if _]
    msgs = (
        '',
        *(s for s in (f'{filtered[f]:d} / {len(results):d} posts were filtered out by {f!s}' if f else '' for f in filters) if s),
        f'{len(listing):d} posts found ({len(results) - len(listing):d} / {len(results):d} filtered out)',
        *listing,
    )
    for msg in msgs:
        Log.info(msg)
    Log.info('Done.')


async def _process_scan_results(kemono: Kemono, results: Sequence[ScannedPost], *, download=False) -> None:
    if download:
        Log.info(f'Sending {len(results):d} posts to download queue...')
        async with KemonoDownloader(kemono, results) as downloader:
            await downloader.run()
        return

    listing: list[str] = []
    for sp in results:
        p: ScannedPostPost = sp['post']
        pid = p['id']
        user = p['user']
        title = p['title']
        content = p['content']
        file = p['file']
        links_dict: dict[str, str] = {file['name']: file['path']} if file and 'name' in file else {}
        attachments = p['attachments']
        links_dict.update({_['name']: _['path'] for _ in attachments})
        links = '\n '.join(f'{name}: https://{kemono.api_address}{path}' for name, path in links_dict.items())
        if content:
            bs = BeautifulSoup(content, 'html.parser')
            refs: list[str] = [str(_['href']) for _ in bs.find_all('a')]
            refs_mega: list[str] = [_ for _ in refs if SITE_MEGA in _ and '#' not in _]
            keys_mega: list[str] = [_.string for _ in bs.find_all(text=re.compile(r'#?\w{28,}'))]
            if len(refs_mega) == len(keys_mega):
                for i in range(len(refs_mega)):
                    key = re.search(r'(#?\w{28,})', keys_mega[i]).group(1)
                    refs[refs.index(refs_mega[i])] = f'{refs_mega[i]}{"" if key.startswith("#") else "#"}{key}'
            refs.extend(f'https://{kemono.api_address}{_["src"]!s}' for _ in bs.find_all('img'))
            links += ('\n' if links and refs else '') + '\n '.join(f'link_{i:d}: {ref}' for i, ref in enumerate(refs))
        post_str = f'[{user}:{pid}] {title}:\n\'{content}\'\nlinks:\n {links}\n'
        listing.append(post_str)
    Log.info('\n'.join(('\n', *listing)) or '\nNothing')


def _parse_posts_file(kemono: Kemono, contents: Iterable[str]) -> list[PostPageScanResult]:
    links: list[PostPageScanResult] = []
    for index, line in enumerate(contents):
        if (lines_range := Config.filter_file_lines) and not lines_range.min <= index + 1 <= lines_range.max:
            continue
        line = line.strip(' \n\ufeff').replace(HTTP_PREFIX, HTTPS_PREFIX)
        if not line:
            continue
        parts = tuple(line.split(' '))
        # supported separators creator:post, creator/post, etc.
        if len(parts) == 1 and parts[0][0].isnumeric():
            parts = tuple(parts[0].split(':', maxsplit=1))
            if len(parts) == 1:
                parts = tuple(parts[0].split('/', maxsplit=1))
        if not parts[0].replace(HTTPS_PREFIX, '').startswith(APIAddress.__args__):
            if len(parts) == 1:
                post_id = parts[0]
                if post_id.isnumeric():
                    Log.debug(f'Parsed single post id {post_id} from \'{line}\' at line {index + 1:d}')
                    links.append(PostPageScanResult(post_id, '', kemono.api_service, kemono.api_address))
                    continue
                else:
                    Log.warn(f'Unsupported from creator+post pair from \'{line}\' at line {index + 1:d}')
            if len(parts) == 2:
                creator_id, post_id = parts
                if creator_id.isnumeric():
                    Log.debug(f'Parsed single creator+post pair {creator_id}+{post_id} from \'{line}\' at line {index + 1:d}')
                    links.append(PostPageScanResult(post_id, creator_id, kemono.api_service, kemono.api_address))
                    continue
                else:
                    Log.debug(f'Unable to parse creator info from creator+post pair from \'{line}\' at line {index + 1:d}')
        part_errors: list[str] = []
        for part_idx, single_part in enumerate(parts):
            try:
                scanned_post = valid_post_url(single_part, False)
                Log.debug(f'Parsed post url {single_part} (index {part_idx:d}) at line {index + 1:d}')
                links.append(scanned_post)
            except ArgumentError:
                part_errors.append(single_part)
        if part_errors:
            Log.warn(f'Unable to parse post url from \'{", ".join(part_errors)}\' at line {index + 1:d}')
    Log.info(f'Parsed {len(links):d} links')
    return links


async def scan_posts_cached(
    kemono: Kemono,
    links: Iterable[PostPageScanResult],
    *,
    ls_results: Iterable[ListedPost] | Iterable[SearchedPost] | None = None,
) -> list[ScannedPost]:
    if Config.skip_cache:
        return await kemono.scan_posts(links)
    links_dict: dict[str, PostPageScanResult] = {_.as_cache_key(): _ for _ in links}
    orig_count = len(links_dict)
    ls_results_dict: dict[str, str] = {}
    for _ in ls_results or []:
        lsp: ScannedPostPost = _.get('post', _)
        lrd_key = PostPageScanResult(lsp['id'], lsp['user'], lsp['service'], kemono.api_address)
        ls_results_dict[lrd_key.as_cache_key()] = lsp.get('published', '')
    cached: dict[str, ScannedPost] = {}
    Log.info(f'Looking for cache file \'{CACHE_SCANNED_NAME_DEFAULT}\'...')
    cache_file_path = Config.default_config_path().with_name(CACHE_SCANNED_NAME_DEFAULT)
    with open(cache_file_path, 'rt+' if cache_file_path.is_file() else 'wt+', encoding=UTF8, newline='\n') as inout_file_cache:
        cache_json: dict[str, ScannedPost] = {}
        try:
            cache_json.update(json.load(inout_file_cache))
            for cache_key_r, cache_entry in cache_json.items():
                cpost = cache_entry['post']
                if cache_key_r in ls_results_dict and cpost['published'] == ls_results_dict.get(cache_key_r):  # can be None on both sides
                    links_dict.pop(cache_key_r)
            Log.info(f'Found {orig_count - len(links_dict):d} fully cached entries!')
        except json.JSONDecodeError:
            pass
        if links_dict and orig_count != len(links_dict):
            Log.info(f'Fetching remaining {len(links_dict):d} posts...')
        if sresults := await kemono.scan_posts([links_dict[_] for _ in links_dict]):
            for sp in sresults:
                post = sp['post']
                cache_key_w = PostPageScanResult(post['id'], post['user'], post['service'], kemono.api_address).as_cache_key()
                cached[cache_key_w] = ScannedPost(
                    post=sp['post'],
                    attachments=sp.get('attachments', []),
                    previews=sp.get('previews', []),
                    videos=sp.get('videos', []),
                    props=sp.get('props', ScannedPostProps(flagged=0, revisions=[])),
                )
            Log.info(f'Writing updated cache back to \'{CACHE_SCANNED_NAME_DEFAULT}\'...')
            inout_file_cache.flush()
            inout_file_cache.seek(0)
            inout_file_cache.truncate()
            json.dump(cache_json | cached, inout_file_cache, ensure_ascii=False, indent=Config.indent, cls=PathURLJSONEncoder)
            inout_file_cache.write('\n')
    return [cached[_] for _ in cached]


async def creator_dump(kemono: Kemono) -> None:
    results = await kemono.list_creators()
    results_sorted = sorted(results, key=lambda c: c['name'].lower())
    with open(Config.dest_base / CREATORS_NAME_DEFAULT, 'wt', encoding=UTF8, newline='\n') as outfile_creators:
        json.dump(
            [(creator['name'], creator['id'], creator['service']) for creator in results_sorted] if Config.prune else results_sorted,
            outfile_creators, ensure_ascii=False, indent=Config.indent,
        )
        outfile_creators.write('\n')


async def creator_list(kemono: Kemono) -> None:
    results: list[Creator] = []
    cache_path = Config.dest_base / CREATORS_NAME_DEFAULT
    if Config.skip_cache is False and cache_path.is_file():
        with open(cache_path, 'rt', encoding=UTF8) as infile_creators:
            results = json.load(infile_creators)
    results = results or await kemono.list_creators()
    matched = [c for c in results if Config.pattern.lower() in c['name'].lower()]
    Log.info('\n'.join(('\n', *(f'[{_["service"]}] {_["name"]}: {_["id"]}' for _ in matched))) or '\nNothing')


async def creator_rip(kemono: Kemono) -> None:
    results = await kemono.list_posts(Config.creator_id)
    links: list[PostPageScanResult] = []
    for lpost in results:
        pid = lpost['id']
        # user = lpost['user']
        # title = lpost['title']
        service = lpost['service']
        link = PostPageScanResult(pid, Config.creator_id, service, kemono.api_address)
        links.append(link)
    if links:
        await post_rip_url(kemono, links=links)


async def post_list(kemono: Kemono) -> None:
    results = await kemono.list_posts(Config.creator_id)
    await _process_list_search_results(kemono, results)


async def post_search(kemono: Kemono) -> None:
    results = await kemono.search_posts(Config.search_string, Config.search_tags)
    await _process_list_search_results(kemono, results)


async def post_scan_id(kemono: Kemono, *, download=False) -> None:
    results: list[ScannedPost] = []
    creator_id = Config.creator_id
    for post_id in Config.post_ids:
        link = PostPageScanResult(post_id, creator_id, kemono.api_service, kemono.api_address)
        posts = await scan_posts_cached(kemono, [link])
        results.extend(posts)
        if Config.same_creator:
            creator_id = creator_id or posts[0]['post']['user']
    await _process_scan_results(kemono, results, download=download)


async def post_scan_url(kemono: Kemono, *, links: list[PostPageScanResult] | None = None, download=False) -> None:
    results: list[ScannedPost] = await scan_posts_cached(kemono, links or Config.links)
    await _process_scan_results(kemono, results, download=download)


async def post_scan_file(kemono: Kemono, *, download=False) -> None:
    with open(Config.src_file, 'rt', encoding=UTF8) as infile_posts:
        lines_str = (
            f' lines {int(Config.filter_file_lines.min):d}-{int(Config.filter_file_lines.max):d}' if Config.filter_file_lines else '')
        Log.info(f'Parsing \'.../{Config.src_file.relative_to(Config.src_file.parent.parent).as_posix()}\'{lines_str}...')
        post_links = _parse_posts_file(kemono, infile_posts)
    return await post_scan_url(kemono, links=post_links, download=download)


async def post_rip_id(kemono: Kemono) -> None:
    return await post_scan_id(kemono, download=True)


async def post_rip_url(kemono: Kemono, *, links: list[PostPageScanResult] | None = None) -> None:
    return await post_scan_url(kemono, links=links, download=True)


async def post_rip_file(kemono: Kemono) -> None:
    return await post_scan_file(kemono, download=True)


async def post_tag_dump(kemono: Kemono) -> None:
    results = await kemono.list_tags()
    results_sorted = sorted(results, key=lambda t: t['tag'].lower())
    with open(Config.dest_base / POST_TAGS_NAME_DEFAULT, 'wt', encoding=UTF8, newline='\n') as outfile_post_tags:
        json.dump(
            [(tag['tag'], tag['post_count']) for tag in results_sorted] if Config.prune else results_sorted,
            outfile_post_tags, ensure_ascii=False, indent=Config.indent,
        )
        outfile_post_tags.write('\n')


async def _config_write(config_path: pathlib.Path, *, use_backup=False) -> None:  # noqa RUF029
    backup_file_path = config_path.with_suffix('.bak') if use_backup and config_path.is_file() else None
    try:
        Log.info(f'Writing configuration to {config_path.as_posix()}...')
        if config_path.is_file():
            with open(config_path, 'rt+', encoding=UTF8, newline='\n') as inout_file_config:
                if backup_file_path:
                    backup_json = json.load(inout_file_config)
                    json_to_save = backup_json | Config.to_json()
                    Log.debug(f'Saving backup to \'{backup_file_path.as_posix()}\'...')
                    with open(backup_file_path, 'wt', encoding=UTF8, newline='\n') as outfile_backup:
                        json.dump(backup_json, outfile_backup, ensure_ascii=False, indent=Config.indent, cls=PathURLJSONEncoder)
                    inout_file_config.flush()
                    inout_file_config.seek(0)
                    inout_file_config.truncate()
                else:
                    json_to_save = Config.to_json()
                json.dump(json_to_save, inout_file_config, ensure_ascii=False, indent=Config.indent, cls=PathURLJSONEncoder)
                inout_file_config.write('\n')
            # if backup_file_path and backup_file_path.is_file():
            #     Log.debug(f'Removing backup file \'{backup_file_path.as_posix()}\'...')
            #     backup_file_path.unlink(missing_ok=True)
        else:
            with open(config_path, 'wt', encoding=UTF8, newline='\n') as out_file_config:
                json.dump(Config.to_json(), out_file_config, ensure_ascii=False, indent=Config.indent, cls=PathURLJSONEncoder)
                out_file_config.write('\n')
        Log.info('Done')
    except Exception:
        Log.error(f'Failed to write to {config_path.as_posix()}!')


async def config_create(*_) -> None:
    config_path = Config.default_config_path()
    if config_path.is_file():
        ans = 'q'
        while ans not in 'YyNn10':
            ans = input(f'File \'{config_path.name}\' already exists! Overwrite? [y/N] ')
        if ans in 'Nn0':
            Log.info('Aborted')
            return
    await _config_write(config_path)


async def config_modify(*_) -> None:
    if ' '.join(sys.argv).endswith(Config.get_action_string()):
        Log.error('No settings modifications provided. Aborting')
        return
    config_path = Config.default_config_path()
    await _config_write(config_path, use_backup=True)


async def launch(kemono: Kemono) -> None:
    kemono_actions: dict[str, Callable[[Kemono], Coroutine[None]]] = {
        'creator dump': creator_dump,
        'creator list': creator_list,
        'creator rip': creator_rip,
        'post list': post_list,
        'post search': post_search,
        'post scan id': post_scan_id,
        'post scan url': post_scan_url,
        'post scan file': post_scan_file,
        'post rip id': post_rip_id,
        'post rip url': post_rip_url,
        'post rip file': post_rip_file,
        'post tags dump': post_tag_dump,
        'config create': config_create,
        'config modify': config_modify,
    }

    action_name = Config.get_action_string()
    assert action_name in kemono_actions, f'Unknown action \'{action_name}\'!'
    proc = kemono_actions[action_name]
    return await proc(kemono)

#
#
#########################################
