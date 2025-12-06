# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json

from kemono_ripper.api.actions import APIFetchAction
from kemono_ripper.api.types import APIAddress, APIService, FreePost, ListedPost, ScannedPost


class GetCreatorPostsAction(APIFetchAction):
    def __init__(self, api_addr: APIAddress, service: APIService, creator_id: int, offset: int) -> None:
        self._setup(api_addr, service, creator_id, offset)
        super().__init__()

    def _setup(self, api_addr: APIAddress, service: APIService, creator_id: int, offset: int) -> None:
        self._api_address = api_addr
        self._method = 'GET'
        self._endpoint = '{}/user/{}/posts'
        self._endpoint_params = (service, creator_id)
        self._request_data = {'o': offset}

    async def process_response_content(self, content: bytes) -> list[ListedPost]:
        json_ = json.loads(content)
        return json_


class GetFreePostAction(APIFetchAction):
    def __init__(self, api_addr: APIAddress, service: APIService, post_id: str) -> None:
        self._setup(api_addr, service, post_id)
        super().__init__()

    def _setup(self, api_addr: APIAddress, service: APIService, post_id: str) -> None:
        self._api_address = api_addr
        self._method = 'GET'
        self._endpoint = '{}/post/{}'
        self._endpoint_params = (service, post_id)
        self._request_data = {}

    async def process_response_content(self, content: bytes) -> FreePost:
        json_ = json.loads(content)
        return json_


class GetCreatorPostAction(APIFetchAction):
    def __init__(self, api_addr: APIAddress, service: APIService, creator_id: int, post_id: str) -> None:
        self._setup(api_addr, service, creator_id, post_id)
        super().__init__()

    def _setup(self, api_addr: APIAddress, service: APIService, creator_id: int, post_id: str) -> None:
        self._api_address = api_addr
        self._method = 'GET'
        self._endpoint = '{}/user/{}/post/{}'
        self._endpoint_params = (service, creator_id, post_id)
        self._request_data = {}

    async def process_response_content(self, content: bytes) -> ScannedPost:
        json_ = json.loads(content)
        return json_

#
#
#########################################
