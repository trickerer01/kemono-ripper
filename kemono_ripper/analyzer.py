# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
import random
import re
from collections.abc import Iterable

from bs4 import BeautifulSoup
from yarl import URL

from .api import APIAddress, DownloadFlags, DownloadStatus, PostInfo, PostLinkInfo, ScannedPost, ScannedPostPost
from .cache import Cache
from .config import Config
from .defs import FILE_NAME_FULL_MAX_LEN, SupportedExternalWebsites
from .download_direct import DirectLinkDownloader
from .formatter import format_path
from .logger import Log
from .util import sanitize_path

__all__ = ('extract_link_name', 'gather_post_info', 'is_link_extension_supported', 'is_link_native', 'is_link_supported')

SUPPORTED_TAGS = (
    ('a', 'href'),
    ('img', 'src'),
)

SUPPORTED_EXTENSIONS = {
    '.mp4', '.webm', '.m4v', '.mov', '.3gp',
    '.ogg', '.wav', '.mp3', '.flac',
    '.webp', '.avif', '.gif', '.png', '.apng', '.jpg', '.jpeg',
    '.fbx', '.blend', '.stl', '.3dx', '.bin',
    '.zip', '.rar', '.gz', '.tar.gz', '.7z',
}


def extract_link_name(url: URL) -> str:
    return url.query.getone('f', url.name)


def link_without_subdomain(url: URL) -> URL:
    return url.with_host('.'.join(url.host.split('.')[-2:])) if url.host else url


def is_link_native(url: URL) -> bool:
    return link_without_subdomain(url).host in APIAddress.__args__


def is_link_supported(url: URL) -> bool:
    return is_link_native(url)


def is_link_extension_supported(ext: str) -> bool:
    return (ext or 'UNK') in SUPPORTED_EXTENSIONS


