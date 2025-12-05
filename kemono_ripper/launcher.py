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
from collections.abc import Callable, Coroutine, Iterable

from bs4 import BeautifulSoup

from .api import Creator, Kemono, ScannedPost, ScannedPostPost
from .config import Config
from .defs import CREATORS_NAME_DEFAULT, UTF8, PostPageScanResult
from .logger import Log
from .util import HTTP_PREFIX, HTTPS_PREFIX

__all__ = ('launch',)

from .validators import valid_post_url


def _process_scan_results(kemono: Kemono, results) -> None:
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
            if single_part.isnumeric():
                links.append(PostPageScanResult(post_id=int(single_part), creator_id=0, service=kemono.api_service))
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
            assert post_id.isnumeric(), f'Unable to parse post info from C+P \'{line}\' at line {index + 1:d}'
            links.append(PostPageScanResult(post_id=int(post_id), creator_id=int(creator_id), service=kemono.api_service))
    return links


async def creator_dump(kemono: Kemono) -> None:
    results = await kemono.list_creators()
    with open(Config.dest_base / CREATORS_NAME_DEFAULT, 'wt', encoding=UTF8, newline='\n') as outfile_creators:
        json.dump(sorted(results, key=lambda c: c['name'].lower()), outfile_creators, ensure_ascii=False, indent=4)
        outfile_creators.write('\n')


async def creator_list(kemono: Kemono) -> None:
    results: list[Creator] = []
    cache_path = Config.dest_base / 'creators.json'
    if not Config.skip_cache and cache_path.exists():
        with open(cache_path, 'rt', encoding=UTF8) as infile_creators:
            results = json.load(infile_creators)
    results = results or await kemono.list_creators()
    matched = [c for c in results if Config.pattern.lower() in c['name'].lower()]
    Log.info('\n'.join(('\n', *(_['name'] + ': ' + _['id'] for _ in matched))) or '\nNothing')


async def post_list(kemono: Kemono) -> None:
    results = await kemono.list_posts(Config.creator_id)
    listing = []
    for p in results:
        id_ = p['id']
        link = f'https://{kemono.api_address}/{Config.service}/user/{Config.creator_id}/post/{id_}'
        listing.append(link)
    Log.info('\n'.join(('\n', *listing)) or '\nNothing')


async def post_scan_id(kemono: Kemono) -> None:
    results = []
    creator_id = Config.creator_id
    for pid in Config.post_ids:
        post = await kemono.scan_post(pid, creator_id)
        results.append(post)
        creator_id = creator_id or int(post['post']['user'])
    _process_scan_results(kemono, results)


async def post_scan_link(kemono: Kemono, *, links: list[PostPageScanResult] | None = None) -> None:
    results: list[ScannedPost] = []
    for link in links or Config.links:
        post = await kemono.scan_post(link.post_id, link.creator_id, link.service)
        results.append(post)
    _process_scan_results(kemono, results)


async def post_scan_file(kemono: Kemono) -> None:
    with open(Config.src_file, 'rt', encoding=UTF8) as infile_posts:
        post_links = _parse_posts_file(kemono, infile_posts)
    return await post_scan_link(kemono, links=post_links)


def _config_write(config_path: pathlib.Path) -> None:
    Log.info(f'Writing configuration to {config_path.as_posix()}...')
    with open(config_path, 'wt', encoding=UTF8, newline='\n') as outfile_settings:
        json.dump(Config.to_json(), outfile_settings, ensure_ascii=False, indent=4)
        outfile_settings.write('\n')
    Log.info('Done')


async def config_create(*_) -> None:  # noqa RUF029
    config_path = Config.default_config_path()
    if config_path.exists():
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
        'post list': post_list,
        'post scan id': post_scan_id,
        'post scan link': post_scan_link,
        'post scan file': post_scan_file,
        'config create': config_create,
        'config modify': config_modify,
    }

    action_name = Config.get_action_string()
    proc: Callable[[Kemono], Coroutine[None]] = kemono_actions.get(action_name)
    assert proc, f'Unknown action \'{action_name}\'!'
    return await proc(kemono)

#
#
#########################################
