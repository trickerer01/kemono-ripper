# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json
from collections.abc import Callable, Coroutine

from bs4 import BeautifulSoup

from .api import Creator, Kemono, ScannedPost, ScannedPostPost
from .config import Config
from .defs import UTF8
from .logger import Log

__all__ = ('launch',)


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
        post_str = f'[{user}:{pid}] {title}:\n{content}\nlinks:\n {links}'
        listing.append(post_str)
    Log.info('\n'.join(('\n', *listing)) or '\nNothing')


async def creator_dump(kemono: Kemono) -> None:
    results = await kemono.list_creators()
    with open(Config.dest_base / 'creators.json', 'wt', encoding=UTF8, newline='\n') as outfile_creators:
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


async def post_scan_link(kemono: Kemono) -> None:
    results: list[ScannedPost] = []
    for link in Config.links:
        pid, cid, service4 = link
        post = await kemono.scan_post(pid, cid, service4)
        results.append(post)
    _process_scan_results(kemono, results)


async def launch(kemono: Kemono) -> None:
    kemono_actions: dict[str, Callable[[Kemono], Coroutine[None]]] = {
        'creator dump': creator_dump,
        'creator list': creator_list,
        'post list': post_list,
        'post scan id': post_scan_id,
        'post scan link': post_scan_link,
    }

    action_name = ' '.join(getattr(Config, _) for _ in vars(Config) if _.startswith('subcommand')).strip()
    proc: Callable[[Kemono], Coroutine[None]] = kemono_actions.get(action_name)
    assert proc, f'Unknows action \'{action_name}\'!'
    return await proc(kemono)

#
#
#########################################
