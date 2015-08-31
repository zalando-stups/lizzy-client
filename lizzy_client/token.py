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


class TokenException(Exception):
    """
    Common Parent Exception for all errors that happen when getting the access token
    """

    def __init__(self, msg=''):
        self.error_msg = msg

    def __str__(self):
        return self.error_msg


class AuthenticationError(TokenException):
    """
    Exception to be raised if authentication failed
    """

    def __init__(self, response: requests.Response):
        self.response = response
        # do to the implementation of Response.ok, status_code is always between 400 and 599
        error_side = 'Server' if 500 <= response.status_code < 600 else 'Client'
        self.error_msg = '{response.status_code} {error_side} Error: {response.reason}'.format_map(locals())


class TokenInfoError(TokenException):
    def __init__(self, error_msg: str):
        self.response = None
        self.error_msg = error_msg


def get_token(url: str, scopes: str, client_id: str, client_secret: str, user: str, password: str) -> dict:
    """
    Get access token info.
    """
    data = {'grant_type': 'password',
            'scope': scopes,
            'username': user,
            'password': password}
    response = requests.post(url=url, auth=(client_id, client_secret), data=data)  # type: requests.Response
    if not response.ok:
        raise AuthenticationError(response)
    token_info = response.json()  # type: dict
    try:
        access_token = token_info['access_token']
    except KeyError:
        raise TokenInfoError('"access_token" not on json.')
    return access_token
