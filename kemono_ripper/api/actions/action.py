# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from abc import ABC, abstractmethod

from yarl import URL

from kemono_ripper.api.types import (
    APIAddress,
    APIEndpoint,
    APIEndpointParams,
    APIEntrance,
    APIMethod,
    APIRequestData,
    APIRequestParams,
    APIResponse,
    PostDownloadInfo,
    PostLinkDownloadInfo,
)


class APIAction(ABC):
    _api_address: APIAddress
    _method: APIMethod
    _endpoint: APIEndpoint
    _endpoint_params: APIEndpointParams
    _request_data: APIRequestParams

    def __init__(self) -> None:
        self._validate()

    @abstractmethod
    def _validate(self) -> None: ...

    @abstractmethod
    def as_api_request_data(self) -> APIRequestData: ...

    @abstractmethod
    def get_url(self) -> URL: ...

    @abstractmethod
    def __str__(self) -> str: ...


class APIFetchAction(APIAction):
    """
    Fetch action is only for querying API itself, FIFO, avoid simultaneous requests!
    """

    def _validate(self) -> None:
        assert self._endpoint.count('{}') == len(self._endpoint_params)

    @abstractmethod
    async def process_response_content(self, content: bytes) -> APIResponse: ...

    def assert_valid_json_result(self, json_: APIResponse) -> None:
        assert json_ != ['error'], f'Invalid json \'{json_!s}\' was returned from request {self!s}'

    def as_api_request_data(self) -> APIRequestData:
        return {'method': self._method, 'url': self.get_url(), 'params': self._request_data}

    def get_url(self) -> URL:
        return URL(f'https://{self._api_address}') / APIEntrance / self._endpoint.format(*self._endpoint_params)

    def __str__(self) -> str:
        return f'[{self._method}] => {self.get_url().human_repr()}'


class APIDownloadAction(APIAction):
    """
    Download actions can be executed in parallel, up to {MAX_JOBS} at a time
    """
    _post: PostDownloadInfo
    _post_link: PostLinkDownloadInfo

    def __init__(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> None:
        self._setup(post, plink)
        super().__init__()

    def _setup(self, post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> None:
        self._method = 'GET'
        self._post = post
        self._post_link = plink

    def _validate(self) -> None:
        assert self._post_link.url.is_absolute()

    def as_api_request_data(self) -> APIRequestData:
        return {'method': self._method, 'url': self.get_url(), 'allow_redirects': True}

    def get_url(self) -> URL:
        return self._post_link.url

    @property
    def post(self) -> PostDownloadInfo:
        return self._post

    @property
    def post_link(self) -> PostLinkDownloadInfo:
        return self._post_link

    def __str__(self) -> str:
        return f'[{self._method}] => {self.get_url().human_repr()}'

#
#
#########################################