async def gather_post_info(posts: Iterable[ScannedPost], api_address: APIAddress) -> list[PostInfo]:
    def next_file_name(name_base: str) -> str:
        next_file_name.last_post_idx = getattr(next_file_name, 'last_post_idx', 0)
        if next_file_name.last_post_idx != spost_idx:
            next_file_name.last_post_idx = spost_idx
            next_file_name.name_idx = 0
        next_file_name.name_idx = getattr(next_file_name, 'name_idx', 0) + 1
        return f'{next_file_name.name_idx:02d}_{name_base}'

    def next_api_address() -> URL:
        next_api_address.name_idx = (getattr(next_api_address, 'name_idx', random.randint(1, 99)) + random.randint(1, 99)) % 4 + 1
        return URL(f'https://n{next_api_address.name_idx:d}.{api_address}')

    post_infos: list[PostInfo] = []
    for spost_idx, spost in enumerate(posts):  # noqa B007  # stupid ruff
        post: ScannedPostPost = spost['post']

        if not post['title']:
            post['title'] = 'Untitled'

        pid = post['id']
        user = post['user']
        service = post['service']
        title = post['title']
        imported = post['added'] or ''
        published = post['published'] or ''
        edited = post['edited'] or ''

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

        if embed := post['embed']:
            eurl = URL(embed['url'])
            links_dict.update({eurl: embed['subject'] or 'Untitled'})

        if attachments := post['attachments']:
            for attachment in attachments:
                aurl = URL(attachment['path'])
                links_dict.update({aurl: attachment.get('name') or 'Untitled'})

        content = post['content']
        if content and len(content) >= 40:
            link_idx = len(links_dict)
            bs = BeautifulSoup(content, 'html.parser')
            for tag_type, tag_name in SUPPORTED_TAGS:
                bs_tags = bs.find_all(tag_type)
                check_mega_keys = tag_type == 'a'
                keys_mega: list[str] = [
                    re.search(r'([-\d\w]{22,})', _.string).group(1)
                    for _ in bs.find_all(string=re.compile(r'(?:^|[^/]+ )[!#]?[-\d\w]{22,}')) if not any(s * 4 in _ for s in '-_')
                ] if check_mega_keys else []
                paths_mega: list[str] = [  # file/folder paths v1
                    re.search(r'(#F?![-\d\w]{8}![-\d\w]{22,})', _.string).group(1)
                    for _ in bs.find_all(string=re.compile(r'(?:^|[^/]+ )#F?![-\d\w]{8}![-\d\w]{22,}'))
                ] if check_mega_keys else []
                mkey_idx = mpath_idx = 0
                for bs_tag in bs_tags:
                    if bs_tag.get(tag_name) is None:
                        Log.warn(f'[{user}:{pid}] {title}: tag \'{tag_name}\' was not found in content element {bs_tag!s}. Skipped')
                        continue
                    url = URL(bs_tag[tag_name].strip())
                    if '/' not in str(url):
                        Log.warn(f'[{user}:{pid}] {title}: found tag \'{tag_name}\' with no address: {bs_tag!s}. Skipped')
                        continue
                    if not url.is_absolute() and url.path.startswith('/data'):
                        url = url.with_path(url.path[len('/data'):])
                    if url not in links_dict:
                        if not url.is_absolute():
                            url_purged = url.with_query('')
                            link_name = f'unnamed_{link_idx:02d}' if url == url_purged else extract_link_name(url)
                        elif is_link_supported(url):
                            link_name = extract_link_name(url)
                        elif is_link_extension_supported(url.suffix) and Config.probe_unknown_links:
                            Log.warn(f'Unknown link {url!s} contains extension. Will be probed for media type')
                            link_name = extract_link_name(url)
                        else:
                            link_idx += 1
                            link_name = f'unnamed_{link_idx:02d}'
                            if url.host == SupportedExternalWebsites.Mega and not url.fragment:
                                if mpath_idx < len(paths_mega) and url.path == '/':
                                    mpath = paths_mega[mpath_idx]
                                    url = url.with_path(mpath, encoded=True)
                                    mpath_idx += 1
                                elif mkey_idx < len(keys_mega) and len(url.path) > 4:
                                    mkey = keys_mega[mkey_idx]
                                    url = url.with_fragment(mkey)
                                    mkey_idx += 1
                        links_dict.update({url: link_name})

        if file := post['file']:
            if 'name' in file:
                furl = URL(file['path'])
                links_dict.update({furl: file['name']})

        if videos := spost.get('videos'):
            for video in videos:
                vurl = URL(video['path'])
                links_dict.update({vurl: video['name']})

        tags = post['tags'] or []
        dest = Config.dest_base.joinpath(format_path(post, Config.path_format))

        links: dict[str, PostLinkInfo] = {}
        for link_base, name in links_dict.items():
            # check if MEGA links were properly parsed / fixed
            if link_base.host == SupportedExternalWebsites.Mega and len(link_base.path) + len(link_base.fragment) < 26:
                Log.error(f'{SupportedExternalWebsites.Mega} link {link_base!s} was not parsed properly! Skipped!!')
                continue
            if link_base.is_absolute() and not link_base.scheme:  # boosty content <img>
                link_base = link_base.with_scheme('https')
            if not link_base.host:
                link_base = next_api_address().with_path(f'data{link_base.path}')
                Log.trace(f'Fixing link with no host -> \'{link_base!s}\'')
            if DirectLinkDownloader.is_link_supported(link_base):
                link_norm = DirectLinkDownloader.normalize_link(link_base)
                if link_norm != link_base:
                    Log.debug(f'Normalized link {link_base!s} -> {link_norm!s}')
                    link_base = link_norm
            if not pathlib.Path(name).suffix:
                name = f'{name}{link_base.suffix}'

            link = link_base
            name_append = name
            lpath = dest.joinpath(sanitize_path(next_file_name(name_append)))
            while (lplen := len(lpath.as_posix())) > FILE_NAME_FULL_MAX_LEN and len(name_append) > 15:
                Log.warn(f'[{user}:{pid}]: file path \'{lpath.as_posix()}\' length is {lplen:d} > {FILE_NAME_FULL_MAX_LEN:d}...')
                name_append = f'{name_append[:len(name_append) // 2]}{link_base.suffix}'
                lpath = dest.joinpath(sanitize_path(next_file_name(name_append)))
            if (lplen := len(lpath.as_posix())) > FILE_NAME_FULL_MAX_LEN:
                raise OSError(f'[{user}:{pid}]: file path \'{lpath.as_posix()}\' length is {lplen:d} > {FILE_NAME_FULL_MAX_LEN:d}!')

            plink = PostLinkInfo(pid, name, link, lpath, DownloadStatus())

            if not is_link_native(plink.url):
                plink.status.flags |= DownloadFlags.EXTERNAL_LINK

            links[name] = plink

        p = PostInfo(pid, user, service, title, imported, published, edited, tags, content, dest, list(links.values()), DownloadStatus())
        await Cache.store_post_info_cache([p])
        post_infos.append(p)

    return post_infos

#
#
#########################################
