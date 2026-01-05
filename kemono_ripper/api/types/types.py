# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
from enum import IntEnum
from typing import Literal, NamedTuple, TypeAlias, TypedDict

from yarl import URL

APIEntrance = 'api/v1'
APIMethod: TypeAlias = Literal['GET', 'POST']
APIAddress: TypeAlias = Literal['kemono.cr', 'kemono.party']
APIService: TypeAlias = Literal['patreon', 'boosty', 'subscribestar', 'fantia', 'gumroad', 'fanbox', 'discord', 'dlsite']
APIEndpointFormat: TypeAlias = Literal['{}/user/{}/posts', '{}/user/{}/post/{}', '{}/post/{}', 'posts/tags', 'posts']
APIEndpoint: TypeAlias = Literal['creators', APIEndpointFormat]


class PostPageScanResult(NamedTuple):
    post_id: str
    creator_id: str
    service: APIService
    api_address: APIAddress

    def as_cache_key(self) -> str:
        return f'{self.post_id}:{self.service}'


# Validated

# Creator list / dump
class Creator(TypedDict):
    id: str
    name: str
    service: APIService
    indexed: int
    updated: int
    favorited: int


# Post list
class ListedPostFile(TypedDict):
    name: str
    path: str


class ListedPostAttachment(TypedDict):
    name: str
    path: str


class ListedPost(TypedDict):
    id: str
    user: str
    service: APIService
    title: str
    substring: str
    published: str
    file: ListedPostFile
    attachments: list[ListedPostAttachment]


# Post scan
class FreePost(TypedDict):
    service: APIService
    artist_id: str
    post_id: str


class ScannedPostPostEmbed(TypedDict):
    url: str  # URL
    subject: str | None
    description: str | None


class ScannedPostPostFileCoverOriginal(TypedDict):
    name: str
    path: str


class ScannedPostPostFileCover(TypedDict):
    original: ScannedPostPostFileCoverOriginal
    main_cover: bool


class ScannedPostPostFile(TypedDict):
    name: str  # may be absent in case of 'covers'
    path: str  # may be absent is case of 'covers'
    covers: list[ScannedPostPostFileCover]  # may be absent
    thumbnail: dict  # unknown, may be absent


class ScannedPostPostAttachment(TypedDict):
    name: str
    path: str


class ScannedPostPostPollChoice(TypedDict):
    text: str
    votes: int


class ScannedPostPostPoll(TypedDict):
    title: str
    choices: list[ScannedPostPostPollChoice]
    closes_at: str
    created_at: str
    description: str | None
    allow_multiple: bool


class ScannedPostPost(TypedDict):
    id: str
    user: str
    service: APIService
    title: str
    content: str
    embed: ScannedPostPostEmbed
    shared_file: bool
    added: str | None  # 'imported'
    published: str
    edited: str | None
    file: ScannedPostPostFile
    attachments: list[ScannedPostPostAttachment]
    poll: ScannedPostPostPoll | None
    # captions: unk
    tags: list[str] | None
    # incomplete_rewards: key may be absent
    # next: str | None  # optional
    # prev: str | None  # optional


class ScannedPostAttachment(TypedDict):
    server: str
    name: str  # full file name with n_extension
    extension: str  # '.abc' may differ from n_extension
    name_extension: str
    stem: str  # file slug without extension
    path: str  # '/2c/41/2c41ce3128d182916e2922ea2c96148ddf2e97d5.png'


class ScannedPostPreview(TypedDict):
    type: Literal['thumbnail', 'embed']
    # thumbnail
    server: str  # 'https://n2.k...o.cr'
    name: str  # 'Wasd.png'
    path: str  # '/2c/41/2c41ce3128d182916e2922ea2c96148ddf2e97d5.png'
    # embed
    url: str  # 'https://gfy...t.com/fwejiopjhpoqwjhojeo'
    subject: str  # 'Asd das ddd'
    description: str  # 'Watch and share Asd das ddd ...'


class ScannedPostVideo(TypedDict):
    server: str  # same as ScannedPostAttachment
    name: str  # same as ScannedPostAttachment
    extension: str  # same as ScannedPostAttachment
    name_extension: str  # same as ScannedPostAttachment
    index: int
    path: str  # same as ScannedPostAttachment


class ScannedPostRevision(ScannedPostPost):
    pass


class ScannedPostProps(TypedDict):
    flagged: int | None
    revisions: list[tuple[int, ScannedPostRevision]]


class ScannedPost(TypedDict):
    post: ScannedPostPost
    attachments: list[ScannedPostAttachment]
    previews: list[ScannedPostPreview]
    videos: list[ScannedPostVideo]  # optional
    props: ScannedPostProps


# Post search
class SearchedPostFile(ScannedPostPostFile):
    pass


class SearchedPost(ScannedPostPost):
    pass


class SearchedPosts(TypedDict):
    count: int
    true_count: int
    posts: list[SearchedPost]


# Post tags
class PostListedTag(TypedDict):
    tag: str
    post_count: int


APIResponse: TypeAlias = list[Creator] | list[PostListedTag] | list[ListedPost] | FreePost | ScannedPost | SearchedPosts
APIEndpointParams: TypeAlias = tuple[str], tuple[str, str] | tuple[str, str, str] | tuple[str, str, list[str]]
APIRequestParams: TypeAlias = dict[str, str | int]
APIRequestData: TypeAlias = dict[str, str | APIRequestParams]


