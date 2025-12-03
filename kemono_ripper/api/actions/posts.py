# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json

from kemono_ripper.api.actions import APIAction
from kemono_ripper.api.types import APIAddress, APIService, FreePost, ListedPost, ScannedPost


class GetCreatorPostsAction(APIAction):
    def __init__(self, api_addr: APIAddress, service: APIService, creator_id: int, offset: int) -> None:
        self._setup(api_addr, service, creator_id, offset)
        super().__init__()

    @classmethod
    def _setup(cls, api_addr: APIAddress, service: APIService, creator_id: int, offset: int) -> None:
        cls._api_address = api_addr
        cls._method = 'GET'
        cls._endpoint = '{}/user/{}/posts'
        cls._endpoint_params = (service, creator_id)
        cls._request_data = {'o': offset}

    @classmethod
    async def process_response_content(cls, content: bytes) -> list[ListedPost]:
        json_ = json.loads(content)
        return json_


class GetFreePostAction(APIAction):
    def __init__(self, api_addr: APIAddress, service: APIService, post_id: int) -> None:
        self._setup(api_addr, service, post_id)
        super().__init__()

    @classmethod
    def _setup(cls, api_addr: APIAddress, service: APIService, post_id: int) -> None:
        cls._api_address = api_addr
        cls._method = 'GET'
        cls._endpoint = '{}/post/{}'
        cls._endpoint_params = (service, post_id)
        cls._request_data = {}

    @classmethod
    async def process_response_content(cls, content: bytes) -> FreePost:
        json_ = json.loads(content)
        return json_


class GetCreatorPostAction(APIAction):
    def __init__(self, api_addr: APIAddress, service: APIService, creator_id: int, post_id: int) -> None:
        self._setup(api_addr, service, creator_id, post_id)
        super().__init__()

    @classmethod
    def _setup(cls, api_addr: APIAddress, service: APIService, creator_id: int, post_id: int) -> None:
        cls._api_address = api_addr
        cls._method = 'GET'
        cls._endpoint = '{}/user/{}/post/{}'
        cls._endpoint_params = (service, creator_id, post_id)
        cls._request_data = {}

    @classmethod
    async def process_response_content(cls, content: bytes) -> ScannedPost:
        json_ = json.loads(content)
        return json_

#
#
#########################################
