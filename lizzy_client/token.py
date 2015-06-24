"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import requests


def get_token(url: str, client_id: str, client_secret: str, user: str, password: str) -> dict:
    """
    Get access token info.
    """
    data = {'grant_type': 'password',
            'scope': 'uid',
            'username': user,
            'password': password}
    request = requests.post(url=url, auth=(client_id, client_secret), data=data)  # type: requests.Response
    request.raise_for_status()
    token_info = request.json()  # type: dict
    return token_info