class DownloadResult(IntEnum):
    SUCCESS = 0
    FAIL_NOT_FOUND = 1
    FAIL_RETRIES = 2
    FAIL_ALREADY_EXISTS = 3
    FAIL_SKIPPED = 4
    FAIL_FILTERED_OUT = 5
    FAIL_UNSUPPORTED = 6
    FAIL_NO_LINKS = 7
    SUCCESS_PARTIAL = 8
    UNKNOWN = 255

    RESULT_MASK_ALL = ((1 << SUCCESS) | (1 << FAIL_NOT_FOUND) | (1 << FAIL_RETRIES) | (1 << FAIL_ALREADY_EXISTS) |
                       (1 << FAIL_SKIPPED) | (1 << FAIL_FILTERED_OUT) | (1 << FAIL_UNSUPPORTED) | (1 << FAIL_NO_LINKS) |
                       (1 << SUCCESS_PARTIAL))
    RESULT_MASK_CRITICAL = (RESULT_MASK_ALL & ~((1 << SUCCESS) | (1 << FAIL_SKIPPED) | (1 << FAIL_ALREADY_EXISTS) | (1 << SUCCESS_PARTIAL)))

    def __str__(self) -> str:
        return f'{self.name} (0x{self.value:02X})'

    __repr__ = __str__


class State(IntEnum):
    NEW = 0
    QUEUED = 1
    ACTIVE = 2
    SCANNING = 3
    SCANNED = 4
    DOWNLOAD_PENDING = 5
    DOWNLOADING = 6
    WRITING = 7
    DONE = 8
    FAILED = 9

    def __str__(self) -> str:
        return f'{self.name} (0x{self.value:02X})'

    __repr__ = __str__


class DownloadFlags(IntEnum):
    NONE = 0x00
    ALREADY_EXISTED_EXACT = 0x01
    ALREADY_EXISTED_SIMILAR = 0x02
    FILE_WAS_CREATED = 0x04
    RETURNED_404 = 0x08
    EXTERNAL_LINK = 0x10
    COMPLETED = 0x20


class DownloadStatus:
    def __init__(self, *, expected_size=0, flags=DownloadFlags.NONE, result=DownloadResult.UNKNOWN, state=State.NEW) -> None:
        self.size = expected_size
        self.flags = flags
        self.result = result
        self.state = state

    def __str__(self) -> str:
        return f'state: {self.state!s}, flags: {self.flags!s}, result: {self.result!s}'

    __repr__ = __str__


class URLProbeResult(NamedTuple):
    suffix: str
    size: int


class SQLColumn(NamedTuple):
    name: str
    data_type: Literal['TEXT', 'INTEGER', 'REAL', 'BLOB']
    not_null: bool
    default: str | None


class SQLSchema(NamedTuple):
    table_name: str
    columns: tuple[SQLColumn, ...]
    primary_key: tuple[str, ...] | tuple


class PostLinkInfo(NamedTuple):
    post_id: str
    name: str
    url: URL
    path: pathlib.Path
    status: DownloadStatus

    def get_local_path(self, levels: Literal[2, 3, 4]) -> str:
        return '/'.join(('...', *self.path.parts[-levels:]))

    @property
    def local_path2(self) -> str:
        return self.get_local_path(2)

    @property
    def local_path3(self) -> str:
        return self.get_local_path(3)

    @property
    def local_path4(self) -> str:
        return self.get_local_path(4)

    @property
    def local_path(self) -> str:
        return self.local_path3

    sql_schema = SQLSchema(
        'cache_post_link',
        (
            SQLColumn('post_id', 'TEXT', True, None),
            SQLColumn('name', 'TEXT', True, None),
            SQLColumn('url', 'TEXT', True, None),
            SQLColumn('path', 'TEXT', True, None),
            SQLColumn('size', 'INTEGER', True, "'0'"),
            SQLColumn('flags', 'INTEGER', True, "'0'"),
        ),
        ('post_id', 'name'))


class PostInfo(NamedTuple):
    post_id: str
    creator_id: str
    service: str
    title: str
    imported: str | None
    published: str | None
    edited: str | None
    tags: list[str]
    content: str
    dest: pathlib.Path
    links: list[PostLinkInfo]
    status: DownloadStatus

    def as_cache_key(self) -> str:
        return f'{self.post_id}:{self.service}'

    def get_local_path(self, levels: Literal[2, 3]) -> str:
        return '/'.join(('...', *self.dest.parts[-levels:]))

    @property
    def local_path2(self) -> str:
        return self.get_local_path(2)

    @property
    def local_path3(self) -> str:
        return self.get_local_path(3)

    @property
    def local_path(self) -> str:
        return self.local_path2

    def __hash__(self) -> int:
        return hash((self.creator_id, self.post_id))

    sql_schema = SQLSchema(
        'cache_post',
        (
            SQLColumn('post_id', 'TEXT', True, None),
            SQLColumn('creator_id', 'TEXT', True, None),
            SQLColumn('service', 'TEXT', True, None),
            SQLColumn('title', 'TEXT', True, None),
            SQLColumn('imported', 'TEXT', False, None),
            SQLColumn('published', 'TEXT', False, None),
            SQLColumn('edited', 'TEXT', False, None),
            SQLColumn('tags', 'TEXT', True, None),
            SQLColumn('content', 'TEXT', True, None),
            SQLColumn('dest', 'TEXT', True, "''"),
            SQLColumn('flags', 'INTEGER', True, "'0'"),
        ),
        ('post_id',))


class PCSDPost(TypedDict):
    """
    Protocol: ListedPost, SearchedPost, ScannedPostPost
    """
    id: str
    user: str
    service: APIService
    published: str

#
#
#########################################
