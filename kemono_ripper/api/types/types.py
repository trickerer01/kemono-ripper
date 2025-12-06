# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from typing import Literal, NamedTuple, TypeAlias, TypedDict

APIEntrance = 'api/v1'
APIMethod: TypeAlias = Literal['GET', 'POST']
APIAddress: TypeAlias = Literal['kemono.cr', 'kemono.su', 'kemono.party', 'coomer.cr', 'coomer.su', 'coomer.party']
APIService: TypeAlias = Literal['patreon', 'boosty', 'subscribestar', 'fantia', 'gumroad', 'fanbox', 'discord', 'dlsite']
APIEndpointFormat: TypeAlias = Literal['{}/user/{}/posts', '{}/user/{}/post/{}', '{}/post/{}']
APIEndpoint: TypeAlias = Literal['creators', APIEndpointFormat]


class PostPageScanResult(NamedTuple):
    post_id: str
    creator_id: int
    service: APIService
    api_address: APIAddress


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


class ScannedPostPostFile(TypedDict):
    name: str
    path: str


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
    embed: dict  # TODO: validate
    shared_file: bool
    added: str
    published: str
    edited: str
    file: ScannedPostPostFile
    attachments: list[ScannedPostPostAttachment]
    poll: ScannedPostPostPoll | None
    # captions: unk
    tags: list[str] | None
    # incomplete_rewards: key may be absent
    next: str | None
    prev: str | None


class ScannedPostAttachment(TypedDict):
    server: str
    name: str  # full file name with n_extension
    extension: str  # '.abc' may differ from n_extension
    name_extension: str
    stem: str  # file slug without extension
    path: str  # '/2c/41/2c41ce3128d182916e2922ea2c96148ddf2e97d5.png'


class ScannedPostPreview(TypedDict):
    type: str  # 'thumbnail'
    server: str  # 'https://n2.k...o.cr'
    name: str  # 'Wasd.png'
    path: str  # '/2c/41/2c41ce3128d182916e2922ea2c96148ddf2e97d5.png'


class ScannedPostRevision(ScannedPostPost):
    pass


class ScannedPostProps(TypedDict):
    flagged: int | None
    revisions: list[tuple[int, ScannedPostRevision]]


class ScannedPost(TypedDict):
    post: ScannedPostPost
    attachments: list[ScannedPostAttachment]
    previews: list[ScannedPostPreview]
    videos: list[dict]  # TODO: validate
    props: ScannedPostProps


APIResponse: TypeAlias = list[Creator] | list[ListedPost] | FreePost | ScannedPost
APIEndpointParams: TypeAlias = tuple[str | int] | tuple
APIRequestParams: TypeAlias = dict[str, str | int]
APIRequestData: TypeAlias = dict[str, str | APIRequestParams]

#
#
#########################################
