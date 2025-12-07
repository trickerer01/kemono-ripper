# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json
import pathlib
import sys
from argparse import ArgumentError
from collections.abc import Callable, Coroutine, Iterable, Sequence

from bs4 import BeautifulSoup

from .api import APIAddress, Creator, Kemono, PostPageScanResult, ScannedPost, ScannedPostPost
from .config import Config
from .defs import CREATORS_NAME_DEFAULT, UTF8
from .downloader import KemonoDownloader
from .logger import Log
from .util import HTTP_PREFIX, HTTPS_PREFIX

__all__ = ('launch',)

from .validators import valid_post_url


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
        links_dict: dict[str, str] = {file['name']: file['path']} if file else {}
        attachments = p['attachments']
        links_dict.update({_['name']: _['path'] for _ in attachments})
        links = '\n '.join(f'{name}: https://{kemono.api_address}{path}' for name, path in links_dict.items())
        if content:
            bs = BeautifulSoup(content, 'html.parser')
            refs: list[str] = [str(_['href']) for _ in bs.find_all('a')]
            refs.extend(f'https://{kemono.api_address}{_["src"]!s}' for _ in bs.find_all('img'))
            links += ('\n' if links and refs else '') + '\n '.join(f'link_{i:d}: {ref}' for i, ref in enumerate(refs))
        post_str = f'[{user}:{pid}] {title}:\n\'{content}\'\nlinks:\n {links}\n'
        listing.append(post_str)
    Log.info('\n'.join(('\n', *listing)) or '\nNothing')


def _parse_posts_file(kemono: Kemono, contents: Iterable[str]) -> list[PostPageScanResult]:
    links: list[PostPageScanResult] = []
    for index, line in enumerate(contents):
        line = line.strip(' \n\ufeff').replace(HTTP_PREFIX, HTTPS_PREFIX)
        if not line:
            continue
        parts = tuple(line.split(' ', maxsplit=1))
        if len(parts) == 1 and parts[0][0].isnumeric():
            parts = tuple(parts[0].split(':', maxsplit=1))
            if len(parts) == 1:
                parts = tuple(parts[0].split('/', maxsplit=1))
        if len(parts) == 1:
            single_part = parts[0]
            # single post id
            if not single_part.replace(HTTPS_PREFIX, '').startswith(APIAddress.__args__):
                links.append(PostPageScanResult(single_part, 0, kemono.api_service, kemono.api_address))
            # full url
            else:
                try:
                    scanned_post = valid_post_url(single_part, False)
                    links.append(scanned_post)
                except ArgumentError:
                    raise ValueError(f'Unable to parse post url from \'{line}\' at line {index + 1:d}')
        else:  # if len(parts) == 2
            # creator id + post id
            creator_id, post_id = parts
            assert creator_id.isnumeric(), f'Unable to parse creator info from C+P \'{line}\' at line {index + 1:d}'
            links.append(PostPageScanResult(post_id, int(creator_id), kemono.api_service, kemono.api_address))
    return links


async def creator_dump(kemono: Kemono) -> None:
    results = await kemono.list_creators()
    with open(Config.dest_base / CREATORS_NAME_DEFAULT, 'wt', encoding=UTF8, newline='\n') as outfile_creators:
        json.dump(sorted(results, key=lambda c: c['name'].lower()), outfile_creators, ensure_ascii=False, indent=4)
        outfile_creators.write('\n')


async def creator_list(kemono: Kemono) -> None:
    results: list[Creator] = []
    cache_path = Config.dest_base / CREATORS_NAME_DEFAULT
    if Config.skip_cache is False and cache_path.is_file():
        with open(cache_path, 'rt', encoding=UTF8) as infile_creators:
            results = json.load(infile_creators)
    results = results or await kemono.list_creators()
    matched = [c for c in results if Config.pattern.lower() in c['name'].lower()]
    Log.info('\n'.join(('\n', *(f'{_["name"]}: {_["id"]}' for _ in matched))) or '\nNothing')


async def creator_rip(kemono: Kemono) -> None:
    results = await kemono.list_posts(Config.creator_id)
    links: list[PostPageScanResult] = []
    for lpost in results:
        post_id = lpost['id']
        service = lpost['service']
        link = PostPageScanResult(post_id, Config.creator_id, service, kemono.api_address)
        links.append(link)
    return await post_rip_url(kemono, links=links)


async def post_list(kemono: Kemono) -> None:
    results = await kemono.list_posts(Config.creator_id)
    listing: list[str] = []
    for lpost in results:
        post_id = lpost['id']
        url = f'https://{kemono.api_address}/{Config.service}/user/{Config.creator_id}/post/{post_id}'
        listing.append(url)
    Log.info('\n'.join(('', *listing)) or '\nNothing')


async def post_scan_id(kemono: Kemono, *, download=False) -> None:
    results: list[ScannedPost] = []
    creator_id = Config.creator_id
    for post_id in Config.post_ids:
        link = PostPageScanResult(post_id, creator_id, kemono.api_service, kemono.api_address)
        posts = await kemono.scan_posts([link])
        results.extend(posts)
        if Config.same_creator:
            creator_id = creator_id or int(posts[0]['post']['user'])
    await _process_scan_results(kemono, results, download=download)


async def post_scan_url(kemono: Kemono, *, links: list[PostPageScanResult] | None = None, download=False) -> None:
    results: list[ScannedPost] = await kemono.scan_posts(links or Config.links)
    await _process_scan_results(kemono, results, download=download)


async def post_scan_file(kemono: Kemono, *, download=False) -> None:
    with open(Config.src_file, 'rt', encoding=UTF8) as infile_posts:
        post_links = _parse_posts_file(kemono, infile_posts)
    return await post_scan_url(kemono, links=post_links, download=download)


async def post_rip_id(kemono: Kemono) -> None:
    return await post_scan_id(kemono, download=True)


async def post_rip_url(kemono: Kemono, *, links: list[PostPageScanResult] | None = None) -> None:
    return await post_scan_url(kemono, links=links, download=True)


async def post_rip_file(kemono: Kemono) -> None:
    return await post_scan_file(kemono, download=True)


def _config_write(config_path: pathlib.Path) -> None:
    Log.info(f'Writing configuration to {config_path.as_posix()}...')
    with open(config_path, 'wt', encoding=UTF8, newline='\n') as outfile_settings:
        json.dump(Config.to_json(), outfile_settings, ensure_ascii=False, indent=4)
        outfile_settings.write('\n')
    Log.info('Done')


async def config_create(*_) -> None:  # noqa RUF029
    config_path = Config.default_config_path()
    if config_path.is_file():
        ans = 'q'
        while ans not in 'YyNn10':
            ans = input(f'File \'{config_path.name}\' already exists! Overwrite? [y/N] ')
        if ans in 'Nn0':
            return
    _config_write(config_path)


async def config_modify(*_) -> None:  # noqa RUF029
    if ' '.join(sys.argv).endswith(Config.get_action_string()):
        Log.error('No settings modifications provided. Aborting')
        return
    config_path = Config.default_config_path()
    _config_write(config_path)


async def launch(kemono: Kemono) -> None:
    kemono_actions: dict[str, Callable[[Kemono], Coroutine[None]]] = {
        'creator dump': creator_dump,
        'creator list': creator_list,
        'creator rip': creator_rip,
        'post list': post_list,
        'post scan id': post_scan_id,
        'post scan url': post_scan_url,
        'post scan file': post_scan_file,
        'post rip id': post_rip_id,
        'post rip url': post_rip_url,
        'post rip file': post_rip_file,
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
