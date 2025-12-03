# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json

from kemono_ripper.api.actions import APIAction
from kemono_ripper.api.types import APIAddress, Creator


class GetCreatorsAction(APIAction):
    def __init__(self, api_addr: APIAddress) -> None:
        self._setup(api_addr)
        super().__init__()

    @classmethod
    def _setup(cls, api_addr: APIAddress) -> None:
        cls._api_address = api_addr
        cls._method = 'GET'
        cls._endpoint = 'creators'
        cls._endpoint_params = ()
        cls._request_data = {}

    @classmethod
    async def process_response_content(cls, content: bytes) -> list[Creator]:
        json_ = json.loads(content)
        return json_

#
#
#########################################
