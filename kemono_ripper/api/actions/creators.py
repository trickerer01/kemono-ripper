# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json

from kemono_ripper.api.actions import APIFetchAction
from kemono_ripper.api.types import APIAddress, Creator


class GetCreatorsAction(APIFetchAction):
    def __init__(self, api_addr: APIAddress) -> None:
        self._setup(api_addr)
        super().__init__()

    def _setup(self, api_addr: APIAddress) -> None:
        self._api_address = api_addr
        self._method = 'GET'
        self._endpoint = 'creators'
        self._endpoint_params = ()
        self._request_data = {}

    async def process_response_content(self, content: bytes) -> list[Creator]:
        json_ = json.loads(content)
        self.assert_valid_json_result(json_)
        return json_

#
#
#########################################
