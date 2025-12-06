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
)


class APIAction(ABC):
    _api_address: APIAddress
    _method: APIMethod
    _endpoint: APIEndpoint
    _endpoint_params: APIEndpointParams
    _request_data: APIRequestParams

    def __init__(self) -> None:
        self._validate()

    @classmethod
    @abstractmethod
    def _validate(cls) -> None: ...
    @classmethod
    @abstractmethod
    def as_api_request_data(cls) -> APIRequestData: ...
    @classmethod
    @abstractmethod
    def get_url(cls) -> URL: ...
    @abstractmethod
    def __str__(self) -> str: ...


class APIFetchAction(APIAction):
    @classmethod
    def _validate(cls) -> None:
        assert cls._endpoint.count('{}') == len(cls._endpoint_params)

    @classmethod
    @abstractmethod
    async def process_response_content(cls, content: bytes) -> APIResponse: ...

    @classmethod
    def as_api_request_data(cls) -> APIRequestData:
        return {'method': cls._method, 'url': cls.get_url(), 'params': cls._request_data}

    @classmethod
    def get_url(cls) -> URL:
        return URL(f'https://{cls._api_address}') / APIEntrance / cls._endpoint.format(*cls._endpoint_params)

    def __str__(self) -> str:
        return f'[{self._method}] => {self.get_url().human_repr()}'


class APIDownloadAction(APIAction):
    _download_url: URL

    def __init__(self, url: URL) -> None:
        self._setup(url)
        super().__init__()

    @classmethod
    def _setup(cls, url: URL) -> None:
        cls._method = 'GET'
        cls._download_url = url

    @classmethod
    def _validate(cls) -> None:
        assert cls._download_url.is_absolute()

    @classmethod
    def as_api_request_data(cls) -> APIRequestData:
        return {'method': cls._method, 'url': cls.get_url(), 'allow_redirects': True}

    @classmethod
    def get_url(cls) -> URL:
        return cls._download_url

    def __str__(self) -> str:
        return f'[{self._method}] => {self.get_url().human_repr()}'

#
#
#########################################
